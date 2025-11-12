# main.py
# 主應用程式入口點 (DSAHelperApp)
# 負責:
# 1. Tkinter 視窗和 UI 狀態管理
# 2. 協調 Worker 執行緒 (啟動、停止、命令)
# 3. 處理來自 Worker 的資料佇列 (Queue)
# 4. 執行所有 *寫入* 操作 (Pymem writes) 和 WinAPI (ctypes)

import tkinter as tk
from tkinter import ttk
import ctypes
import os
import sys
import time 
import queue       # (Refactored) 新增
import threading   # (Refactored) 新增

import pymem
import pymem.pattern
import psutil
try:
    import ctypes.wintypes
except ImportError:
    print("缺少 ctypes.wintypes 模組")
    sys.exit(1)

# --- (Refactored) 從拆分的檔案中導入 ---
from constants import *
from ui_components import ScrollableFrame
from utils import is_admin
import app_ui # 導入整個 UI 模組
from memory_worker import MemoryMonitorThread
# --------------------------------------


# --- DPI 感知設定 (必須在 tkinter 之前) ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1) 
except (AttributeError, OSError):
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass
# --- DPI 感知結束 ---


class DSAHelperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # (v3.10) 動態 DPI 縮放
        try:
            self.scaling_factor = self.tk.call('tk', 'scaling')
        except Exception:
            self.scaling_factor = 1.0 

        BASE_WIDTH = 890  
        BASE_HEIGHT = 210 
        BASE_LEFT_PANEL_WIDTH = 114 
        BASE_CHAR_COLUMN_WIDTH = 114

        scaled_width = int(BASE_WIDTH * self.scaling_factor)
        scaled_height = int(BASE_HEIGHT * self.scaling_factor)
        
        self.scaled_left_panel_width = int(BASE_LEFT_PANEL_WIDTH * self.scaling_factor)
        self.scaled_char_column_width = int(BASE_CHAR_COLUMN_WIDTH * self.scaling_factor)

        self.title("DSA新端輔助程式 v4.00 (多執行緒版) by 石器推廣大使 陳財佑")
        
        try:
            self.iconbitmap("icon.ico")
        except tk.TclError:
            self.log("錯誤: 找不到 icon.ico 檔案。")
        
        self.geometry(f"{scaled_width}x{scaled_height}") 
        self.resizable(False, True) 

        # (Refactored) 儲存 UI 元件的引用
        self.notebook = None
        self.tabs = {} 
        self.tab_frame_settings = None
        self.tab_frame_char = None
        self.client_checkboxes = [] 
        self.refresh_rate_combo = None
        self.setting_widgets = []   
        self.person_vars = [None] * MAX_CLIENTS       
        self.pet_vars_list = [None] * MAX_CLIENTS     
        self.char_frames = [None] * MAX_CLIENTS  
        
        # 狀態變數
        self.client_selection_vars = [tk.IntVar() for _ in range(MAX_CLIENTS)]
        self.refresh_rate_var = tk.StringVar()
        
        # (Refactored) client_data_slots 成為 "唯一真相來源 (Single Source of Truth)"
        # 它儲存句柄、基址和 *最新快取的資料*
        self.client_data_slots = [self.create_empty_slot_data() for _ in range(MAX_CLIENTS)]
        
        # (Refactored) 執行緒 和 佇列
        self.data_queue = queue.Queue()    # Worker -> UI
        self.command_queue = queue.Queue() # UI -> Worker
        self.worker_thread = None
        
        if not is_admin():
            self.title(f"{self.title()} (錯誤：請以管理員權限執行)")
            label = tk.Label(self, text="錯誤：\n必須以「系統管理員」權限執行此程式！", 
                             font=("Arial", 12), fg="red", padx=50, pady=50)
            label.pack()
        else:
            # (Refactored) UI 建立被移交給 app_ui 模組
            app_ui.create_main_widgets(self)
            
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.log("介面初始化完成。請點擊 '綁定石器'。")
            
            # (Refactored) 啟動 Worker 執行緒
            self.start_worker_thread()
            
            # (Refactored) 啟動 UI 佇列檢查迴圈
            self.check_data_queue()

    def create_empty_slot_data(self):
        """(v3.5) 建立一個空的資料槽"""
        return {
            "pid": None, "hwnd": None, "status": "未綁定", 
            "pm_handle": None, # (Main Thread) Pymem 句柄 (用於 *寫入*)
            "module_base": None, 
            
            # (Refactored) 以下是 Worker 執行緒會更新的 "快取"
            "game_state": "unbound",
            "account_name": "", 
            "char_data_cache": None, 
            "pet_data_cache": [None] * 5, 
            
            # 補丁狀態
            "walk_address": None, "walk_original_byte": None, "walk_is_patched": False,
            "speed_address_1": None, "speed_address_2": None, "speed_original_bytes_1": None, 
            "speed_original_bytes_2": None, "speed_is_patched": False,
            "noclip_address": None, "noclip_original_bytes": None, "noclip_is_patched": False,
            "is_hidden": False
        }

    def log(self, message):
        """(Refactored) 確保 log 總是在主執行緒中列印"""
        print(f"[Main] {message}") 

    # --- (Refactored) 執行緒 & 佇列管理 ---

    def start_worker_thread(self):
        """啟動記憶體監控執行緒"""
        if self.worker_thread is not None and self.worker_thread.is_alive():
            self.log("Worker 執行緒已在執行中。")
            return
            
        self.log("正在啟動 Worker 執行緒...")
        self.worker_thread = MemoryMonitorThread(
            self.data_queue,
            self.command_queue,
            self.client_data_slots # (Refactored) 傳遞對 slot 列表的 *引用*
        )
        self.worker_thread.start()
        # 傳送初始刷新率
        self.on_refresh_rate_change()

    def check_data_queue(self):
        """
        (Main Thread) 
        UI 迴圈，檢查來自 Worker 執行緒的資料。
        這是 *唯一* 應該更新 UI 的地方。
        """
        try:
            # 獲取來自 Worker 的 *整包* 最新資料
            full_data_package = self.data_queue.get_nowait()
            
            data_updated = False
            
            # (Refactored) 將最新資料更新到 "唯一真相來源" (self.client_data_slots)
            for i in range(MAX_CLIENTS):
                new_data = full_data_package[i]
                slot = self.client_data_slots[i]
                
                # (Refactored) Worker 報告句柄已失效
                if new_data["status"] == "已失效" and slot["status"] == "已綁定":
                    self.log(f"窗口 {i+1} (PID {slot['pid']}) 句柄已失效，正在清理...")
                    try:
                        if slot["pm_handle"]:
                            slot["pm_handle"].close()
                    except Exception as e:
                        self.log(f"  > 關閉失效句柄時出錯: {e}")
                    
                    # 重置 slot
                    self.client_data_slots[i] = self.create_empty_slot_data()
                    self.client_selection_vars[i].set(0)
                    data_updated = True
                
                # 正常更新快取資料
                elif slot["status"] == "已綁定":
                    # 檢查資料是否有實際變化
                    if (slot["account_name"] != new_data["account_name"] or
                        slot["char_data_cache"] != new_data["char_data_cache"] or
                        slot["pet_data_cache"] != new_data["pet_data_cache"]):
                        
                        data_updated = True
                        
                    slot["account_name"] = new_data["account_name"]
                    slot["game_state"] = new_data["game_state"]
                    slot["char_data_cache"] = new_data["char_data_cache"]
                    slot["pet_data_cache"] = new_data["pet_data_cache"]
            
            # (Refactored) 僅在資料實際變更時才觸發成本高昂的 UI 更新
            if data_updated:
                self.update_client_list_ui() # 更新左側列表
                self.update_all_displays()   # 更新右側頁籤

        except queue.Empty:
            pass # 佇列中沒有資料，很正常
        
        # (Refactored) 設置下一次檢查 (例如 100ms)
        # 這使 UI 保持響應，無論 Worker 的刷新率多慢
        self.after(100, self.check_data_queue)


    # --- 核心功能：綁定與掃描 (Main Thread) ---
    # (Refactored) 綁定和掃描 (一次性 I/O) 保留在主執行緒中
    # 點擊按鈕時的短暫卡頓是可以接受的

    def find_game_windows(self):
        """(Main Thread) 查找遊戲窗口"""
        found_windows = []
        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL,
                                             ctypes.wintypes.HWND,
                                             ctypes.wintypes.LPARAM)
        GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
        def foreach_window(hwnd, lParam):
            if IsWindowVisible(hwnd) == 0: return True 
            length = GetWindowTextLength(hwnd) + 1
            buffer = ctypes.create_unicode_buffer(length)
            GetWindowText(hwnd, buffer, length)
            pid = ctypes.wintypes.DWORD()
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                try:
                    proc = psutil.Process(pid.value)
                    if proc.name().lower() == PROCESS_NAME.lower():
                        found_windows.append((hwnd, pid.value))
                        if len(found_windows) >= MAX_CLIENTS: return False 
                except (psutil.NoSuchProcess, psutil.AccessDenied): pass
            return True
        EnumWindows(EnumWindowsProc(foreach_window), 0)
        return found_windows

    def on_bind_click(self):
        """(Main Thread) v3.6 綁定邏輯 (幾乎不變)"""
        self.log(f"--- 開始檢查綁定並搜尋新窗口 ---")
        
        current_pids = set()
        
        # 1. 檢查現有綁定是否仍然有效 (或是否被 Worker 標記為失效)
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            
            # (Refactored) 檢查 status == '已失效'
            if slot["status"] == "已失效":
                self.log(f"窗口 {i+1} (PID {slot['pid']}) 已被標記為失效, 清理...")
                # Worker 執行緒可能已經關閉了句柄，但再次嘗試關閉是安全的
                try:
                    if slot["pm_handle"]: slot["pm_handle"].close()
                except Exception: pass
                
                self.client_data_slots[i] = self.create_empty_slot_data()
                self.client_selection_vars[i].set(0)
                self.update_client_list_ui(i)
                continue

            if slot["pid"] and slot["pm_handle"] and slot["module_base"]:
                # (Refactored) 不再需要 read 測試，依賴 Worker 的 "已失效" 狀態
                current_pids.add(slot["pid"])
                self.log(f"窗口 {i+1} (PID {slot['pid']}) 檢查通過, 保留綁定。")
                continue

        # 2. 搜尋*新*的窗口
        found_windows = self.find_game_windows()
        new_windows = [w for w in found_windows if w[1] not in current_pids]

        if not new_windows:
            self.log("沒有找到新的窗口。")
            self.update_all_displays() # 確保 UI (例如剛被清理的) 已更新
            return

        # 3. 將新窗口填入空 slots
        self.log(f"找到 {len(new_windows)} 個新窗口, 正在綁定...")
        new_window_iter = iter(new_windows)
        for i in range(MAX_CLIENTS):
            if self.client_data_slots[i]["pid"] is None: # 這是個空 slot
                try:
                    hwnd, pid = next(new_window_iter)
                    slot = self.client_data_slots[i]
                    slot["pid"] = pid
                    slot["hwnd"] = hwnd
                    
                    # (Main Thread) 執行一次性的掃描 I/O
                    self.scan_client_addresses(i) 
                    
                    self.log(f"新窗口 (PID {pid}) 已綁定到窗口 {i+1}")
                    
                    # (Refactored) 立即更新 UI，而不是等待 Worker
                    self.update_client_list_ui(i) 
                    
                except StopIteration:
                    break # 沒有更多新窗口了
        
        # 4. 統一更新
        self.update_all_displays()


    def scan_client_addresses(self, slot_index):
        """(Main Thread) 掃描並快取 (儲存 pm_handle)"""
        slot = self.client_data_slots[slot_index]
        pid = slot["pid"]
        self.log(f"--- D正在掃描 PID: {pid} ---")

        try:
            # (Main Thread) 建立並儲存 Pymem 句柄
            pm = pymem.Pymem(pid)
            slot["pm_handle"] = pm
            
            module = pymem.process.module_from_name(pm.process_handle, PROCESS_NAME)
            if not module:
                self.log(f"  > 錯誤 (PID: {pid}): 找不到 {PROCESS_NAME} 模組。")
                slot["status"] = "掃描失敗"
                pm.close() 
                slot["pm_handle"] = None
                return
            
            slot["module_base"] = module.lpBaseOfDll
            self.log(f"  > (PID: {pid}) 找到模組基址 @ 0x{module.lpBaseOfDll:X}")

            # --- 1. 處理「快速行走」 ---
            try:
                addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_WALK)
                if not addr:
                    self.log(f"  > (PID: {pid}) 找不到「行走」特徵碼")
                    slot["walk_address"] = None 
                else:
                    patch_addr = addr + WALK_PATCH_OFFSET
                    curr_byte = pm.read_bytes(patch_addr, 1)[0]
                    slot["walk_address"] = patch_addr
                    if slot["walk_original_byte"] is None: slot["walk_original_byte"] = curr_byte
                    if curr_byte == WALK_PATCHED_BYTE: slot["walk_is_patched"] = True
                    elif curr_byte == slot["walk_original_byte"]: slot["walk_is_patched"] = False
                    self.log(f"  > (PID: {pid}) 找到「行走」 @ 0x{patch_addr:X} (狀態: {'已修補' if slot['walk_is_patched'] else '原始'})")
            except Exception as e: self.log(f"  > (PID: {pid}) 掃描「行走」出錯: {e}")

            # --- 2. 處理「遊戲加速」 ---
            try:
                addr1, addr2 = None, None
                is_patched_scan = False
                addr1 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_1_ORIGINAL)
                addr2 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_2_ORIGINAL)
                if not addr1 or not addr2:
                    self.log(f"  > (PID: {pid}) 未找到「加速」原始 AOB，嘗試掃描已修補 AOB...")
                    addr1 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_1_PATCHED)
                    addr2 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_2_PATCHED)
                    if addr1 and addr2: is_patched_scan = True 
                if not addr1 or not addr2:
                    self.log(f"  > (PID: {pid}) 找不到「加速」特徵碼")
                    slot["speed_address_1"] = None; slot["speed_address_2"] = None
                else:
                    patch_addr1 = addr1 + SPEED_AOB_OFFSET
                    patch_addr2 = addr2 + SPEED_AOB_OFFSET
                    slot["speed_address_1"] = patch_addr1
                    slot["speed_address_2"] = patch_addr2
                    if is_patched_scan:
                        slot["speed_is_patched"] = True
                        if slot["speed_original_bytes_1"] is None: self.log(f"  > (PID: {pid}) 警告：找到已修補的「加速」位址，但沒有快取原始 bytes，將無法還原！")
                    else:
                        slot["speed_is_patched"] = False
                        slot["speed_original_bytes_1"] = pm.read_bytes(patch_addr1, len(NOP_PATCH))
                        slot["speed_original_bytes_2"] = pm.read_bytes(patch_addr2, len(NOP_PATCH))
                    self.log(f"  > (PID: {pid}) 找到「加速1」 @ 0x{patch_addr1:X} (狀態: {'已修補' if slot['speed_is_patched'] else '原始'})")
            except Exception as e: self.log(f"  > (PID: {pid}) 掃描「加速」出錯: {e}")

            # --- 3. 處理「穿牆行走」 ---
            try:
                addr = None
                is_patched_scan = False
                addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_NOCLIP_ORIGINAL)
                if not addr:
                    self.log(f"  > (PID: {pid}) 未找到「穿牆」原始 AOB，嘗試掃描已修補 AOB...")
                    addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_NOCLIP_PATCHED)
                    if addr: is_patched_scan = True 
                if not addr:
                    self.log(f"  > (PID: {pid}) 找不到「穿牆」特徵碼")
                    slot["noclip_address"] = None
                else:
                    patch_addr = addr + NOCLIP_PATCH_OFFSET
                    slot["noclip_address"] = patch_addr
                    if is_patched_scan:
                        slot["noclip_is_patched"] = True
                        if slot["noclip_original_bytes"] is None: self.log(f"  > (PID: {pid}) 警告：找到已修補的「穿牆」位址，但沒有快取原始 bytes，將無法還原！")
                    else:
                        slot["noclip_is_patched"] = False
                        slot["noclip_original_bytes"] = pm.read_bytes(patch_addr, len(NOCLIP_PATCHED_BYTES))
                    self.log(f"  > (PID: {pid}) 找到「穿牆」 @ 0x{patch_addr:X} (狀態: {'已修補' if slot['noclip_is_patched'] else '原始'})")
            except Exception as e: self.log(f"  > (PID: {pid}) 掃描「穿牆」出錯: {e}")

            # --- 4. 掃描完成 ---
            slot["status"] = "已綁定"
            
        except Exception as e:
            self.log(f"掃描時發生嚴重錯誤 (PID: {pid}): {e}")
            slot["status"] = "掃描失敗"
            if slot["pm_handle"]: 
                slot["pm_handle"].close()
                slot["pm_handle"] = None


    # --- (Refactored) GUI 更新 (Main Thread) ---
    # 這些函式現在 *只讀取快取 (self.client_data_slots)*，不執行 I/O
    
    def on_selection_change(self):
        """(Main Thread) 當 Checkbox 被點擊時, 更新右側顯示"""
        self.update_all_displays()

    def update_all_displays(self):
        """
        (Main Thread) 核心: 動態建立/銷毀 UI
        (Refactored) *** 不執行任何 Pymem 讀取 ***
        *** 只從 self.client_data_slots 讀取快取資料 ***
        """
        
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            
            is_selected = self.client_selection_vars[i].get() == 1
            is_bound = slot["status"] == "已綁定"
            
            settings_ui = self.setting_widgets[i]
            
            if is_selected and is_bound:
                # --- 1. 更新「遊戲設置」 ---
                settings_ui["frame"].pack(side="left", fill="y", anchor="n", padx=5, pady=5) 
                
                settings_ui["frame"].config(text=slot.get("account_name", f"窗口 {i+1}"))
                settings_ui["vars"]["game_speed"].set(slot["speed_is_patched"])
                settings_ui["vars"]["fast_walk"].set(slot["walk_is_patched"])
                settings_ui["vars"]["no_clip"].set(slot["noclip_is_patched"])
                settings_ui["vars"]["hide_sa"].set(slot["is_hidden"])
                
                settings_ui["widgets"]["speed"].config(state="normal" if slot["speed_address_1"] else "disabled")
                settings_ui["widgets"]["walk"].config(state="normal" if slot["walk_address"] else "disabled")
                settings_ui["widgets"]["noclip"].config(state="normal" if slot["noclip_address"] else "disabled")
                settings_ui["widgets"]["hide"].config(state="normal" if slot["hwnd"] else "disabled")

                # --- 2. 檢查「人寵資料」UI 是否需要建立 ---
                if self.char_frames[i] is None:
                    # --- 2a. 建立 UI ---
                    self.log(f"窗口 {i+1}: 正在建立人寵 UI...")
                    parent_frame = self.tab_frame_char.inner_frame
                    
                    client_frame = ttk.Labelframe(parent_frame, text=f"窗口 {i+1}", padding=5)
                    
                    for col_idx in range(0, 11, 2):
                        client_frame.columnconfigure(col_idx, minsize=self.scaled_char_column_width)
                    client_frame.rowconfigure(0, weight=1)
                    
                    person_vars_dict = {}
                    app_ui.create_person_column(client_frame, 0, person_vars_dict)
                    
                    pet_vars_list_for_client = []
                    for p_idx in range(5):
                        sep = ttk.Separator(client_frame, orient="vertical")
                        sep.grid(row=0, column=(p_idx*2 + 1), sticky="ns", padx=5)
                        pet_vars = app_ui.create_pet_column(client_frame, p_idx, (p_idx*2 + 2))
                        pet_vars_list_for_client.append(pet_vars)
                    
                    # 儲存
                    self.char_frames[i] = client_frame
                    self.person_vars[i] = person_vars_dict
                    self.pet_vars_list[i] = pet_vars_list_for_client

                # --- 2b. 顯示並更新 UI (無論是剛建立的還是已有的) ---
                char_ui_frame = self.char_frames[i]
                person_vars = self.person_vars[i]
                pet_vars_list = self.pet_vars_list[i]

                char_ui_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=5) 
                char_ui_frame.config(text=slot.get("account_name", f"窗口 {i+1}"))
                
                # (Refactored) 從快取更新
                self._configure_character_widgets(slot.get("char_data_cache"), person_vars)
                
                pet_caches = slot.get("pet_data_cache", [None] * 5)
                for p_idx in range(5):
                    self._configure_pet_widgets(pet_caches[p_idx], pet_vars_list[p_idx], p_idx)

            else:
                # --- 3. 未勾選: 隱藏 (Settings) 並 銷毀 (Char Info) ---
                settings_ui["frame"].pack_forget()

                if self.char_frames[i] is not None:
                    self.log(f"窗口 {i+1}: 正在銷毀人寵 UI...")
                    self.char_frames[i].destroy()
                    self.char_frames[i] = None
                    self.person_vars[i] = None
                    self.pet_vars_list[i] = None
        
        # 觸發 ScrollableFrame 重新計算
        if self.tab_frame_settings:
            self.tab_frame_settings.inner_frame.event_generate("<Configure>")
        if self.tab_frame_char:
            self.tab_frame_char.inner_frame.event_generate("<Configure>")

    def _configure_character_widgets(self, data, person_vars):
        """(Main Thread) 輔助函式, 根據 *快取資料* data 設定 UI"""
        app_bg_color = self.cget("background") # 獲取 App 背景色
        if data:
            person_vars["name"].config(text=data.get("name", "錯誤"))
            person_vars["nickname"].config(text=data.get("nickname", "稱號"))
            person_vars["lv"].config(text=data.get("lv", "--"))
            person_vars["hp"].config(text=data.get("hp", "--/--"))
            person_vars["mp"].config(text=data.get("mp", "--/--"))
            person_vars["atk"].config(text=data.get("atk", "--"))
            person_vars["def"].config(text=data.get("def", "--"))
            person_vars["agi"].config(text=data.get("agi", "--"))
            person_vars["vit"].config(text=data.get("vit", "--"))
            person_vars["str"].config(text=data.get("str", "--"))
            person_vars["sta"].config(text=data.get("sta", "--"))
            person_vars["spd"].config(text=data.get("spd", "--"))

            rebirth_text = data.get("rebirth", "未知")
            rebirth_color = REBIRTH_COLOR_MAP.get(rebirth_text, DEFAULT_FG_COLOR)
            person_vars["rebirth"].config(text=rebirth_text, foreground=rebirth_color)

            charm_val = data.get("charm", 0) 
            charm_color = "red" if charm_val <= 60 else DEFAULT_FG_COLOR
            person_vars["charm"].config(text=str(charm_val), foreground=charm_color)

            element_text = data.get("element", "無")
            
            if element_text != person_vars.get("last_element"):
                app_ui.update_element_display(person_vars["element_frame"], element_text, app_bg_color)
                person_vars["last_element"] = element_text
        else:
            # (省略... 與原碼相同)
            person_vars["name"].config(text="人物")
            person_vars["nickname"].config(text="稱號")
            # ... (其他欄位)
            person_vars["rebirth"].config(text="--", foreground=DEFAULT_FG_COLOR)
            person_vars["charm"].config(text="--", foreground=DEFAULT_FG_COLOR)
            if person_vars.get("last_element") != "無":
                app_ui.update_element_display(person_vars["element_frame"], "無", app_bg_color)
                person_vars["last_element"] = "無"


    def _clear_pet_vars(self, pet_vars, pet_index, app_bg_color):
        """(Main Thread) 輔助函式, 重置寵物 widgets"""
        pet_vars["name"].config(text=f"寵物{app_ui.num_to_chinese(pet_index + 1)}")
        pet_vars["nickname"].config(text="")
        # ... (其他欄位)
        pet_vars["loyal"].config(text="--", foreground=DEFAULT_FG_COLOR)
        app_ui.update_element_display(pet_vars["element_frame"], "無", app_bg_color)
        pet_vars["rebirth"].config(text="--", foreground=DEFAULT_FG_COLOR)

    def _configure_pet_widgets(self, data, pet_vars, p_idx):
        """(Main Thread) 根據 *快取資料* data 設定 UI"""
        app_bg_color = self.cget("background") # 獲取 App 背景色
        if data:
            pet_vars["name"].config(text=data.get("name", "錯誤"))
            pet_vars["nickname"].config(text=data.get("nickname", ""))
            # ... (其他欄位)

            rebirth_text = data.get("rebirth", "未知")
            rebirth_color = REBIRTH_COLOR_MAP.get(rebirth_text, DEFAULT_FG_COLOR)
            pet_vars["rebirth"].config(text=rebirth_text, foreground=rebirth_color)

            loyal_val = data.get("loyal", 100) 
            loyal_color = "red" if loyal_val <= 20 else DEFAULT_FG_COLOR
            pet_vars["loyal"].config(text=str(loyal_val), foreground=loyal_color)

            element_text = data.get("element", "無")
            
            if element_text != pet_vars.get("last_element"):
                app_ui.update_element_display(pet_vars["element_frame"], element_text, app_bg_color)
                pet_vars["last_element"] = element_text
        else:
            if pet_vars.get("last_element") is not None:
                self._clear_pet_vars(pet_vars, p_idx, app_bg_color)
                pet_vars["last_element"] = None

    def update_client_list_ui(self, slot_index=None):
        """
        (Main Thread) 
        (Refactored) 只更新左側 Checkbox 的 *顯示*
        *** 不執行任何 Pymem 讀取 ***
        """
        indices_to_update = range(MAX_CLIENTS) if slot_index is None else [slot_index]
        
        for i in indices_to_update:
            slot = self.client_data_slots[i]
            checkbox = self.client_checkboxes[i] 

            if slot["status"] == "已綁定":
                checkbox.config(text=slot["account_name"], state="normal", fg="green")
            else:
                checkbox.config(text=f"窗口 {i+1}: {slot['status']}", state="disabled", fg="grey")
                # (Refactored) 清理操作已移至 check_data_queue 和 on_bind_click
                
    # (Refactored) 刪除 start_monitoring_loop 和 monitor_game_states
    # 它們的邏輯已移至 memory_worker.py

    def get_poll_interval_sec(self):
        """(Refactored) 轉換刷新頻率 (秒)"""
        value = self.refresh_rate_var.get()
        mapping = {
            '0.5s': 0.5, '1s': 1.0, '3s': 3.0, '5s': 5.0,
            '10s': 10.0, '60s': 60.0, '不刷新': None
        }
        return mapping.get(value, 3.0) # 預設 3s

    def on_refresh_rate_change(self, event=None):
        """
        (Main Thread) 
        (Refactored) 當刷新頻率改變時, *傳送命令* 到 Worker 執行緒
        """
        new_rate_sec = self.get_poll_interval_sec()
        self.log(f"刷新頻率變更為: {self.refresh_rate_var.get()}")
        
        # 傳送命令到 Worker 執行緒
        if self.worker_thread and self.worker_thread.is_alive():
            self.command_queue.put({
                "action": "set_rate",
                "value": new_rate_sec
            })

    # --- (Main Thread) 核心功能：執行修補 (寫入) ---
    # (Refactored) 所有 *寫入* 操作保留在主執行緒中
    # 這些是快速、瞬時的操作，不會造成持續的 UI 卡頓
    
    def on_toggle_walk(self, client_index):
        slot = self.client_data_slots[client_index]
        pm = slot["pm_handle"]
        addr, orig_byte = slot["walk_address"], slot["walk_original_byte"]
        
        if pm is None or addr is None or orig_byte is None:
            self.log(f"窗口 {client_index+1} 錯誤：行走功能未綁定。")
            self.setting_widgets[client_index]["vars"]["fast_walk"].set(not self.setting_widgets[client_index]["vars"]["fast_walk"].get())
            return
            
        is_checked = self.setting_widgets[client_index]["vars"]["fast_walk"].get()
        target_byte = WALK_PATCHED_BYTE if is_checked else orig_byte
        action_text = "啟用" if is_checked else "還原"
        self.log(f"窗口 {client_index+1}: 快速行走 {action_text}...")
        success = self.perform_write_byte(pm, addr, target_byte)
        if success: slot["walk_is_patched"] = is_checked
        else:
            self.log("操作失敗！")
            self.setting_widgets[client_index]["vars"]["fast_walk"].set(not is_checked)

    def on_toggle_speed(self, client_index):
        slot = self.client_data_slots[client_index]
        pm = slot["pm_handle"]
        
        if pm is None or not slot["speed_address_1"] or not slot["speed_original_bytes_1"]:
            self.log(f"窗口 {client_index+1} 錯誤：加速功能未綁定。")
            self.setting_widgets[client_index]["vars"]["game_speed"].set(not self.setting_widgets[client_index]["vars"]["game_speed"].get())
            return
            
        is_checked = self.setting_widgets[client_index]["vars"]["game_speed"].get()
        action_text = "啟用 (NOP)" if is_checked else "還原 (ADD)"
        self.log(f"窗口 {client_index+1}: 遊戲加速 {action_text}...")
        if is_checked: target1, target2 = NOP_PATCH, NOP_PATCH
        else: target1, target2 = slot["speed_original_bytes_1"], slot["speed_original_bytes_2"]
        s1 = self.perform_write_bytes(pm, slot["speed_address_1"], target1)
        s2 = self.perform_write_bytes(pm, slot["speed_address_2"], target2)
        if s1 and s2: slot["speed_is_patched"] = is_checked
        else:
            self.log("操作失敗！")
            self.setting_widgets[client_index]["vars"]["game_speed"].set(not is_checked)

    def on_toggle_noclip(self, client_index):
        slot = self.client_data_slots[client_index]
        pm = slot["pm_handle"]
        addr, orig_bytes = slot["noclip_address"], slot["noclip_original_bytes"]
        
        if pm is None or addr is None or orig_bytes is None:
            self.log(f"窗口 {client_index+1} 錯誤：穿牆功能未綁定。")
            self.setting_widgets[client_index]["vars"]["no_clip"].set(not self.setting_widgets[client_index]["vars"]["no_clip"].get())
            return
            
        is_checked = self.setting_widgets[client_index]["vars"]["no_clip"].get()
        target_bytes = NOCLIP_PATCHED_BYTES if is_checked else orig_bytes
        action_text = "啟用" if is_checked else "還原"
        self.log(f"窗口 {client_index+1}: 穿牆行走 {action_text}...")
        success = self.perform_write_bytes(pm, addr, target_bytes)
        if success: slot["noclip_is_patched"] = is_checked
        else:
            self.log("操作失敗！")
            self.setting_widgets[client_index]["vars"]["no_clip"].set(not is_checked)

    def on_toggle_hide(self, client_index):
        slot = self.client_data_slots[client_index]
        hwnd = slot["hwnd"]
        if hwnd is None:
            self.log(f"窗口 {client_index+1} 錯誤：未找到窗口句柄(HWND)。")
            return
            
        is_checked = self.setting_widgets[client_index]["vars"]["hide_sa"].get()
        command = SW_HIDE if is_checked else SW_SHOW
        action_text = "隱藏" if is_checked else "顯示"
        self.log(f"窗口 {client_index+1}: {action_text}...")
        try:
            ctypes.windll.user32.ShowWindow(hwnd, command)
            slot["is_hidden"] = is_checked
        except Exception as e:
            self.log(f"隱藏窗口時出錯: {e}")
            self.setting_widgets[client_index]["vars"]["hide_sa"].set(not is_checked)

    def perform_write_byte(self, pm, patch_address, target_byte):
        """(Main Thread) 寫入單一位元組"""
        try:
            pm.write_uchar(patch_address, target_byte)
            written_byte = pm.read_bytes(patch_address, 1)[0]
            if written_byte == target_byte:
                self.log(f"  > 成功! (PID: {pm.process_id}) @ 0x{patch_address:X} -> 0x{target_byte:X}")
                return True
            else:
                self.log(f"  > 失敗! (PID: {pm.process_id}) 寫入後驗證失敗。")
                return False
        except Exception as e:
            self.log(f"寫入時出錯 (PID: {pm.process_id}): {e}")
            return False
            
    def perform_write_bytes(self, pm, patch_address, target_bytes):
        """(Main Thread) 寫入多位元組"""
        try:
            pm.write_bytes(patch_address, target_bytes, len(target_bytes))
            written_bytes = pm.read_bytes(patch_address, len(target_bytes))
            if written_bytes == target_bytes:
                self.log(f"  > V成功! (PID: {pm.process_id}) @ 0x{patch_address:X} -> {target_bytes.hex()}")
                return True
            else:
                self.log(f"  > 失敗! (PID: {pm.process_id}) 寫入後驗證失敗。")
                return False
        except Exception as e:
            self.log(f"寫入多位元組時出錯 (PID: {pm.process_id}): {e}")
            return False

    # --- (Main Thread) WinAPI & 關閉 ---

    def on_client_right_click_single(self, event, client_index):
        slot = self.client_data_slots[client_index]
        if slot["status"] != "已綁定" or slot["hwnd"] is None: return
        hwnd = slot["hwnd"]
        try:
            self.log(f"窗口 {client_index+1}: 激活")
            if ctypes.windll.user32.IsIconic(hwnd):
                ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception as e:
            self.log(f"右鍵單擊窗口 {client_index+1} 時出錯: {e}")

    def on_client_right_click_double(self, event, client_index):
        slot = self.client_data_slots[client_index]
        if slot["status"] != "已綁定" or slot["hwnd"] is None: return
        hwnd = slot["hwnd"]
        try:
            self.log(f"窗口 {client_index+1}: 縮小")
            ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE) 
        except Exception as e:
            self.log(f"右鍵雙擊窗口 {client_index+1} 時出錯: {e}")

    def on_closing(self):
        """(Main Thread) 關閉程式時的清理"""
        
        # (Refactored) 1. 告訴 Worker 執行緒停止
        self.log("正在傳送停止訊號到 Worker 執行緒...")
        if self.worker_thread and self.worker_thread.is_alive():
            self.command_queue.put({"action": "stop"})
            # (可選) 等待執行緒結束，最多 2 秒
            self.worker_thread.join(timeout=2.0) 
            if self.worker_thread.is_alive():
                self.log("  > Worker 執行緒未在 2 秒內停止。")

        # 2. 執行主執行緒的清理 (還原補丁、關閉句柄)
        self.log("正在還原所有補丁並關閉句柄...")
        
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            pm = slot["pm_handle"]
            
            if not pm or slot["status"] != "已綁定":
                continue
            
            # (Refactored) 檢查句柄是否仍然有效
            try:
                pm.read_int(slot["module_base"]) 
            except Exception:
                self.log(f"窗口 {i+1} (PID {slot['pid']}) 句柄已失效, 跳過還原。")
                try: pm.close() # 關閉失效的句柄
                except: pass
                continue
            
            self.log(f"正在還原窗口 {i+1} (PID: {slot['pid']})...")
            try:
                if slot["walk_is_patched"] and slot["walk_original_byte"]:
                    self.perform_write_byte(pm, slot["walk_address"], slot["walk_original_byte"])
                if slot["speed_is_patched"] and slot["speed_original_bytes_1"]:
                    self.perform_write_bytes(pm, slot["speed_address_1"], slot["speed_original_bytes_1"])
                    self.perform_write_bytes(pm, slot["speed_address_2"], slot["speed_original_bytes_2"])
                if slot["noclip_is_patched"] and slot["noclip_original_bytes"]:
                    self.perform_write_bytes(pm, slot["noclip_address"], slot["noclip_original_bytes"])
                if slot["is_hidden"]:
                    ctypes.windll.user32.ShowWindow(slot["hwnd"], SW_SHOW)
            except Exception as e:
                self.log(f"還原 PID {slot['pid']} 時出錯: {e}")
            
            try:
                pm.close()
                self.log(f"  > (PID: {slot['pid']}) 句柄已關閉。")
            except Exception as e:
                self.log(f"關閉句柄 (PID: {slot['pid']}) 時出錯: {e}")

        self.destroy()

# --- 程式主體 ---
if __name__ == "__main__":
    app = DSAHelperApp()
    app.mainloop()