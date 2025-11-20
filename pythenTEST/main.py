# main.py
# 程式入口：視窗管理、執行緒協調、DPI 偵測

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

class DSAHelperApp(tk.Tk):
    def __init__(self):
        # 1. 設定 DPI 感知
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1) 
        except (AttributeError, OSError):
            try: ctypes.windll.user32.SetProcessDPIAware()
            except: pass
        
        super().__init__()
        
        # 2. 偵測 DPI 與螢幕解析度
        try:
            window_handle = self.winfo_id()
            REAL_DPI = ctypes.windll.user32.GetDpiForWindow(window_handle)
            SYSTEM_DPI_SCALING = REAL_DPI / 96.0
        except Exception as e:
            self.log(f"[ERROR] DPI 偵測失敗: {e}。使用預設值 1.0")
            SYSTEM_DPI_SCALING = 1.0 

        self.log(f"--- DPI 偵測: {REAL_DPI} (Scale: {SYSTEM_DPI_SCALING:.2f})")
        
        # 暫時固定解析度比例
        RESOLUTION_RATIO = 1.0

        # 3. 選擇基礎參數 (4K)
        if SYSTEM_DPI_SCALING <= 1.1: 
            BASE_PARAMS_4K = app_ui.PARAMS_4K_100
        elif SYSTEM_DPI_SCALING <= 1.35: 
            BASE_PARAMS_4K = app_ui.PARAMS_4K_125
        else: 
            BASE_PARAMS_4K = app_ui.PARAMS_4K_150

        # 4. 計算最終佈局參數並寫回 app_ui
        app_ui.RESOLUTION_RATIO = RESOLUTION_RATIO 
        
        app_ui.LAYOUT_APP_BASE_WIDTH = int(BASE_PARAMS_4K["APP_BASE_WIDTH"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_APP_BASE_HEIGHT = int(BASE_PARAMS_4K["APP_BASE_HEIGHT"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_LEFT_PANEL_WIDTH = int(BASE_PARAMS_4K["LEFT_PANEL_WIDTH"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_NON_CONTENT_HEIGHT = int(BASE_PARAMS_4K["NON_CONTENT_HEIGHT"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_CANVAS_ROW_PADDING = int(BASE_PARAMS_4K["CANVAS_ROW_PADDING"] * RESOLUTION_RATIO)

        app_ui.LAYOUT_LEFT_CHECKBOX_PADY = int(BASE_PARAMS_4K["LEFT_CHECKBOX_PADY"] * RESOLUTION_RATIO)
        app_ui.LAYOUT_SETTINGS_CHECKBOX_PADY = int(BASE_PARAMS_4K["SETTINGS_CHECKBOX_PADY"] * RESOLUTION_RATIO)

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

        # 動態計算高度
        app_ui.BASE_CANVAS_ROW_HEIGHT = (app_ui.LAYOUT_CANVAS_BASE_Y_START + 
                                  (10 * app_ui.LAYOUT_CANVAS_BASE_Y_STEP) + 
                                  app_ui.LAYOUT_CANVAS_BASE_Y_START)

        app_ui.FINAL_CANVAS_ROW_TOTAL_HEIGHT = (app_ui.BASE_CANVAS_ROW_HEIGHT + 
                                         app_ui.LAYOUT_CANVAS_ROW_PADDING)

        # 5. 介面初始化
        self.scaled_left_panel_width = app_ui.LAYOUT_LEFT_PANEL_WIDTH
        self.current_base_width = app_ui.LAYOUT_APP_BASE_WIDTH
        self.base_window_height = app_ui.LAYOUT_APP_BASE_HEIGHT
        self.non_content_height = app_ui.LAYOUT_NON_CONTENT_HEIGHT
        self.height_per_client_row = app_ui.FINAL_CANVAS_ROW_TOTAL_HEIGHT

        self.title("DSA Helper v4.9 (Cleaned)")
        try: self.iconbitmap("icon.ico")
        except tk.TclError: pass
        
        self.geometry(f"{self.current_base_width}x{self.base_window_height}") 
        self.resizable(False, True) 

        self.notebook = None
        self.tabs = {} 
        self.tab_frame_settings = None
        self.tab_frame_char = None
        self.client_checkboxes = [] 
        self.refresh_rate_combo = None
        self.setting_widgets = []
        self.client_canvas_ui = [None] * MAX_CLIENTS
        self.client_selection_vars = [tk.IntVar() for _ in range(MAX_CLIENTS)]
        self.refresh_rate_var = tk.StringVar()
        self.client_data_slots = [self.create_empty_slot_data() for _ in range(MAX_CLIENTS)]
        
        self.data_queue = queue.Queue()
        self.command_queue = queue.Queue()
        self.worker_thread = None
        
        if not is_admin():
            self.title(f"{self.title()} (錯誤：請以管理員權限執行)")
            label = tk.Label(self, text="錯誤：\n必須以「系統管理員」權限執行此程式！", fg="red", padx=50, pady=50)
            label.pack()
        else:
            app_ui.create_main_widgets(self)
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.log("介面初始化完成。請點擊 '綁定石器'。")
            self.start_worker_thread()
            self.check_data_queue()
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

    def on_tab_changed(self, event=None):
        self.adjust_window_height()

    def adjust_window_height(self):
        """根據當前頁籤和選中數量，動態調整視窗高度"""
        try:
            current_tab_text = self.notebook.tab(self.notebook.select(), "text")
        except Exception:
            current_tab_text = ""
        
        if current_tab_text != "人寵資料":
            if self.winfo_height() != self.base_window_height:
                self.geometry(f"{self.current_base_width}x{self.base_window_height}")
            return
        
        selected_count = 0
        for i in range(MAX_CLIENTS):
            if self.client_selection_vars[i].get() == 1 and self.client_data_slots[i]["status"] == "已綁定":
                selected_count += 1
        
        if selected_count == 0:
            new_height = self.base_window_height
        else:
            content_height = selected_count * (self.height_per_client_row+9)
            new_height = self.non_content_height + content_height
            max_height = self.winfo_screenheight()-40
            new_height = max(self.base_window_height, min(new_height, max_height))
        
        if self.winfo_height() != new_height:
            self.geometry(f"{self.current_base_width}x{new_height}")

    # --- 執行緒與佇列管理 ---
    def start_worker_thread(self):
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
        self.worker_thread = MemoryMonitorThread(self.data_queue, self.command_queue, self.client_data_slots)
        self.worker_thread.start()
        self.on_refresh_rate_change() 

    def check_data_queue(self):
        try:
            full_data_package = self.data_queue.get_nowait()
            account_name_updated = False
            
            for i in range(MAX_CLIENTS):
                new_data = full_data_package[i]
                slot = self.client_data_slots[i]
                client_ui_pack = self.client_canvas_ui[i] 

                if new_data["status"] == "已失效" and slot["status"] == "已綁定":
                    self.log(f"窗口 {i+1} 失效，正在清理...")
                    try:
                        if slot["pm_handle"]: slot["pm_handle"].close_process()
                    except Exception: pass
                    self.client_data_slots[i] = self.create_empty_slot_data()
                    self.client_selection_vars[i].set(0)
                    account_name_updated = True
                    self.update_all_displays()
                
                elif slot["status"] == "已綁定":
                    if slot["account_name"] != new_data["account_name"]:
                        account_name_updated = True
                        slot["account_name"] = new_data["account_name"]
                        self.update_all_displays() 
                    
                    slot["game_state"] = new_data["game_state"]

                    # 精確更新 UI
                    if client_ui_pack and not account_name_updated: 
                        canvas = client_ui_pack["canvas"]
                        vars_list = client_ui_pack["vars_list"]
                        self._granular_update_char_canvas(canvas, vars_list[0], slot["char_data_cache"], new_data["char_data_cache"])
                        for p_idx in range(5):
                            self._granular_update_pet_canvas(canvas, vars_list[p_idx + 1], p_idx, slot["pet_data_cache"][p_idx], new_data["pet_data_cache"][p_idx])
                    
                    slot["char_data_cache"] = new_data["char_data_cache"]
                    slot["pet_data_cache"] = new_data["pet_data_cache"]
            
            if account_name_updated:
                self.update_client_list_ui()

        except queue.Empty:
            pass 
        
        self.after(100, self.check_data_queue)

    # --- 綁定與掃描功能 ---
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
        self.log(f"--- 開始檢查綁定 ---")
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

        self.log(f"找到 {len(new_windows)} 個新窗口，正在綁定...")
        new_window_iter = iter(new_windows)
        for i in range(MAX_CLIENTS):
            if self.client_data_slots[i]["pid"] is None: 
                try:
                    hwnd, pid = next(new_window_iter)
                    slot = self.client_data_slots[i]
                    slot["pid"] = pid
                    slot["hwnd"] = hwnd
                    self.scan_client_addresses(i) 
                    self.log(f"窗口 {i+1} 綁定成功 (PID {pid})")
                    self.update_client_list_ui(i) 
                except StopIteration:
                    break 
        self.update_all_displays()

    def scan_client_addresses(self, slot_index):
        slot = self.client_data_slots[slot_index]
        pid = slot["pid"]
        try:
            pm = pymem.Pymem(pid)
            slot["pm_handle"] = pm
            module = pymem.process.module_from_name(pm.process_handle, PROCESS_NAME)
            if not module:
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
                addr1 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_1_ORIGINAL)
                addr2 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_2_ORIGINAL)
                is_patched_scan = False
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
                addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_NOCLIP_ORIGINAL)
                is_patched_scan = False
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
        except Exception:
            slot["status"] = "掃描失敗"
            if slot["pm_handle"]: slot["pm_handle"].close_process(); slot["pm_handle"] = None

    # --- UI 更新邏輯 ---
    def on_selection_change(self):
        self.update_all_displays()

    def update_all_displays(self):
        """動態建立/銷毀 UI"""
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            is_selected = self.client_selection_vars[i].get() == 1
            is_bound = slot["status"] == "已綁定"
            settings_ui = self.setting_widgets[i]
            
            if is_selected and is_bound:
                # 更新設置頁籤
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

                # 更新人寵畫布
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
                # 隱藏與銷毀
                settings_ui["frame"].pack_forget()
                client_ui_pack = self.client_canvas_ui[i]
                if client_ui_pack is not None:
                    client_ui_pack["frame"].destroy() 
                    self.client_canvas_ui[i] = None
        
        if self.tab_frame_settings: self.tab_frame_settings.inner_frame.event_generate("<Configure>")
        if self.tab_frame_char: self.tab_frame_char.inner_frame.event_generate("<Configure>")
        self.adjust_window_height()

    def _configure_character_canvas(self, canvas, person_vars, data):
        """全量更新人物 Canvas"""
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
                lbl_key, val_key = f"elem_{i+1}_lbl", f"elem_{i+1}_val"
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
        """僅更新有變動的 Canvas 項目"""
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
                self._configure_character_canvas(canvas, person_vars, new_data) # 屬性較複雜，直接重繪
        except Exception:
            self._configure_character_canvas(canvas, person_vars, new_data) 

    def _configure_pet_canvas(self, canvas, pet_vars, data, p_idx):
        """全量更新寵物 Canvas"""
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
                lbl_key, val_key = f"elem_{i+1}_lbl", f"elem_{i+1}_val"
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
        """僅更新有變動的 Canvas 項目"""
        if not new_data: 
            if old_data: self._configure_pet_canvas(canvas, pet_vars, None, p_idx)
            return
        if not old_data: 
            self._configure_pet_canvas(canvas, pet_vars, new_data, p_idx)
            return

        try:
            if old_data.get("status_text") != new_data.get("status_text") or old_data.get("name") != new_data.get("name"):
                self._configure_pet_canvas(canvas, pet_vars, new_data, p_idx) # 名字或狀態改變，重繪頭部
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
        mapping = {'0.5s': 0.5, '1s': 1.0, '3s': 3.0, '5s': 5.0, '10s': 10.0, '60s': 60.0, '不刷新': None}
        return mapping.get(value, 3.0) 

    def on_refresh_rate_change(self, event=None):
        new_rate_sec = self.get_poll_interval_sec()
        if self.worker_thread and self.worker_thread.is_alive():
            self.command_queue.put({"action": "set_rate", "value": new_rate_sec})

    # --- 記憶體寫入操作 (加速/穿牆/隱藏) ---
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
        """單擊右鍵：縮小視窗"""
        slot = self.client_data_slots[client_index]
        if slot["status"] == "已綁定" and slot["hwnd"]:
            ctypes.windll.user32.ShowWindow(slot["hwnd"], SW_MINIMIZE) 

    def on_client_right_click_double(self, event, client_index):
        """雙擊右鍵：激活視窗"""
        slot = self.client_data_slots[client_index]
        if slot["status"] == "已綁定" and slot["hwnd"]:
            if ctypes.windll.user32.IsIconic(slot["hwnd"]):
                ctypes.windll.user32.ShowWindow(slot["hwnd"], SW_RESTORE)
            ctypes.windll.user32.SetForegroundWindow(slot["hwnd"])

    def on_closing(self):
        """關閉程式清理"""
        if self.worker_thread and self.worker_thread.is_alive():
            self.command_queue.put({"action": "stop"})
            self.worker_thread.join(timeout=1.0) 

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