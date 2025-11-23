# main.py
# (v4.10 - 整合道具列表上色/過濾、戰鬥狀態UI、自動高度與縮放)

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
import re # (重要) 用於處理說明文字的正規表示式

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
        # 1. DPI Awareness
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1) 
        except (AttributeError, OSError):
            try: ctypes.windll.user32.SetProcessDPIAware()
            except: pass
        
        # 2. Initialize
        super().__init__()
        
        # 3. DPI 偵測
        try:
            window_handle = self.winfo_id()
            self.REAL_DPI = ctypes.windll.user32.GetDpiForWindow(window_handle)
            self.SYSTEM_DPI_SCALING = self.REAL_DPI / 96.0
        except Exception as e:
            self.log(f"[ERROR] DPI 偵測失敗: {e}。將使用預設值 1.0")
            self.SYSTEM_DPI_SCALING = 1.0 

        self.log(f"--- 系統 DPI Scale: {self.SYSTEM_DPI_SCALING}")

        # 初始化使用者變數
        self.user_scale = 1.0  # 預設縮放 100%
        
        # UI 變數
        self.refresh_rate_var = tk.StringVar(value='3s')
        self.zoom_var = tk.StringVar(value='100%') 
        self.auto_height_var = tk.IntVar(value=1) # 自動高度開關 (預設開啟)
        
        self.client_selection_vars = [tk.IntVar() for _ in range(MAX_CLIENTS)]
        
        # 初始化 UI 容器 (防止 rebuild_ui 報錯)
        self.client_checkboxes = []
        self.setting_widgets = []
        self.client_canvas_ui = [None] * MAX_CLIENTS
        self.client_item_ui = {}   # 道具列表 UI 參照
        self.client_battle_ui = {} # 戰鬥狀態 UI 參照
        self.tabs = {}
        
        self.client_data_slots = [self.create_empty_slot_data() for _ in range(MAX_CLIENTS)]
        self.data_queue = queue.Queue()
        self.command_queue = queue.Queue()
        self.worker_thread = None

        # 4. 計算初始佈局參數
        self.calc_layout_params()

        # 5. 視窗基本設定
        self.title("DSA Helper v4.10 (完整版)")
        try: self.iconbitmap("icon.ico")
        except: pass
        
        # 6. 建立 UI
        self.rebuild_ui(first_run=True)

        # 7. 啟動與權限檢查
        if not is_admin():
            self.title(f"{self.title()} (錯誤：請以管理員權限執行)")
            label = tk.Label(self, text="錯誤：\n必須以「系統管理員」權限執行此程式！", 
                             fg="red", padx=50, pady=50)
            label.pack()
        else:
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.log("介面初始化完成。請點擊 '綁定石器'。")
            self.start_worker_thread()
            self.check_data_queue()
            self.adjust_window_height()

    def calc_layout_params(self):
        """(新增) 獨立的版面參數計算，支援使用者縮放"""
        
        # 根據系統 DPI 選擇 4K 基礎參數
        if self.SYSTEM_DPI_SCALING <= 1.1: 
            BASE_PARAMS_4K = app_ui.PARAMS_4K_100
        elif self.SYSTEM_DPI_SCALING <= 1.35: 
            BASE_PARAMS_4K = app_ui.PARAMS_4K_125
        else: 
            BASE_PARAMS_4K = app_ui.PARAMS_4K_150

        # 最終比例 = 1.0 * 使用者自訂縮放
        RESOLUTION_RATIO = 1.0 * self.user_scale
        
        self.log(f"--- 重算佈局: User Scale={self.user_scale}, Final Ratio={RESOLUTION_RATIO:.2f}")

        # 寫入 app_ui
        app_ui.RESOLUTION_RATIO = RESOLUTION_RATIO 
        
        # 基礎介面參數
        app_ui.LAYOUT_APP_BASE_WIDTH = int(BASE_PARAMS_4K["APP_BASE_WIDTH"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_APP_BASE_HEIGHT = int(BASE_PARAMS_4K["APP_BASE_HEIGHT"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_LEFT_PANEL_WIDTH = int(BASE_PARAMS_4K["LEFT_PANEL_WIDTH"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_NON_CONTENT_HEIGHT = int(BASE_PARAMS_4K["NON_CONTENT_HEIGHT"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_ROW_PADDING = int(BASE_PARAMS_4K["CANVAS_ROW_PADDING"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_LEFT_CHECKBOX_PADY = int(BASE_PARAMS_4K["LEFT_CHECKBOX_PADY"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_SETTINGS_CHECKBOX_PADY = int(BASE_PARAMS_4K["SETTINGS_CHECKBOX_PADY"] * RESOLUTION_RATIO)

        # 人寵 Canvas 參數
        app_ui.LAYOUT_CANVAS_BASE_FONT_SIZE = max(int(BASE_PARAMS_4K["CANVAS_FONT_SIZE"] * RESOLUTION_RATIO), 1)
        app_ui.LAYOUT_CANVAS_BASE_Y_START = int(BASE_PARAMS_4K["CANVAS_Y_START"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_BASE_Y_STEP = int(BASE_PARAMS_4K["CANVAS_Y_STEP"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_BASE_COL_WIDTH = int(BASE_PARAMS_4K["CANVAS_COL_WIDTH"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_BASE_COL_PADDING = int(BASE_PARAMS_4K["CANVAS_COL_PADDING"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_BASE_START_X = int(BASE_PARAMS_4K["CANVAS_START_X"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_X_VALUE_1 = int(BASE_PARAMS_4K["CANVAS_X_VAL_1"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_X_LABEL_2 = int(BASE_PARAMS_4K["CANVAS_X_LBL_2"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_X_VALUE_2 = int(BASE_PARAMS_4K["CANVAS_X_VAL_2"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_ELEM_VAL_OFFSET = int(BASE_PARAMS_4K["CANVAS_ELEM_VAL_OFFSET"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_ELEM_STEP = int(BASE_PARAMS_4K["CANVAS_ELEM_STEP"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_PERSON_Y_ADJUST_1 = int(BASE_PARAMS_4K["CANVAS_PERSON_Y_ADJ_1"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_PERSON_Y_ADJUST_2 = int(BASE_PARAMS_4K["CANVAS_PERSON_Y_ADJ_2"] * RESOLUTION_RATIO)
        
        # 道具列表 Canvas 參數
        app_ui.LAYOUT_ITEM_CANVAS_HEIGHT = int(BASE_PARAMS_4K["ITEM_CANVAS_HEIGHT"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_ITEM_FONT_SIZE = max(int(BASE_PARAMS_4K["ITEM_FONT_SIZE"] * RESOLUTION_RATIO), 1)
        app_ui.LAYOUT_ITEM_ROW_HEIGHT = int(BASE_PARAMS_4K["ITEM_ROW_HEIGHT"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_ITEM_COL_1_X = int(BASE_PARAMS_4K["ITEM_COL_1_X"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_ITEM_COL_2_X = int(BASE_PARAMS_4K["ITEM_COL_2_X"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_ITEM_SEPARATOR_X = int(BASE_PARAMS_4K["ITEM_SEPARATOR_X"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_ITEM_HEADER_Y_OFFSET = int(BASE_PARAMS_4K["ITEM_HEADER_Y_OFFSET"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_ITEM_ACCOUNT_PAD_Y = int(BASE_PARAMS_4K["ITEM_ACCOUNT_PAD_Y"] * RESOLUTION_RATIO)
        
        # 戰鬥狀態 Canvas 參數 (v4.10)
        app_ui.LAYOUT_BATTLE_CANVAS_HEIGHT = int(BASE_PARAMS_4K["BATTLE_CANVAS_HEIGHT"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_BATTLE_FONT_SIZE = max(int(BASE_PARAMS_4K["BATTLE_FONT_SIZE"] * RESOLUTION_RATIO), 1)
        app_ui.LAYOUT_BATTLE_ROW_HEIGHT = int(BASE_PARAMS_4K["BATTLE_ROW_HEIGHT"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_BATTLE_COL_1_X = int(BASE_PARAMS_4K["BATTLE_COL_1_X"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_BATTLE_COL_2_X = int(BASE_PARAMS_4K["BATTLE_COL_2_X"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_BATTLE_SEPARATOR_X = int(BASE_PARAMS_4K["BATTLE_SEPARATOR_X"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_BATTLE_HEADER_Y_OFFSET = int(BASE_PARAMS_4K["BATTLE_HEADER_Y_OFFSET"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_BATTLE_ACCOUNT_PAD_Y = int(BASE_PARAMS_4K["BATTLE_ACCOUNT_PAD_Y"] * RESOLUTION_RATIO)

        # 計算衍生高度
        app_ui.BASE_CANVAS_ROW_HEIGHT = (app_ui.LAYOUT_CANVAS_BASE_Y_START + (10 * app_ui.LAYOUT_CANVAS_BASE_Y_STEP) + app_ui.LAYOUT_CANVAS_BASE_Y_START)
        app_ui.FINAL_CANVAS_ROW_TOTAL_HEIGHT = (app_ui.BASE_CANVAS_ROW_HEIGHT + app_ui.LAYOUT_CANVAS_ROW_PADDING)

        # 更新主視窗實例變數
        self.scaled_left_panel_width = app_ui.LAYOUT_LEFT_PANEL_WIDTH
        self.current_base_width = app_ui.LAYOUT_APP_BASE_WIDTH
        self.base_window_height = app_ui.LAYOUT_APP_BASE_HEIGHT
        self.non_content_height = app_ui.LAYOUT_NON_CONTENT_HEIGHT
        self.height_per_client_row = app_ui.FINAL_CANVAS_ROW_TOTAL_HEIGHT

    def rebuild_ui(self, first_run=False):
        """重建整個 UI 介面"""
        if not first_run:
            for widget in self.winfo_children():
                if isinstance(widget, tk.Widget):
                    widget.destroy()
            
            # 重置 UI 引用 (保留數據 slot)
            self.client_checkboxes = []
            self.setting_widgets = []
            self.client_canvas_ui = [None] * MAX_CLIENTS
            
            if hasattr(self, "client_item_ui"): self.client_item_ui = {}
            if hasattr(self, "client_battle_ui"): self.client_battle_ui = {}
                
            self.notebook = None
            self.tab_frame_settings = None
            self.tab_frame_char = None
            self.refresh_rate_combo = None 

        # 重新建立 UI
        app_ui.create_main_widgets(self)
        
        # 調整視窗大小
        self.geometry(f"{self.current_base_width}x{self.base_window_height}")
        self.resizable(False, True)
        
        if not first_run:
            self.update_client_list_ui()
            self.update_all_displays()
            self.adjust_window_height()

    def on_zoom_change(self, event):
        """使用者選擇縮放比例時觸發"""
        val_str = self.zoom_var.get().replace('%', '')
        try:
            scale_val = float(val_str) / 100.0
        except:
            scale_val = 1.0
            
        if scale_val != self.user_scale:
            self.user_scale = scale_val
            self.log(f"使用者切換縮放: {self.user_scale*100}%")
            self.calc_layout_params()
            self.rebuild_ui()

    def create_empty_slot_data(self):
        """初始化資料結構 (含道具與戰鬥數據快取)"""
        return {
            "pid": None, "hwnd": None, "status": "未綁定", 
            "pm_handle": None, "module_base": None, 
            "game_state": "unbound", "account_name": "", 
            "char_data_cache": None, 
            "pet_data_cache": [None] * 5, 
            "item_data_cache": {}, 
            "battle_data_cache": {}, # (預留) 戰鬥數據
            "walk_address": None, "walk_original_byte": None, "walk_is_patched": False,
            "speed_address_1": None, "speed_address_2": None, "speed_original_bytes_1": None, 
            "speed_original_bytes_2": None, "speed_is_patched": False,
            "noclip_address": None, "noclip_original_bytes": None, "noclip_is_patched": False,
            "is_hidden": False
        }

    def log(self, message):
        print(f"[Main] {message}") 

    def on_tab_changed(self, event=None):
        self.adjust_window_height()

    def adjust_window_height(self):
        """(修改) 自動調整視窗高度 (自動偵測法)"""
        
        # 1. 檢查自動縮放開關
        if self.auto_height_var.get() == 0:
            return

        self.update_idletasks() # 強制更新排版

        try:
            current_tab_text = self.notebook.tab(self.notebook.select(), "text")
        except Exception:
            current_tab_text = ""
            
        target_content_frame = None
        if current_tab_text == "人寵資料":
            if hasattr(self, "tab_frame_char") and self.tab_frame_char:
                target_content_frame = self.tab_frame_char.inner_frame
        elif current_tab_text == "道具列表":
            if hasattr(self, "tab_frame_items") and self.tab_frame_items:
                target_content_frame = self.tab_frame_items.inner_frame
        elif current_tab_text == "戰鬥狀態":
            if hasattr(self, "tab_frame_battle") and self.tab_frame_battle:
                target_content_frame = self.tab_frame_battle.inner_frame

        target_height = self.base_window_height
        
        has_selection = False
        for i in range(MAX_CLIENTS):
            if self.client_selection_vars[i].get() == 1 and self.client_data_slots[i]["status"] == "已綁定":
                has_selection = True
                break

        if has_selection and target_content_frame:
            content_h = target_content_frame.winfo_reqheight()
            
            # 加上頁籤標題列與緩衝
            tab_header_h = int(45 * self.user_scale)
            padding_h = int(10 * self.user_scale)
            calc_h = tab_header_h + content_h + padding_h
            
            # 左側面板最小高度防護
            left_panel_min_h = int(220 * self.user_scale)
            target_height = max(calc_h, left_panel_min_h)

        max_h = self.winfo_screenheight() - 60
        
        if not has_selection or current_tab_text == "遊戲設置":
            final_height = self.base_window_height
        else:
            final_height = min(int(target_height), max_h)
            final_height = max(final_height, int(220 * self.user_scale))

        if self.winfo_height() != final_height:
            self.geometry(f"{self.current_base_width}x{final_height}")

    def start_worker_thread(self):
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
        self.worker_thread = MemoryMonitorThread(
            self.data_queue, self.command_queue, self.client_data_slots 
        )
        self.worker_thread.start()
        self.on_refresh_rate_change() 

    def check_data_queue(self):
        """(修正) 處理資料回傳 (補上戰鬥數據更新)"""
        try:
            full_data_package = self.data_queue.get_nowait()
            account_name_updated = False 
            
            for i in range(MAX_CLIENTS):
                new_data = full_data_package[i]
                slot = self.client_data_slots[i]
                client_ui_pack = self.client_canvas_ui[i]

                if new_data["status"] == "已失效" and slot["status"] == "已綁定":
                    # ... (省略清理代碼，保持不變) ...
                    self.update_all_displays() 
                
                elif slot["status"] == "已綁定":
                    if slot["account_name"] != new_data["account_name"]:
                        account_name_updated = True
                        slot["account_name"] = new_data["account_name"]
                        self.update_all_displays() 
                    
                    slot["game_state"] = new_data["game_state"]
                    
                    # 更新資料快取
                    slot["char_data_cache"] = new_data["char_data_cache"]
                    slot["pet_data_cache"] = new_data["pet_data_cache"]
                    slot["item_data_cache"] = new_data["item_data_cache"]
                    
                    # (★★★) 關鍵修正：補上這行，UI 才能拿到戰鬥數據！ (★★★)
                    slot["battle_data_cache"] = new_data.get("battle_data_cache", {})

                    # ... (省略人寵 UI 更新代碼，保持不變) ...
            
            if account_name_updated:
                self.update_client_list_ui()

            # 檢查當前分頁並刷新
            try:
                if self.notebook.select():
                    current_tab_text = self.notebook.tab(self.notebook.select(), "text")
                    if current_tab_text == "道具列表":
                        self._update_items_tab_ui()
                    elif current_tab_text == "戰鬥狀態":
                        self._update_battle_tab_ui()
            except Exception: pass

        except queue.Empty:
            pass 
        
        self.after(100, self.check_data_queue)

    def _update_items_tab_ui(self):
        """動態更新道具列表 (Canvas + 上色 + 過濾)"""
        if not hasattr(app_ui, "create_item_client_panel") or not hasattr(self, "tab_frame_items"):
            return
        if not hasattr(self, "client_item_ui"):
            self.client_item_ui = {} 

        parent_frame = self.tab_frame_items.inner_frame
        structure_changed = False

        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            should_show = (self.client_selection_vars[i].get() == 1 and slot["status"] == "已綁定")
            
            if not should_show:
                if i in self.client_item_ui:
                    self.client_item_ui[i]["frame"].destroy()
                    del self.client_item_ui[i]
                    structure_changed = True
                continue
            
            if i not in self.client_item_ui:
                ui_pack = app_ui.create_item_client_panel(parent_frame, slot["account_name"])
                self.client_item_ui[i] = ui_pack
                structure_changed = True
                
            ui_data = self.client_item_ui[i]
            if ui_data["frame"].cget("text") != slot["account_name"]:
                ui_data["frame"].config(text=slot["account_name"]) 
            
            canvas = ui_data["canvas"]
            text_ids = ui_data["ids"]
            items_cache = slot.get("item_data_cache", {})
            
            from constants import EQUIP_MAPPING, ITEM_COLOR_RULES, DEFAULT_ITEM_COLOR
            import re 

            for idx, tid in text_ids.items():
                item = items_cache.get(idx)
                
                if idx < 0:
                    prefix = EQUIP_MAPPING.get(idx, "??")
                else:
                    prefix = f"{idx+1:02d}"
                
                if not item:
                    canvas.itemconfigure(tid, text=f"{prefix}: (空)", fill="#888888")
                    continue
                
                stack_str = f" [{item['stack']}]" if item['stack'] > 1 else ""
                
                dur_text = str(item['dur']).strip()
                dur_str = ""
                if dur_text and dur_text != "0/0" and "不會損壞" not in dur_text:
                    dur_str = f" {dur_text}"
                    
                desc_str = ""
                if item['desc']:
                    cleaned_desc = " ".join(item['desc'].split())
                    cleaned_desc = re.sub(r'\s*([+-])\s*', r'\1', cleaned_desc)
                    desc_str = f" {{{cleaned_desc}}}"
                
                full_text = f"{prefix}:{stack_str} {item['name']}{desc_str}{dur_str}"
                
                # 上色邏輯
                final_color = DEFAULT_ITEM_COLOR
                item_name = item['name']
                found_color = False
                for color_code, keywords in ITEM_COLOR_RULES.items():
                    for kw in keywords:
                        if kw in item_name:
                            final_color = color_code
                            found_color = True
                            break
                    if found_color: break
                
                canvas.itemconfigure(tid, text=full_text, fill=final_color)
        
        if structure_changed:
            self.tab_frame_items.inner_frame.event_generate("<Configure>")
            self.adjust_window_height()

    # --- main.py 修改部分 ---

    def _update_battle_tab_ui(self):
        """(修改) 動態更新戰鬥狀態 UI (含斷線顯示)"""
        if not hasattr(app_ui, "create_battle_client_panel") or not hasattr(self, "tab_frame_battle"):
            return
        if not hasattr(self, "client_battle_ui"):
            self.client_battle_ui = {} 

        parent_frame = self.tab_frame_battle.inner_frame
        structure_changed = False 

        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            should_show = (self.client_selection_vars[i].get() == 1 and slot["status"] == "已綁定")
            
            if not should_show:
                if i in self.client_battle_ui:
                    self.client_battle_ui[i]["frame"].destroy()
                    del self.client_battle_ui[i]
                    structure_changed = True
                continue
            
            if i not in self.client_battle_ui:
                ui_pack = app_ui.create_battle_client_panel(parent_frame, slot["account_name"])
                self.client_battle_ui[i] = ui_pack
                structure_changed = True
                
            ui_data = self.client_battle_ui[i]
            if ui_data["frame"].cget("text") != slot["account_name"]:
                ui_data["frame"].config(text=slot["account_name"]) 
            
            canvas = ui_data["canvas"]
            text_ids = ui_data["ids"]
            
            battle_data = slot.get("battle_data_cache", {})
            game_state = slot.get("game_state", 0)
            
            # (修改) 狀態判斷邏輯
            for pos_id, tid in text_ids.items():
                
                if game_state == 11:
                    # 斷線狀態
                    canvas.itemconfigure(tid, text=f"{pos_id}: (斷線)", fill="red")
                    continue

                if game_state != 10:
                    # 非戰鬥狀態
                    status_text = f"(狀態: {game_state})" if game_state != 0 else "(未讀取)"
                    canvas.itemconfigure(tid, text=f"{pos_id}: {status_text}", fill="#888888")
                    continue

                # 戰鬥中 (State 10)
                info_str = battle_data.get(pos_id)
                
                if info_str:
                    canvas.itemconfigure(tid, text=info_str, fill="black")
                else:
                    # 有戰鬥狀態但沒資料 (代表解析失敗或該位置無單位)
                    canvas.itemconfigure(tid, text=f"{pos_id}: --", fill="#CCCCCC")
            
        if structure_changed:
            self.tab_frame_battle.inner_frame.event_generate("<Configure>")
            self.adjust_window_height()

    # --- 核心功能：綁定與掃描 ---
    def find_game_windows(self):
        found_windows = []
        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
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
                try:
                    if slot["pm_handle"]: slot["pm_handle"].close_process()
                except Exception: pass
                self.client_data_slots[i] = self.create_empty_slot_data()
                self.client_selection_vars[i].set(0)
                self.update_client_list_ui(i)
                continue

            if slot["pid"] and slot["pm_handle"] and slot["module_base"]:
                current_pids.add(slot["pid"])
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

            # 1. 快速行走
            try:
                addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_WALK)
                if addr:
                    patch_addr = addr + WALK_PATCH_OFFSET
                    curr_byte = pm.read_bytes(patch_addr, 1)[0]
                    slot["walk_address"] = patch_addr
                    if slot["walk_original_byte"] is None: slot["walk_original_byte"] = curr_byte
                    slot["walk_is_patched"] = (curr_byte == WALK_PATCHED_BYTE)
            except Exception: pass

            # 2. 遊戲加速
            try:
                addr1, addr2, is_patched_scan = None, None, False
                addr1 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_1_ORIGINAL)
                addr2 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_2_ORIGINAL)
                if not addr1 or not addr2:
                    addr1 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_1_PATCHED)
                    addr2 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_2_PATCHED)
                    if addr1 and addr2: is_patched_scan = True 
                if addr1 and addr2:
                    patch_addr1, patch_addr2 = addr1 + SPEED_AOB_OFFSET, addr2 + SPEED_AOB_OFFSET
                    slot["speed_address_1"], slot["speed_address_2"] = patch_addr1, patch_addr2
                    if is_patched_scan:
                        slot["speed_is_patched"] = True
                    else:
                        slot["speed_is_patched"] = False
                        slot["speed_original_bytes_1"] = pm.read_bytes(patch_addr1, len(NOP_PATCH))
                        slot["speed_original_bytes_2"] = pm.read_bytes(patch_addr2, len(NOP_PATCH))
            except Exception: pass

            # 3. 穿牆行走
            try:
                addr, is_patched_scan = None, False
                addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_NOCLIP_ORIGINAL)
                if not addr:
                    addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_NOCLIP_PATCHED)
                    if addr: is_patched_scan = True 
                if addr:
                    patch_addr = addr + NOCLIP_PATCH_OFFSET
                    slot["noclip_address"] = patch_addr
                    if is_patched_scan:
                        slot["noclip_is_patched"] = True
                    else:
                        slot["noclip_is_patched"] = False
                        slot["noclip_original_bytes"] = pm.read_bytes(patch_addr, len(NOCLIP_PATCHED_BYTES))
            except Exception: pass

            slot["status"] = "已綁定"
        except Exception as e:
            self.log(f"掃描時發生嚴重錯誤 (PID: {pid}): {e}")
            slot["status"] = "掃描失敗"
            if slot["pm_handle"]: 
                slot["pm_handle"].close_process(); slot["pm_handle"] = None

    # --- UI 更新 (人寵部分) ---
    def on_selection_change(self):
        self.update_all_displays()

    def update_all_displays(self):
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            is_selected = self.client_selection_vars[i].get() == 1
            is_bound = slot["status"] == "已綁定"
            settings_ui = self.setting_widgets[i]
            
            if is_selected and is_bound:
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

                client_ui_pack = self.client_canvas_ui[i]
                if client_ui_pack is None:
                    parent_frame = self.tab_frame_char.inner_frame
                    client_frame = ttk.Labelframe(parent_frame, text=f"窗口 {i+1}", padding=0)
                    canvas, all_vars_list = app_ui.create_client_info_canvas(client_frame, self)
                    client_ui_pack = {
                        "frame": client_frame,
                        "canvas": canvas,
                        "vars_list": all_vars_list
                    }
                    self.client_canvas_ui[i] = client_ui_pack
                
                client_ui_pack["frame"].grid(row=i, column=0, sticky="ew", padx=5, pady=5) 
                client_ui_pack["frame"].config(text=slot.get("account_name", f"窗口 {i+1}"))
                
                canvas = client_ui_pack["canvas"]
                vars_list = client_ui_pack["vars_list"]
                self._configure_character_canvas(canvas, vars_list[0], slot.get("char_data_cache"))
                pet_caches = slot.get("pet_data_cache", [None] * 5)
                for p_idx in range(5):
                    self._configure_pet_canvas(canvas, vars_list[p_idx + 1], pet_caches[p_idx], p_idx)

            else:
                settings_ui["frame"].pack_forget()
                client_ui_pack = self.client_canvas_ui[i]
                if client_ui_pack is not None:
                    client_ui_pack["frame"].destroy() 
                    self.client_canvas_ui[i] = None
        
        if self.tab_frame_settings:
            self.tab_frame_settings.inner_frame.event_generate("<Configure>")
        if self.tab_frame_char:
            self.tab_frame_char.inner_frame.event_generate("<Configure>")
            
        self.adjust_window_height()

    def _configure_character_canvas(self, canvas, person_vars, data):
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
                    canvas.itemconfigure(person_vars[lbl_key], text=label, fill=color)
                    canvas.itemconfigure(person_vars[val_key], text=f"{value}", fill=color)
                else:
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
            for i in range(4):
                if f"elem_{i+1}_lbl" in person_vars:
                    canvas.itemconfigure(person_vars[f"elem_{i+1}_lbl"], text="")
                    canvas.itemconfigure(person_vars[f"elem_{i+1}_val"], text="")

    def _granular_update_char_canvas(self, canvas, person_vars, old_data, new_data):
        if not new_data: 
            if old_data: self._configure_character_canvas(canvas, person_vars, None)
            return
        
        if not old_data: 
            self._configure_character_canvas(canvas, person_vars, new_data)
            return

        try:
            if old_data["name"] != new_data["name"]: canvas.itemconfigure(person_vars["name"], text=new_data.get("name", "人物"))
            if old_data["nickname"] != new_data["nickname"]: canvas.itemconfigure(person_vars["nickname"], text=new_data.get("nickname", "稱號"))
            if old_data["lv"] != new_data["lv"]: canvas.itemconfigure(person_vars["lv"], text=new_data.get("lv", "--"))
            if old_data["hp"] != new_data["hp"]: canvas.itemconfigure(person_vars["hp"], text=new_data.get("hp", "--/--"))
            if old_data["mp"] != new_data["mp"]: canvas.itemconfigure(person_vars["mp"], text=new_data.get("mp", "--/--"))
            if old_data["atk"] != new_data["atk"]: canvas.itemconfigure(person_vars["atk"], text=new_data.get("atk", "--"))
            if old_data["def"] != new_data["def"]: canvas.itemconfigure(person_vars["def"], text=new_data.get("def", "--"))
            if old_data["agi"] != new_data["agi"]: canvas.itemconfigure(person_vars["agi"], text=new_data.get("agi", "--"))
            if old_data["vit"] != new_data["vit"]: canvas.itemconfigure(person_vars["vit"], text=new_data.get("vit", "--"))
            if old_data["str"] != new_data["str"]: canvas.itemconfigure(person_vars["str"], text=new_data.get("str", "--"))
            if old_data["sta"] != new_data["sta"]: canvas.itemconfigure(person_vars["sta"], text=new_data.get("sta", "--"))
            if old_data["spd"] != new_data["spd"]: canvas.itemconfigure(person_vars["spd"], text=new_data.get("spd", "--"))

            if old_data["rebirth"] != new_data["rebirth"]:
                rebirth_text = new_data.get("rebirth", "未知")
                rebirth_color = REBIRTH_COLOR_MAP.get(rebirth_text, DEFAULT_FG_COLOR)
                canvas.itemconfigure(person_vars["rebirth"], text=rebirth_text, fill=rebirth_color)

            if old_data["charm"] != new_data["charm"]:
                charm_val = new_data.get("charm", 0) 
                charm_color = "red" if charm_val <= 60 else DEFAULT_FG_COLOR
                canvas.itemconfigure(person_vars["charm"], text=str(charm_val), fill=charm_color)

            if old_data["element_raw"] != new_data["element_raw"]:
                self._configure_character_canvas(canvas, person_vars, new_data)
        except Exception:
            self._configure_character_canvas(canvas, person_vars, new_data) 

    def _configure_pet_canvas(self, canvas, pet_vars, data, p_idx):
        default_pet_title = app_ui.num_to_chinese(p_idx + 1)
        if data:
            pet_name = data.get("name")
            display_name = pet_name if pet_name else f"寵物{default_pet_title}"
            
            status_text = data.get("status_text", "休")
            status_color_key = data.get("status_color_key", "未轉生") 
            status_color = REBIRTH_COLOR_MAP.get(status_color_key, DEFAULT_FG_COLOR)
            
            full_display_name = f"[{status_text}] {display_name}"
            canvas.itemconfigure(pet_vars["name"], text=full_display_name, fill=status_color)
            
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

    def _granular_update_pet_canvas(self, canvas, pet_vars, p_idx, old_data, new_data):
        if not new_data: 
            if old_data: self._configure_pet_canvas(canvas, pet_vars, None, p_idx)
            return
        if not old_data: 
            self._configure_pet_canvas(canvas, pet_vars, new_data, p_idx)
            return

        try:
            if old_data.get("status_text") != new_data.get("status_text") or old_data.get("name") != new_data.get("name"):
                self._configure_pet_canvas(canvas, pet_vars, new_data, p_idx) 
            else:
                if old_data["nickname"] != new_data["nickname"]: canvas.itemconfigure(pet_vars["nickname"], text=new_data.get("nickname", ""))
                if old_data["lv"] != new_data["lv"]: canvas.itemconfigure(pet_vars["lv"], text=new_data.get("lv", "--"))
                if old_data["exp"] != new_data["exp"]: canvas.itemconfigure(pet_vars["exp"], text=new_data.get("exp", "--"))
                if old_data["lack"] != new_data["lack"]: canvas.itemconfigure(pet_vars["lack"], text=new_data.get("lack", "--"))
                if old_data["hp"] != new_data["hp"]: canvas.itemconfigure(pet_vars["hp"], text=new_data.get("hp", "--/--"))
                if old_data["atk"] != new_data["atk"]: canvas.itemconfigure(pet_vars["atk"], text=new_data.get("atk", "--"))
                if old_data["def"] != new_data["def"]: canvas.itemconfigure(pet_vars["def"], text=new_data.get("def", "--"))
                if old_data["agi"] != new_data["agi"]: canvas.itemconfigure(pet_vars["agi"], text=new_data.get("agi", "--"))
                
                if old_data["rebirth"] != new_data["rebirth"]:
                    rebirth_text = new_data.get("rebirth", "未知")
                    rebirth_color = REBIRTH_COLOR_MAP.get(rebirth_text, DEFAULT_FG_COLOR)
                    canvas.itemconfigure(pet_vars["rebirth"], text=rebirth_text, fill=rebirth_color)

                if old_data["loyal"] != new_data["loyal"]:
                    loyal_val = new_data.get("loyal", 100) 
                    loyal_color = "red" if loyal_val <= 20 else DEFAULT_FG_COLOR
                    canvas.itemconfigure(pet_vars["loyal"], text=str(loyal_val), fill=loyal_color)

                if old_data["element_raw"] != new_data["element_raw"]:
                    self._configure_pet_canvas(canvas, pet_vars, new_data, p_idx)
        except Exception:
            self._configure_pet_canvas(canvas, pet_vars, new_data, p_idx)

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
        if self.worker_thread and self.worker_thread.is_alive():
            self.command_queue.put({"action": "set_rate", "value": new_rate_sec})

    # --- 寫入操作 ---
    def on_toggle_walk(self, client_index):
        slot = self.client_data_slots[client_index]
        pm = slot["pm_handle"]
        addr, orig_byte = slot["walk_address"], slot["walk_original_byte"]
        if pm is None or addr is None:
            self.setting_widgets[client_index]["vars"]["fast_walk"].set(not self.setting_widgets[client_index]["vars"]["fast_walk"].get())
            return
        is_checked = self.setting_widgets[client_index]["vars"]["fast_walk"].get()
        target_byte = WALK_PATCHED_BYTE if is_checked else orig_byte
        if self.perform_write_byte(pm, addr, target_byte): slot["walk_is_patched"] = is_checked
        else: self.setting_widgets[client_index]["vars"]["fast_walk"].set(not is_checked)

    def on_toggle_speed(self, client_index):
        slot = self.client_data_slots[client_index]
        pm = slot["pm_handle"]
        if pm is None or not slot["speed_address_1"]:
            self.setting_widgets[client_index]["vars"]["game_speed"].set(not self.setting_widgets[client_index]["vars"]["game_speed"].get())
            return
        is_checked = self.setting_widgets[client_index]["vars"]["game_speed"].get()
        if is_checked: target1, target2 = NOP_PATCH, NOP_PATCH
        else: target1, target2 = slot["speed_original_bytes_1"], slot["speed_original_bytes_2"]
        s1 = self.perform_write_bytes(pm, slot["speed_address_1"], target1)
        s2 = self.perform_write_bytes(pm, slot["speed_address_2"], target2)
        if s1 and s2: slot["speed_is_patched"] = is_checked
        else: self.setting_widgets[client_index]["vars"]["game_speed"].set(not is_checked)

    def on_toggle_noclip(self, client_index):
        slot = self.client_data_slots[client_index]
        pm = slot["pm_handle"]
        addr, orig_bytes = slot["noclip_address"], slot["noclip_original_bytes"]
        if pm is None or addr is None:
            self.setting_widgets[client_index]["vars"]["no_clip"].set(not self.setting_widgets[client_index]["vars"]["no_clip"].get())
            return
        is_checked = self.setting_widgets[client_index]["vars"]["no_clip"].get()
        target_bytes = NOCLIP_PATCHED_BYTES if is_checked else orig_bytes
        if self.perform_write_bytes(pm, addr, target_bytes): slot["noclip_is_patched"] = is_checked
        else: self.setting_widgets[client_index]["vars"]["no_clip"].set(not is_checked)

    def on_toggle_hide(self, client_index):
        slot = self.client_data_slots[client_index]
        hwnd = slot["hwnd"]
        if not hwnd: return
        is_checked = self.setting_widgets[client_index]["vars"]["hide_sa"].get()
        command = SW_HIDE if is_checked else SW_SHOW
        try:
            ctypes.windll.user32.ShowWindow(hwnd, command)
            slot["is_hidden"] = is_checked
        except Exception:
            self.setting_widgets[client_index]["vars"]["hide_sa"].set(not is_checked)

    def perform_write_byte(self, pm, patch_address, target_byte):
        try:
            pm.write_uchar(patch_address, target_byte)
            return pm.read_bytes(patch_address, 1)[0] == target_byte
        except Exception as e:
            self.log(f"寫入失敗: {e}")
            return False
            
    def perform_write_bytes(self, pm, patch_address, target_bytes):
        try:
            pm.write_bytes(patch_address, target_bytes, len(target_bytes))
            return pm.read_bytes(patch_address, len(target_bytes)) == target_bytes
        except Exception as e:
            self.log(f"寫入失敗: {e}")
            return False

    def on_client_right_click_single(self, event, client_index):
        slot = self.client_data_slots[client_index]
        if slot["status"] == "已綁定" and slot["hwnd"]:
            ctypes.windll.user32.ShowWindow(slot["hwnd"], SW_MINIMIZE) 

    def on_client_right_click_double(self, event, client_index):
        slot = self.client_data_slots[client_index]
        if slot["status"] == "已綁定" and slot["hwnd"]:
            if ctypes.windll.user32.IsIconic(slot["hwnd"]):
                ctypes.windll.user32.ShowWindow(slot["hwnd"], SW_RESTORE)
            ctypes.windll.user32.SetForegroundWindow(slot["hwnd"])

    def on_closing(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.command_queue.put({"action": "stop"})
            self.worker_thread.join(timeout=2.0) 

        self.log("正在還原補丁...")
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            pm = slot["pm_handle"]
            if not pm or slot["status"] != "已綁定": continue
            
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
                pm.close_process()
            except Exception: pass
        self.destroy()

if __name__ == "__main__":
    app = DSAHelperApp()
    app.mainloop()