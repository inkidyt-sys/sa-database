# main.py

import tkinter as tk
from tkinter import ttk
import ctypes
import queue

from constants import *
from utils import is_admin
import app_ui 
from memory_worker import MemoryMonitorThread

import game_scanner
import game_features

# --- DPI ---
try: ctypes.windll.shcore.SetProcessDpiAwareness(1) 
except: 
    try: ctypes.windll.user32.SetProcessDPIAware()
    except: pass

class DSAHelperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.detect_dpi()
        self.user_scale = 1.0
        
        # UI 變數
        self.refresh_rate_var = tk.StringVar(value='3s')
        self.zoom_var = tk.StringVar(value='100%') 
        self.auto_height_var = tk.IntVar(value=1)
        self.client_selection_vars = [tk.IntVar() for _ in range(MAX_CLIENTS)]
        
        # 資料結構
        self.client_data_slots = [self.create_empty_slot_data() for _ in range(MAX_CLIENTS)]
        self.client_checkboxes = []
        self.setting_widgets = []
        # UI 緩存
        self.client_canvas_ui = [None] * MAX_CLIENTS
        self.client_item_ui = {}
        self.client_battle_ui = {}
        self.tabs = {}
        
        self.data_queue = queue.Queue()
        self.command_queue = queue.Queue()
        self.worker_thread = None

        self.title("DSA 新端輔助程式 v5.0 by 陳財佑")
        try: self.iconbitmap("icon.ico")
        except: pass
        
        self.calc_layout_params()
        self.rebuild_ui(first_run=True)

        if not is_admin():
            self.show_admin_error()
        else:
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.start_worker_thread()
            self.check_data_queue()
            self.adjust_window_height()

    def detect_dpi(self):
        try:
            self.REAL_DPI = ctypes.windll.user32.GetDpiForWindow(self.winfo_id())
            self.SYSTEM_DPI_SCALING = self.REAL_DPI / 96.0
        except: self.SYSTEM_DPI_SCALING = 1.0 

    def calc_layout_params(self):
        base_scale = 1.0
        if self.SYSTEM_DPI_SCALING > 1.35: base_scale = 1.5
        elif self.SYSTEM_DPI_SCALING > 1.1: base_scale = 1.25
        
        final_ratio = base_scale * self.user_scale
        
        # 更新 app_ui 並取得視窗大小
        dims = app_ui.update_layout_params(final_ratio)
        self.scaled_left_panel_width = dims["LEFT_PANEL_WIDTH"]
        self.current_base_width = dims["APP_WIDTH"]
        self.base_window_height = dims["APP_HEIGHT"]

    def rebuild_ui(self, first_run=False):
        if not first_run:
            for widget in self.winfo_children(): widget.destroy()
            self.client_checkboxes, self.setting_widgets = [], []
            self.client_canvas_ui = [None] * MAX_CLIENTS
            self.client_item_ui, self.client_battle_ui, self.notebook = {}, {}, None

        app_ui.create_main_widgets(self)
        self.geometry(f"{self.current_base_width}x{self.base_window_height}")
        self.resizable(False, True)
        
        if not first_run:
            self.update_client_list_ui()
            self.update_all_displays()
            self.adjust_window_height()

    def on_zoom_change(self, event):
        try: val = float(self.zoom_var.get().replace('%', '')) / 100.0
        except: val = 1.0
        if val != self.user_scale:
            self.user_scale = val
            self.calc_layout_params()
            self.rebuild_ui()

    def create_empty_slot_data(self):
        return {
            "pid": None, "hwnd": None, "status": "未綁定", 
            "pm_handle": None, "module_base": None, "game_state": "unbound", 
            "account_name": "", 
            "char_data_cache": None, "pet_data_cache": [None]*5, 
            "item_data_cache": {}, "battle_data_cache": {},
            "walk_address": None, "walk_original_byte": None, "walk_is_patched": False,
            "speed_address_1": None, "speed_address_2": None, 
            "speed_original_bytes_1": None, "speed_original_bytes_2": None, "speed_is_patched": False,
            "noclip_address": None, "noclip_original_bytes": None, "noclip_is_patched": False,
            "is_hidden": False
        }

    def start_worker_thread(self):
        if self.worker_thread and self.worker_thread.is_alive(): return
        self.worker_thread = MemoryMonitorThread(self.data_queue, self.command_queue, self.client_data_slots)
        self.worker_thread.start()
        self.on_refresh_rate_change()

    def check_data_queue(self):
        try:
            full_data = self.data_queue.get_nowait()
            account_changed = False
            for i, new_data in enumerate(full_data):
                slot = self.client_data_slots[i]
                
                # --- [新增] 自動偵測視窗關閉/失效邏輯 ---
                # 如果當前是「已綁定」，但後台回傳「已失效」，代表遊戲關了
                if slot["status"] == "已綁定" and new_data["status"] == "已失效":
                    print(f"窗口 {i+1} 連線中斷，重置狀態。")
                    
                    # 1. 嘗試關閉記憶體控制代碼 (避免殘留)
                    try: 
                        if slot["pm_handle"]: slot["pm_handle"].close_process()
                    except: pass
                    
                    # 2. 重置為空插槽數據 (變回 "未綁定")
                    self.client_data_slots[i] = self.create_empty_slot_data()
                    
                    # 3. 標記需要刷新左側列表
                    account_changed = True
                    continue # 跳過本次後續更新，直接處理下一個
                # -------------------------------------

                if slot["status"] == "已綁定":
                    if slot["account_name"] != new_data["account_name"]:
                        slot["account_name"] = new_data["account_name"]; account_changed = True
                    for k in ["game_state", "char_data_cache", "pet_data_cache", "item_data_cache", "battle_data_cache"]:
                        slot[k] = new_data[k]
            
            self.update_all_displays()
            if account_changed: self.update_client_list_ui()
            
            # 刷新 Tab
            try:
                if self.notebook.select():
                    t = self.notebook.tab(self.notebook.select(), "text")
                    if t == "道具列表": self._update_items_tab_ui()
                    elif t == "戰鬥狀態": self._update_battle_tab_ui()
            except: pass
        except queue.Empty: pass
        self.after(100, self.check_data_queue)

    def on_bind_click(self):
        curr_pids = {slot["pid"] for slot in self.client_data_slots if slot["status"] == "已綁定"}
        new_wins = [w for w in game_scanner.find_game_windows() if w[1] not in curr_pids]

        if not new_wins:
            self.update_all_displays()
            return

        iter_wins = iter(new_wins)
        for i in range(MAX_CLIENTS):
            if self.client_data_slots[i]["pid"] is None:
                try:
                    hwnd, pid = next(iter_wins)
                    self.client_data_slots[i].update({"pid": pid, "hwnd": hwnd})
                    game_scanner.scan_slot(self.client_data_slots[i])
                    self.update_client_list_ui(i)
                except StopIteration: break
        self.update_all_displays()

    def on_selection_change(self): self.update_all_displays()
    def on_tab_changed(self, e=None): self.adjust_window_height()

    def update_client_list_ui(self, idx=None):
        r = range(MAX_CLIENTS) if idx is None else [idx]
        for i in r:
            s = self.client_data_slots[i]
            is_bound = s["status"]=="已綁定"
            self.client_checkboxes[i].config(text=s["account_name"] if is_bound else f"窗口 {i+1}: {s['status']}",
                                             state="normal" if is_bound else "disabled", fg="green" if is_bound else "grey")

    def update_all_displays(self):
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            sel = self.client_selection_vars[i].get()
            ui = self.client_canvas_ui[i]
            
            if sel and slot["status"] == "已綁定":
                sw = self.setting_widgets[i]
                sw["frame"].pack(side="left", fill="y", anchor="n", padx=5, pady=5)
                sw["frame"].config(text=slot["account_name"])
                sw["vars"]["game_speed"].set(slot["speed_is_patched"])
                sw["vars"]["fast_walk"].set(slot["walk_is_patched"])
                sw["vars"]["no_clip"].set(slot["noclip_is_patched"])
                sw["vars"]["hide_sa"].set(slot["is_hidden"])
                
                if not ui:
                    frame = ttk.Labelframe(self.tab_frame_char.inner_frame, text="初始化...", padding=0)
                    cv, items = app_ui.create_client_info_canvas(frame, self)
                    self.client_canvas_ui[i] = {"frame": frame, "canvas": cv, "items": items}
                    ui = self.client_canvas_ui[i]
                
                ui["frame"].grid(row=i, column=0, sticky="ew", padx=5, pady=5)
                ui["frame"].config(text=slot["account_name"])
                
                app_ui.update_char_canvas(ui["canvas"], ui["items"][0], slot.get("char_data_cache"))
                for p_idx in range(5):
                    app_ui.update_pet_canvas(ui["canvas"], ui["items"][p_idx+1], slot.get("pet_data_cache")[p_idx], p_idx)
            else:
                self.setting_widgets[i]["frame"].pack_forget()
                if ui: 
                    ui["frame"].destroy(); self.client_canvas_ui[i] = None

        if self.tab_frame_char: self.tab_frame_char.inner_frame.event_generate("<Configure>")
        self.adjust_window_height()

    def _update_items_tab_ui(self):
        if not hasattr(self, "tab_frame_items"): return
        parent = self.tab_frame_items.inner_frame
        needs_redraw = False
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            show = (self.client_selection_vars[i].get() == 1 and slot["status"] == "已綁定")
            
            if not show:
                if i in self.client_item_ui:
                    self.client_item_ui[i]["frame"].destroy(); del self.client_item_ui[i]; needs_redraw = True
                continue
            if i not in self.client_item_ui:
                self.client_item_ui[i] = app_ui.create_item_client_panel(parent, slot["account_name"]); needs_redraw = True
            
            ui = self.client_item_ui[i]
            
            # --- [修改] 更新標題資訊 (加入石幣) ---
            title_text = slot["account_name"]
            char = slot.get("char_data_cache")
            if char:
                # 格式: 帳號 名稱 LV:xxx HP:xxx/xxx MP:xxx/xxx 石幣:xxxxxx
                title_text = f"{slot['account_name']}   {char.get('name','')}   LV:{char.get('lv','--')}   HP:{char.get('hp','--/--')}   MP:{char.get('mp','--/--')}   石幣:{char.get('gold', 0)}"
            
            if ui["frame"].cget("text") != title_text: 
                ui["frame"].config(text=title_text)
            # ------------------------------------
            
            app_ui.update_items_canvas(ui["canvas"], ui["ids"], slot.get("item_data_cache", {}))

        if needs_redraw: parent.event_generate("<Configure>"); self.adjust_window_height()

    def _update_battle_tab_ui(self):
        if not hasattr(self, "tab_frame_battle"): return
        parent = self.tab_frame_battle.inner_frame
        needs_redraw = False
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            show = (self.client_selection_vars[i].get() == 1 and slot["status"] == "已綁定")
            if not show:
                if i in self.client_battle_ui:
                    self.client_battle_ui[i]["frame"].destroy(); del self.client_battle_ui[i]; needs_redraw = True
                continue
            if i not in self.client_battle_ui:
                self.client_battle_ui[i] = app_ui.create_battle_client_panel(parent, slot["account_name"]); needs_redraw = True
            
            ui = self.client_battle_ui[i]
            
            # --- [修改] 更新標題資訊 (含狀態與回合數) ---
            title_text = slot["account_name"]
            char = slot.get("char_data_cache")
            
            # 1. 基礎資訊
            if char:
                title_text = f"{slot['account_name']}   {char.get('name','')}   LV:{char.get('lv','--')}   HP:{char.get('hp','--/--')}   MP:{char.get('mp','--/--')}"

            # 2. 狀態與回合數判斷
            game_state = slot.get("game_state", 0)
            battle_data = slot.get("battle_data_cache", {})
            
            # 假設 10 為戰鬥狀態 (依據 Constants 設定)
            if game_state == 10:
                # 讀取回合數並 +1
                r_val = battle_data.get("round", 0)
                title_text += f"   狀態:戰鬥中 第{r_val + 1}回"
            else:
                title_text += "   狀態:平時"

            if ui["frame"].cget("text") != title_text: 
                ui["frame"].config(text=title_text)
            # ------------------------------------------
            
            # 使用 app_ui 的更新函式
            app_ui.update_battle_canvas(ui["canvas"], ui["ids"], battle_data, game_state)

        if needs_redraw: parent.event_generate("<Configure>"); self.adjust_window_height()

    def on_toggle_walk(self, i): 
        if not game_features.toggle_memory_feature(self.client_data_slots[i], "walk_is_patched", "walk_address", 
            "walk_original_byte", WALK_PATCHED_BYTE, self.setting_widgets[i]["vars"]["fast_walk"].get(), True):
            self._revert_chk(i, "fast_walk")

    def on_toggle_noclip(self, i):
        if not game_features.toggle_memory_feature(self.client_data_slots[i], "noclip_is_patched", "noclip_address",
            "noclip_original_bytes", NOCLIP_PATCHED_BYTES, self.setting_widgets[i]["vars"]["no_clip"].get(), False):
            self._revert_chk(i, "no_clip")

    def on_toggle_speed(self, i):
        if not game_features.toggle_speed(self.client_data_slots[i], self.setting_widgets[i]["vars"]["game_speed"].get()):
            self._revert_chk(i, "game_speed")

    def on_toggle_hide(self, i):
        if not game_features.toggle_hide_window(self.client_data_slots[i], self.setting_widgets[i]["vars"]["hide_sa"].get()):
            self._revert_chk(i, "hide_sa")

    def _revert_chk(self, i, name):
        v = self.setting_widgets[i]["vars"][name]; v.set(not v.get())

    def on_refresh_rate_change(self, e=None):
        m = {'0.5s':0.5, '1s':1.0, '3s':3.0, '5s':5.0, '10s':10.0, '60s':60.0, '不刷新':None}
        self.command_queue.put({"action": "set_rate", "value": m.get(self.refresh_rate_var.get(), 3.0)})

    def adjust_window_height(self):
        if not self.auto_height_var.get(): return
        self.update_idletasks()
        try:
            if self.notebook.select():
                tab_text = self.notebook.tab(self.notebook.select(), "text")
                target_frame = None
                extra_padding = 100

                if tab_text == "人寵資料": target_frame = getattr(self, "tab_frame_char", None) and self.tab_frame_char.inner_frame
                elif tab_text == "道具列表": target_frame = getattr(self, "tab_frame_items", None) and self.tab_frame_items.inner_frame
                elif tab_text == "戰鬥狀態": target_frame = getattr(self, "tab_frame_battle", None) and self.tab_frame_battle.inner_frame
                elif tab_text == "遊戲設置":
                    target_frame = getattr(self, "tab_frame_settings", None) and self.tab_frame_settings.inner_frame
                    extra_padding += 50 

                if target_frame:
                    final_h = target_frame.winfo_reqheight() + extra_padding
                    self.geometry(f"{self.current_base_width}x{max(300, min(final_h, self.winfo_screenheight()-100))}")
        except: pass

    def on_client_right_click_single(self, e, i):
        h = self.client_data_slots[i]["hwnd"]
        if h: ctypes.windll.user32.ShowWindow(h, SW_MINIMIZE)
    def on_client_right_click_double(self, e, i):
        h = self.client_data_slots[i]["hwnd"]
        if h: ctypes.windll.user32.ShowWindow(h, SW_RESTORE); ctypes.windll.user32.SetForegroundWindow(h)
    
    def show_admin_error(self): tk.Label(self, text="錯誤：請以管理員身份執行", fg="red", font=("Arial", 20)).pack(pady=50)

    def on_closing(self):
        if self.worker_thread: self.command_queue.put({"action": "stop"}); self.worker_thread.join(1.0)
        for s in self.client_data_slots:
            if s["status"] == "已綁定":
                try: s["pm_handle"].close_process()
                except: pass
        self.destroy()

if __name__ == "__main__":
    app = DSAHelperApp()
    app.mainloop()