# main.py (v4.3 - 單一畫布, 動態高度, 右鍵對調)

import tkinter as tk
from tkinter import ttk
import ctypes
import os
import sys
import time 
import queue
import threading

import pymem
import pymem.pattern
import psutil
try:
    import ctypes.wintypes
except ImportError:
    print("缺少 ctypes.wintypes 模組")
    sys.exit(1)

from constants import *
from ui_components import ScrollableFrame
from utils import is_admin
import app_ui 
from memory_worker import MemoryMonitorThread

# --- DPI 感知設定 ---
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
        
        try:
            self.scaling_factor = self.tk.call('tk', 'scaling')
        except Exception:
            self.scaling_factor = 1.0 

        BASE_WIDTH = 925
        BASE_HEIGHT = 180
        BASE_LEFT_PANEL_WIDTH = 114 

        scaled_width = int(BASE_WIDTH * self.scaling_factor)
        scaled_height = int(BASE_HEIGHT * self.scaling_factor)
        
        self.scaled_left_panel_width = int(BASE_LEFT_PANEL_WIDTH * self.scaling_factor)
        
        # (★★★) (修正 #3) 動態高度變數
        self.current_base_width = scaled_width
        self.base_window_height = scaled_height 
        self.non_content_height = int(20 * self.scaling_factor) # 估算: 標題/頁籤/日誌等非內容高度
        self.height_per_client_row = int((app_ui.CANVAS_ROW_HEIGHT + 20) * self.scaling_factor) # 每個客戶端 UI 的高度

        self.title("DSA新端輔助程式 v4.3 (寬網格/動態高度) by 石器推廣大使 陳財佑")
        
        try: self.iconbitmap("icon.ico")
        except tk.TclError: self.log("錯誤: 找不到 icon.ico 檔案。")
        
        self.geometry(f"{scaled_width}x{scaled_height}") 
        self.resizable(False, True) # 允許動態高度

        self.notebook = None
        self.tabs = {} 
        self.tab_frame_settings = None
        self.tab_frame_char = None
        self.client_checkboxes = [] 
        self.refresh_rate_combo = None
        self.setting_widgets = []
        
        # (★★★) (修正 #1) 返回「單一畫布」的 UI 引用
        # 結構: [{"frame": ttk.Labelframe, "canvas": tk.Canvas, "vars_list": [dict, dict, ...]}, None, ...]
        self.client_canvas_ui = [None] * MAX_CLIENTS
        
        self.client_selection_vars = [tk.IntVar() for _ in range(MAX_CLIENTS)]
        self.refresh_rate_var = tk.StringVar()
        
        self.client_data_slots = [self.create_empty_slot_data() for _ in range(MAX_CLIENTS)]
        
        self.data_queue = queue.Queue()
        self.command_queue = queue.Queue()
        self.worker_thread = None
        
        if not is_admin():
            self.title(f"{self.title()} (錯誤：請以管理員權限執行)")
            label = tk.Label(self, text="錯誤：\n必須以「系統管理員」權限執行此程式！", 
                             font=("Arial", 12), fg="red", padx=50, pady=50)
            label.pack()
        else:
            app_ui.create_main_widgets(self)
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.log("介面初始化完成。請點擊 '綁定石器'。")
            self.start_worker_thread()
            self.check_data_queue()
            
            # (★★★) (修正 #3) 首次調整高度
            self.adjust_window_height() 

    def create_empty_slot_data(self):
        return {
            "pid": None, "hwnd": None, "status": "未綁定", 
            "pm_handle": None, "module_base": None, 
            "game_state": "unbound", "account_name": "", 
            "char_data_cache": None, "pet_data_cache": [None] * 5, 
            "walk_address": None, "walk_original_byte": None, "walk_is_patched": False,
            "speed_address_1": None, "speed_address_2": None, "speed_original_bytes_1": None, 
            "speed_original_bytes_2": None, "speed_is_patched": False,
            "noclip_address": None, "noclip_original_bytes": None, "noclip_is_patched": False,
            "is_hidden": False
        }

    def log(self, message):
        print(f"[Main] {message}") 

    # --- (★★★) (修正 #3) 動態高度函式 ---
    
    def on_tab_changed(self, event=None):
        """(★★★) (修正 #3) 頁籤切換時，調整高度"""
        self.adjust_window_height()

    def adjust_window_height(self):
        """(★★★) (修正 #3) 根據當前頁籤和選中數量，動態調整視窗高度"""
        try:
            current_tab_text = self.notebook.tab(self.notebook.select(), "text")
        except Exception:
            current_tab_text = ""
        
        if current_tab_text != "人寵資料":
            # 不在人寵頁籤，使用基礎高度
            if self.winfo_height() != self.base_window_height:
                self.geometry(f"{self.current_base_width}x{self.base_window_height}")
            return
        
        # 在人寵頁籤，計算選中數量
        selected_count = 0
        for i in range(MAX_CLIENTS):
            if self.client_selection_vars[i].get() == 1 and self.client_data_slots[i]["status"] == "已綁定":
                selected_count += 1
        
        if selected_count == 0:
            new_height = self.base_window_height
        else:
            content_height = selected_count * self.height_per_client_row
            new_height = self.non_content_height + content_height + 70
            
            # 限制最大/最小高度
            max_height = self.winfo_screenheight() - 50
            new_height = max(self.base_window_height, min(new_height, max_height))
        
        if self.winfo_height() != new_height:
            self.geometry(f"{self.current_base_width}x{new_height}")

    # --- 執行緒 & 佇列管理 ---
    def start_worker_thread(self):
        if self.worker_thread is not None and self.worker_thread.is_alive():
            self.log("Worker 執行緒已在執行中。")
            return
        self.log("正在啟動 Worker 執行緒...")
        self.worker_thread = MemoryMonitorThread(
            self.data_queue, self.command_queue, self.client_data_slots 
        )
        self.worker_thread.start()
        self.on_refresh_rate_change() 

    def check_data_queue(self):
        try:
            full_data_package = self.data_queue.get_nowait()
            data_updated = False
            
            for i in range(MAX_CLIENTS):
                new_data = full_data_package[i]
                slot = self.client_data_slots[i]
                
                if new_data["status"] == "已失效" and slot["status"] == "已綁定":
                    self.log(f"窗口 {i+1} (PID {slot['pid']}) 句柄已失效，正在清理...")
                    try:
                        if slot["pm_handle"]: slot["pm_handle"].close()
                    except Exception as e:
                        self.log(f"  > 關閉失效句柄時出錯: {e}")
                    self.client_data_slots[i] = self.create_empty_slot_data()
                    self.client_selection_vars[i].set(0)
                    data_updated = True
                
                elif slot["status"] == "已綁定":
                    if (slot["account_name"] != new_data["account_name"] or
                        slot["char_data_cache"] != new_data["char_data_cache"] or
                        slot["pet_data_cache"] != new_data["pet_data_cache"]):
                        data_updated = True
                        
                    slot["account_name"] = new_data["account_name"]
                    slot["game_state"] = new_data["game_state"]
                    slot["char_data_cache"] = new_data["char_data_cache"]
                    slot["pet_data_cache"] = new_data["pet_data_cache"]
            
            if data_updated:
                self.update_client_list_ui() 
                self.update_all_displays()   

        except queue.Empty:
            pass 
        
        self.after(100, self.check_data_queue)


    # --- 核心功能：綁定與掃描 (Main Thread) ---
    def find_game_windows(self):
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
        self.log(f"--- 開始檢查綁定並搜尋新窗口 ---")
        current_pids = set()
        
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            if slot["status"] == "已失效":
                self.log(f"窗口 {i+1} (PID {slot['pid']}) 已被標記為失效, 清理...")
                try:
                    if slot["pm_handle"]: slot["pm_handle"].close_process()
                except Exception: pass
                self.client_data_slots[i] = self.create_empty_slot_data()
                self.client_selection_vars[i].set(0)
                self.update_client_list_ui(i)
                continue

            if slot["pid"] and slot["pm_handle"] and slot["module_base"]:
                current_pids.add(slot["pid"])
                self.log(f"窗口 {i+1} (PID {slot['pid']}) 檢查通過, 保留綁定。")
                continue

        found_windows = self.find_game_windows()
        new_windows = [w for w in found_windows if w[1] not in current_pids]

        if not new_windows:
            self.log("沒有找到新的窗口。")
            self.update_all_displays()
            return

        self.log(f"找到 {len(new_windows)} 個新窗口, 正在綁定...")
        new_window_iter = iter(new_windows)
        for i in range(MAX_CLIENTS):
            if self.client_data_slots[i]["pid"] is None: 
                try:
                    hwnd, pid = next(new_window_iter)
                    slot = self.client_data_slots[i]
                    slot["pid"] = pid
                    slot["hwnd"] = hwnd
                    self.scan_client_addresses(i) 
                    self.log(f"新窗口 (PID {pid}) 已綁定到窗口 {i+1}")
                    self.update_client_list_ui(i) 
                except StopIteration:
                    break 
        self.update_all_displays()

    def scan_client_addresses(self, slot_index):
        slot = self.client_data_slots[slot_index]
        pid = slot["pid"]
        self.log(f"--- 正在掃描 PID: {pid} ---")
        try:
            pm = pymem.Pymem(pid)
            slot["pm_handle"] = pm
            module = pymem.process.module_from_name(pm.process_handle, PROCESS_NAME)
            if not module:
                self.log(f"  > 錯誤 (PID: {pid}): 找不到 {PROCESS_NAME} 模組。")
                slot["status"] = "掃描失敗"
                pm.close(); slot["pm_handle"] = None; return
            
            slot["module_base"] = module.lpBaseOfDll
            self.log(f"  > (PID: {pid}) 找到模組基址 @ 0x{module.lpBaseOfDll:X}")

            # --- 1. 快速行走 ---
            try:
                addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_WALK)
                if addr:
                    patch_addr = addr + WALK_PATCH_OFFSET
                    curr_byte = pm.read_bytes(patch_addr, 1)[0]
                    slot["walk_address"] = patch_addr
                    if slot["walk_original_byte"] is None: slot["walk_original_byte"] = curr_byte
                    slot["walk_is_patched"] = (curr_byte == WALK_PATCHED_BYTE)
                    self.log(f"  > (PID: {pid}) 找到「行走」 @ 0x{patch_addr:X}")
                else: self.log(f"  > (PID: {pid}) 找不到「行走」特徵碼")
            except Exception as e: self.log(f"  > (PID: {pid}) 掃描「行走」出錯: {e}")

            # --- 2. 遊戲加速 ---
            try:
                addr1, addr2, is_patched_scan = None, None, False
                addr1 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_1_ORIGINAL)
                addr2 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_2_ORIGINAL)
                if not addr1 or not addr2:
                    self.log(f"  > (PID: {pid}) 未找到「加速」原始 AOB，嘗試掃描已修補 AOB...")
                    addr1 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_1_PATCHED)
                    addr2 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_2_PATCHED)
                    if addr1 and addr2: is_patched_scan = True 
                if addr1 and addr2:
                    patch_addr1, patch_addr2 = addr1 + SPEED_AOB_OFFSET, addr2 + SPEED_AOB_OFFSET
                    slot["speed_address_1"], slot["speed_address_2"] = patch_addr1, patch_addr2
                    if is_patched_scan:
                        slot["speed_is_patched"] = True
                        if slot["speed_original_bytes_1"] is None: self.log(f"  > (PID: {pid}) 警告：找到已修補的「加速」位址！")
                    else:
                        slot["speed_is_patched"] = False
                        slot["speed_original_bytes_1"] = pm.read_bytes(patch_addr1, len(NOP_PATCH))
                        slot["speed_original_bytes_2"] = pm.read_bytes(patch_addr2, len(NOP_PATCH))
                    self.log(f"  > (PID: {pid}) 找到「加速1」 @ 0x{patch_addr1:X}")
                else: self.log(f"  > (PID: {pid}) 找不到「加速」特徵碼")
            except Exception as e: self.log(f"  > (PID: {pid}) 掃描「加速」出錯: {e}")

            # --- 3. 穿牆行走 ---
            try:
                addr, is_patched_scan = None, False
                addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_NOCLIP_ORIGINAL)
                if not addr:
                    self.log(f"  > (PID: {pid}) 未找到「穿牆」原始 AOB，嘗試掃描已修補 AOB...")
                    addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_NOCLIP_PATCHED)
                    if addr: is_patched_scan = True 
                if addr:
                    patch_addr = addr + NOCLIP_PATCH_OFFSET
                    slot["noclip_address"] = patch_addr
                    if is_patched_scan:
                        slot["noclip_is_patched"] = True
                        if slot["noclip_original_bytes"] is None: self.log(f"  > (PID: {pid}) 警告：找到已修補的「穿牆」位址！")
                    else:
                        slot["noclip_is_patched"] = False
                        slot["noclip_original_bytes"] = pm.read_bytes(patch_addr, len(NOCLIP_PATCHED_BYTES))
                    self.log(f"  > (PID: {pid}) 找到「穿牆」 @ 0x{patch_addr:X}")
                else: self.log(f"  > (PID: {pid}) 找不到「穿牆」特徵碼")
            except Exception as e: self.log(f"  > (PID: {pid}) 掃描「穿牆」出錯: {e}")

            slot["status"] = "已綁定"
        except Exception as e:
            self.log(f"掃描時發生嚴重錯誤 (PID: {pid}): {e}")
            slot["status"] = "掃描失敗"
            if slot["pm_handle"]: 
                slot["pm_handle"].close_process(); slot["pm_handle"] = None


    # --- (★★★) (修正 #1)「單一畫布」GUI 更新 (Main Thread) ---
    def on_selection_change(self):
        self.update_all_displays()

    def update_all_displays(self):
        """(Main Thread) (單一畫布 優化) 動態建立/銷毀 UI"""
        
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

                # --- 2. (單一畫布 優化) 檢查「人寵資料」UI ---
                client_ui_pack = self.client_canvas_ui[i]
                
                if client_ui_pack is None:
                    # --- 2a. 建立 UI ---
                    self.log(f"窗口 {i+1}: 正在建立 單一畫布 UI...")
                    parent_frame = self.tab_frame_char.inner_frame
                    
                    client_frame = ttk.Labelframe(parent_frame, text=f"窗口 {i+1}", padding=0)
                    
                    canvas, all_vars_list = app_ui.create_client_info_canvas(client_frame, self)
                    
                    # 儲存 UI 引用
                    client_ui_pack = {
                        "frame": client_frame,
                        "canvas": canvas,
                        "vars_list": all_vars_list # [person_vars, pet1_vars, ...]
                    }
                    self.client_canvas_ui[i] = client_ui_pack
                
                # --- 2b. 顯示並更新 UI ---
                client_ui_pack["frame"].grid(row=i, column=0, sticky="ew", padx=5, pady=5) 
                client_ui_pack["frame"].config(text=slot.get("account_name", f"窗口 {i+1}"))
                
                canvas = client_ui_pack["canvas"]
                vars_list = client_ui_pack["vars_list"]
                
                # 更新人物 Canvas
                self._configure_character_canvas(canvas, vars_list[0], slot.get("char_data_cache"))
                
                # 更新寵物 Canvases
                pet_caches = slot.get("pet_data_cache", [None] * 5)
                for p_idx in range(5):
                    self._configure_pet_canvas(canvas, vars_list[p_idx + 1], pet_caches[p_idx], p_idx)

            else:
                # --- 3. 未勾選: 隱藏 (Settings) 並 銷毀 (Char Info Canvas) ---
                settings_ui["frame"].pack_forget()
                client_ui_pack = self.client_canvas_ui[i]
                if client_ui_pack is not None:
                    self.log(f"窗口 {i+1}: 正在銷毀 單一畫布 UI...")
                    client_ui_pack["frame"].destroy() 
                    self.client_canvas_ui[i] = None
        
        if self.tab_frame_settings:
            self.tab_frame_settings.inner_frame.event_generate("<Configure>")
        if self.tab_frame_char:
            self.tab_frame_char.inner_frame.event_generate("<Configure>")
            
        # (★★★) (修正 #3) 更新完 UI 後，調整視窗高度
        self.adjust_window_height()


    def _configure_character_canvas(self, canvas, person_vars, data):
        """(單一畫布 優化) 更新人物 Canvas Item ID"""
        if data:
            canvas.itemconfigure(person_vars["name"], text=data.get("name", "人物"))
            canvas.itemconfigure(person_vars["nickname"], text=data.get("nickname", "稱號"))
            canvas.itemconfigure(person_vars["lv"], text=data.get("lv", "--"))
            canvas.itemconfigure(person_vars["hp"], text=data.get("hp", "--/--"))
            canvas.itemconfigure(person_vars["mp"], text=data.get("mp", "--/--"))
            canvas.itemconfigure(person_vars["atk"], text=data.get("atk", "--"))
            canvas.itemconfigure(person_vars["def"], text=data.get("def", "--"))
            canvas.itemconfigure(person_vars["agi"], text=data.get("agi", "--"))
            canvas.itemconfigure(person_vars["vit"], text=data.get("vit", "--"))
            canvas.itemconfigure(person_vars["str"], text=data.get("str", "--"))
            canvas.itemconfigure(person_vars["sta"], text=data.get("sta", "--"))
            canvas.itemconfigure(person_vars["spd"], text=data.get("spd", "--"))

            rebirth_text = data.get("rebirth", "未知")
            rebirth_color = REBIRTH_COLOR_MAP.get(rebirth_text, DEFAULT_FG_COLOR)
            canvas.itemconfigure(person_vars["rebirth"], text=rebirth_text, fill=rebirth_color)

            charm_val = data.get("charm", 0) 
            charm_color = "red" if charm_val <= 60 else DEFAULT_FG_COLOR
            canvas.itemconfigure(person_vars["charm"], text=str(charm_val), fill=charm_color)

            # (★★★) 修正：動態屬性顯示 (v4.3.4)
            e, w, f, wi = data.get("element_raw", (0,0,0,0))
            
            # 1. 建立要顯示的屬性列表
            attributes_to_show = []
            if e > 0: attributes_to_show.append(("地", e//10, ELEMENT_COLOR_MAP["地"]))
            if w > 0: attributes_to_show.append(("水", w//10, ELEMENT_COLOR_MAP["水"]))
            if f > 0: attributes_to_show.append(("火", f//10, ELEMENT_COLOR_MAP["火"]))
            if wi > 0: attributes_to_show.append(("風", wi//10, ELEMENT_COLOR_MAP["風"]))

            # 2. 填入 4 個 UI 槽位
            for i in range(4):
                lbl_key = f"elem_{i+1}_lbl"
                val_key = f"elem_{i+1}_val"
                
                if i < len(attributes_to_show):
                    # 有資料可填
                    label, value, color = attributes_to_show[i]
                    canvas.itemconfigure(person_vars[lbl_key], text=label, fill=color)
                    canvas.itemconfigure(person_vars[val_key], text=f"{value}", fill=color)
                else:
                    # 清空多餘的槽位
                    canvas.itemconfigure(person_vars[lbl_key], text="")
                    canvas.itemconfigure(person_vars[val_key], text="")
        else:
            canvas.itemconfigure(person_vars["name"], text="人物")
            canvas.itemconfigure(person_vars["nickname"], text="稱號")
            canvas.itemconfigure(person_vars["lv"], text="--")
            canvas.itemconfigure(person_vars["hp"], text="--/--")
            canvas.itemconfigure(person_vars["mp"], text="--/--")
            canvas.itemconfigure(person_vars["atk"], text="--")
            canvas.itemconfigure(person_vars["def"], text="--")
            canvas.itemconfigure(person_vars["agi"], text="--")
            canvas.itemconfigure(person_vars["vit"], text="--")
            canvas.itemconfigure(person_vars["str"], text="--")
            canvas.itemconfigure(person_vars["sta"], text="--")
            canvas.itemconfigure(person_vars["spd"], text="--")
            canvas.itemconfigure(person_vars["rebirth"], text="--", fill=DEFAULT_FG_COLOR)
            canvas.itemconfigure(person_vars["charm"], text="--", fill=DEFAULT_FG_COLOR)
            
            # (★★★) 修正：在 else 情況下清除所有 4 個槽位 (v4.3.4)
            for i in range(4):
                if f"elem_{i+1}_lbl" in person_vars:
                    canvas.itemconfigure(person_vars[f"elem_{i+1}_lbl"], text="")
                    canvas.itemconfigure(person_vars[f"elem_{i+1}_val"], text="")


    def _configure_pet_canvas(self, canvas, pet_vars, data, p_idx):
        """(單一畫布 優化) 更新寵物 Canvas Item ID"""
        default_pet_title = app_ui.num_to_chinese(p_idx + 1)
        if data:
            # (★★★) v4.3.8 格式改為 [狀態]名字
            pet_name = data.get("name")
            display_name = pet_name if pet_name else f"寵物{default_pet_title}"
            
            status_text = data.get("status_text", "休")
            status_color_key = data.get("status_color_key", "未轉生") 
            status_color = REBIRTH_COLOR_MAP.get(status_color_key, DEFAULT_FG_COLOR)
            
            # 組合字串: "[休]凱比特"
            full_display_name = f"[{status_text}] {display_name}"
            
            # 更新名字 (含狀態) 並變色
            canvas.itemconfigure(pet_vars["name"], text=full_display_name, fill=status_color)
            
            # 其餘數值更新
            canvas.itemconfigure(pet_vars["nickname"], text=data.get("nickname", ""))
            canvas.itemconfigure(pet_vars["lv"], text=data.get("lv", "--"))
            canvas.itemconfigure(pet_vars["exp"], text=data.get("exp", "--"))
            canvas.itemconfigure(pet_vars["lack"], text=data.get("lack", "--"))
            canvas.itemconfigure(pet_vars["hp"], text=data.get("hp", "--/--"))
            canvas.itemconfigure(pet_vars["atk"], text=data.get("atk", "--"))
            canvas.itemconfigure(pet_vars["def"], text=data.get("def", "--"))
            canvas.itemconfigure(pet_vars["agi"], text=data.get("agi", "--"))
            
            rebirth_text = data.get("rebirth", "未知")
            rebirth_color = REBIRTH_COLOR_MAP.get(rebirth_text, DEFAULT_FG_COLOR)
            canvas.itemconfigure(pet_vars["rebirth"], text=rebirth_text, fill=rebirth_color)

            loyal_val = data.get("loyal", 100) 
            loyal_color = "red" if loyal_val <= 20 else DEFAULT_FG_COLOR
            canvas.itemconfigure(pet_vars["loyal"], text=str(loyal_val), fill=loyal_color)

            # (★★★) 動態屬性顯示
            e, w, f, wi = data.get("element_raw", (0,0,0,0))
            
            attributes_to_show = []
            if e > 0: attributes_to_show.append(("地", e//10, ELEMENT_COLOR_MAP["地"]))
            if w > 0: attributes_to_show.append(("水", w//10, ELEMENT_COLOR_MAP["水"]))
            if f > 0: attributes_to_show.append(("火", f//10, ELEMENT_COLOR_MAP["火"]))
            if wi > 0: attributes_to_show.append(("風", wi//10, ELEMENT_COLOR_MAP["風"]))

            for i in range(4):
                lbl_key = f"elem_{i+1}_lbl"
                val_key = f"elem_{i+1}_val"
                
                if i < len(attributes_to_show):
                    label, value, color = attributes_to_show[i]
                    canvas.itemconfigure(pet_vars[lbl_key], text=label, fill=color)
                    canvas.itemconfigure(pet_vars[val_key], text=f"{value}", fill=color)
                else:
                    canvas.itemconfigure(pet_vars[lbl_key], text="")
                    canvas.itemconfigure(pet_vars[val_key], text="")
        else:
            # (★★★) 預設狀態
            canvas.itemconfigure(pet_vars["name"], text=f"寵物{default_pet_title}", fill=DEFAULT_FG_COLOR)
            canvas.itemconfigure(pet_vars["nickname"], text="")
            canvas.itemconfigure(pet_vars["lv"], text="--")
            canvas.itemconfigure(pet_vars["exp"], text="--")
            canvas.itemconfigure(pet_vars["lack"], text="--")
            canvas.itemconfigure(pet_vars["hp"], text="--/--")
            canvas.itemconfigure(pet_vars["atk"], text="--")
            canvas.itemconfigure(pet_vars["def"], text="--")
            canvas.itemconfigure(pet_vars["agi"], text="--")
            canvas.itemconfigure(pet_vars["rebirth"], text="--", fill=DEFAULT_FG_COLOR)
            canvas.itemconfigure(pet_vars["loyal"], text="--", fill=DEFAULT_FG_COLOR)
            
            for i in range(4):
                if f"elem_{i+1}_lbl" in pet_vars:
                    canvas.itemconfigure(pet_vars[f"elem_{i+1}_lbl"], text="")
                    canvas.itemconfigure(pet_vars[f"elem_{i+1}_val"], text="")


    def update_client_list_ui(self, slot_index=None):
        indices_to_update = range(MAX_CLIENTS) if slot_index is None else [slot_index]
        for i in indices_to_update:
            slot = self.client_data_slots[i]
            checkbox = self.client_checkboxes[i] 
            if slot["status"] == "已綁定":
                checkbox.config(text=slot["account_name"], state="normal", fg="green")
            else:
                checkbox.config(text=f"窗口 {i+1}: {slot['status']}", state="disabled", fg="grey")
                
    def get_poll_interval_sec(self):
        value = self.refresh_rate_var.get()
        mapping = {
            '0.5s': 0.5, '1s': 1.0, '3s': 3.0, '5s': 5.0,
            '10s': 10.0, '60s': 60.0, '不刷新': None
        }
        return mapping.get(value, 3.0) 

    def on_refresh_rate_change(self, event=None):
        new_rate_sec = self.get_poll_interval_sec()
        self.log(f"刷新頻率變更為: {self.refresh_rate_var.get()}")
        if self.worker_thread and self.worker_thread.is_alive():
            self.command_queue.put({"action": "set_rate", "value": new_rate_sec})

    # --- (Main Thread) 核心功能：執行修補 (寫入) ---
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
        self.log(f"窗口 {client_index+1}: 快速行走 {'啟用' if is_checked else '還原'}...")
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
        self.log(f"窗口 {client_index+1}: 遊戲加速 {'啟用 (NOP)' if is_checked else '還原 (ADD)'}...")
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
        self.log(f"窗口 {client_index+1}: 穿牆行走 {'啟用' if is_checked else '還原'}...")
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
        self.log(f"窗口 {client_index+1}: {'隱藏' if is_checked else '顯示'}...")
        try:
            ctypes.windll.user32.ShowWindow(hwnd, command)
            slot["is_hidden"] = is_checked
        except Exception as e:
            self.log(f"隱藏窗口時出錯: {e}")
            self.setting_widgets[client_index]["vars"]["hide_sa"].set(not is_checked)

    def perform_write_byte(self, pm, patch_address, target_byte):
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

    # --- (★★★) (修正 #2) WinAPI & 關閉 (右鍵邏輯對調) ---

    def on_client_right_click_single(self, event, client_index):
        """(★★★) (修正 #2) 邏輯對調: 單擊 = 縮小"""
        slot = self.client_data_slots[client_index]
        if slot["status"] != "已綁定" or slot["hwnd"] is None: return
        hwnd = slot["hwnd"]
        try:
            self.log(f"窗口 {client_index+1}: 縮小")
            ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE) 
        except Exception as e:
            self.log(f"右鍵單擊(縮小)窗口 {client_index+1} 時出錯: {e}")

    def on_client_right_click_double(self, event, client_index):
        """(★★★) (修正 #2) 邏輯對調: 雙擊 = 激活/還原"""
        slot = self.client_data_slots[client_index]
        if slot["status"] != "已綁定" or slot["hwnd"] is None: return
        hwnd = slot["hwnd"]
        try:
            self.log(f"窗口 {client_index+1}: 激活")
            if ctypes.windll.user32.IsIconic(hwnd):
                ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception as e:
            self.log(f"右鍵雙擊(激活)窗口 {client_index+1} 時出錯: {e}")

    def on_closing(self):
        """(Main Thread) 關閉程式時的清理"""
        self.log("正在傳送停止訊號到 Worker 執行緒...")
        if self.worker_thread and self.worker_thread.is_alive():
            self.command_queue.put({"action": "stop"})
            self.worker_thread.join(timeout=2.0) 

        self.log("正在還原所有補丁並關閉句柄...")
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            pm = slot["pm_handle"]
            if not pm or slot["status"] != "已綁定": continue
            
            try:
                pm.read_int(slot["module_base"]) 
            except Exception:
                self.log(f"窗口 {i+1} (PID {slot['pid']}) 句柄已失效, 跳過還原。")
                try:
                    pm.close_process()
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
                pm.close_process()
                self.log(f"  > (PID: {slot['pid']}) 句柄已關閉。")
            except Exception as e:
                self.log(f"關閉句柄 (PID: {slot['pid']}) 時出錯: {e}")

        self.destroy()

# --- 程式主體 ---
if __name__ == "__main__":
    app = DSAHelperApp()
    app.mainloop()