import tkinter as tk
from tkinter import ttk, messagebox
import app_ui
import queue
import os

class MockApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DSA Helper - UI Debugger")
        
        self.user_scale = 1.0
        self.refresh_rate_var = tk.StringVar(value='3s')
        self.zoom_var = tk.StringVar(value='100%')
        self.auto_height_var = tk.IntVar(value=1)
        self.client_selection_vars = [tk.IntVar(value=1) for _ in range(6)]
        self.client_checkboxes = []
        self.setting_widgets = []
        self.client_canvas_ui = [None] * 6
        self.client_item_ui = {}
        self.client_battle_ui = {}
        self.tabs = {}
        self.client_data_slots = [{"account_name": f"測試帳號_{i+1}", "status": "已綁定"} for i in range(6)]

        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)

        self.debug_panel = ttk.LabelFrame(self.main_container, text="🛠️ 參數調整面板", padding=10, width=300)
        self.debug_panel.pack(side="left", fill="y", padx=5, pady=5)
        self.debug_panel.pack_propagate(False) 
        
        self.preview_frame = ttk.Frame(self.main_container)
        self.preview_frame.pack(side="right", fill="both", expand=True)
        
        self.create_debug_controls()
        self.apply_layout()

    def on_bind_click(self): print("[Mock] 點擊綁定")
    def on_selection_change(self): print("[Mock] 勾選變更"); self.refresh_mock_data()
    def on_tab_changed(self, e): 
        self.adjust_window_height(); self.refresh_mock_data()
    def on_refresh_rate_change(self, e=None): pass
    def on_zoom_change(self, e=None): pass
    def on_toggle_speed(self, i): pass
    def on_toggle_walk(self, i): pass
    def on_toggle_noclip(self, i): pass
    def on_toggle_hide(self, i): pass
    
    def adjust_window_height(self):
        self.update_idletasks()
        try:
            if hasattr(self, 'notebook') and self.notebook and self.notebook.select():
                tab_text = self.notebook.tab(self.notebook.select(), "text")
                target_frame = None
                extra = 80
                if tab_text == "人寵資料" and hasattr(self, "tab_frame_char"): target_frame = self.tab_frame_char.inner_frame
                elif tab_text == "道具列表" and hasattr(self, "tab_frame_items"): target_frame = self.tab_frame_items.inner_frame
                elif tab_text == "戰鬥狀態" and hasattr(self, "tab_frame_battle"): target_frame = self.tab_frame_battle.inner_frame
                elif tab_text == "遊戲設置" and hasattr(self, "tab_frame_settings"): target_frame = self.tab_frame_settings.inner_frame; extra += 50
                
                if target_frame:
                    h = target_frame.winfo_reqheight() + extra
                    print(f"[Info] 內容需求高度: {h}")
        except: pass

    def on_client_right_click_single(self, e, i): pass
    def on_client_right_click_double(self, e, i): pass

    def create_debug_controls(self):
        # [修改] 更新預設值 & 新增選項
        self.params = {
            "SCALE": {"label": "整體縮放 (Scale)", "val": 1.0, "step": 0.1},
            "BASE_FONT": {"label": "字體大小 (10)", "val": 10, "step": 1},
            "BASE_ROW_H": {"label": "基礎行高 (14)", "val": 14, "step": 1},
            "BASE_WIDTH": {"label": "視窗總寬 (1000)", "val": 1000, "step": 50},
            "BASE_HEIGHT": {"label": "視窗基準高 (280)", "val": 280, "step": 10},
            "LEFT_W": {"label": "左面板寬 (120)", "val": 120, "step": 10},
            "PADDING": {"label": "通用邊距 (5)", "val": 5, "step": 1},
            
            # [新增] 細部微調選項
            "CHECKBOX_PADY": {"label": "左側勾選距 (2)", "val": 2, "step": 1},
            "CHAR_COL_W": {"label": "人寵欄寬 (120)", "val": 120, "step": 5},
            "GRID_BASE_W": {"label": "列表網格基寬 (60)", "val": 60, "step": 5},
        }
        
        self.entries = {}
        row = 0
        for key, settings in self.params.items():
            ttk.Label(self.debug_panel, text=settings["label"]).grid(row=row, column=0, sticky="w", pady=2)
            var = tk.DoubleVar(value=settings["val"]) if isinstance(settings["val"], float) else tk.IntVar(value=settings["val"])
            entry = ttk.Entry(self.debug_panel, textvariable=var, width=8)
            entry.grid(row=row, column=1, padx=5)
            self.entries[key] = var
            row += 1
            
        ttk.Separator(self.debug_panel, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1
        
        btn_frame = ttk.Frame(self.debug_panel)
        btn_frame.grid(row=row, column=0, columnspan=2)
        ttk.Button(btn_frame, text="套用 (Apply)", command=self.apply_layout).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="保存 (Save)", command=self.save_params).pack(side="left", padx=5)

    def apply_layout(self):
        # 讀取數值
        scale = self.entries["SCALE"].get()
        base_font = self.entries["BASE_FONT"].get()
        base_row_h = self.entries["BASE_ROW_H"].get()
        base_w = self.entries["BASE_WIDTH"].get()
        base_h = self.entries["BASE_HEIGHT"].get()
        left_w = self.entries["LEFT_W"].get()
        pad = self.entries["PADDING"].get()
        
        # 新參數讀取
        cb_pady = self.entries["CHECKBOX_PADY"].get()
        char_col_w = self.entries["CHAR_COL_W"].get()
        grid_base_w = self.entries["GRID_BASE_W"].get()
        
        # 覆寫 app_ui 參數
        app_ui.LAYOUT_PARAMS["SCALE"] = scale
        app_ui.LAYOUT_PARAMS["FONT_SIZE_NORMAL"] = max(int(base_font * scale), 1)
        app_ui.LAYOUT_PARAMS["FONT_SIZE_BOLD"] = max(int(base_font * scale), 1)
        app_ui.LAYOUT_PARAMS["ROW_HEIGHT"] = int(base_row_h * scale)
        app_ui.LAYOUT_PARAMS["PADDING"] = int(pad * scale)
        
        # 注入新參數
        app_ui.LAYOUT_PARAMS["CHECKBOX_PADY"] = int(cb_pady * scale)
        app_ui.LAYOUT_PARAMS["CHAR_COL_WIDTH"] = int(char_col_w * scale)
        app_ui.LAYOUT_PARAMS["GRID_BASE_WIDTH"] = int(grid_base_w * scale)
        
        self.scaled_left_panel_width = int(left_w * scale)
        self.current_base_width = int(base_w * scale)
        self.base_window_height = int(base_h * scale)
        
        for widget in self.preview_frame.winfo_children(): widget.destroy()
        self.client_checkboxes = []
        self.setting_widgets = []
        self.client_canvas_ui = [None] * 6
        self.client_item_ui = {}
        self.client_battle_ui = {}
        
        app_root = tk.Frame(self.preview_frame)
        app_root.pack(fill="both", expand=True)
        
        # 屬性綁定
        app_root.scaled_left_panel_width = self.scaled_left_panel_width
        app_root.client_selection_vars = self.client_selection_vars
        app_root.on_bind_click = self.on_bind_click
        app_root.on_selection_change = self.on_selection_change
        app_root.on_client_right_click_single = self.on_client_right_click_single
        app_root.on_client_right_click_double = self.on_client_right_click_double
        app_root.client_checkboxes = self.client_checkboxes
        app_root.tabs = self.tabs
        app_root.refresh_rate_var = self.refresh_rate_var
        app_root.on_refresh_rate_change = self.on_refresh_rate_change
        app_root.zoom_var = self.zoom_var
        app_root.on_zoom_change = self.on_zoom_change
        app_root.auto_height_var = self.auto_height_var
        app_root.adjust_window_height = self.adjust_window_height
        app_root.tab_frame_settings = getattr(self, 'tab_frame_settings', None)
        app_root.setting_widgets = self.setting_widgets
        app_root.on_toggle_speed = self.on_toggle_speed
        app_root.on_toggle_walk = self.on_toggle_walk
        app_root.on_toggle_noclip = self.on_toggle_noclip
        app_root.on_toggle_hide = self.on_toggle_hide
        app_root.on_tab_changed = self.on_tab_changed
        app_root.notebook = None
        
        try: app_ui.create_main_widgets(app_root)
        except Exception as e: print(f"[Error] {e}"); return
        
        self.notebook = app_root.notebook
        self.tab_frame_char = app_root.tab_frame_char
        self.tab_frame_items = app_root.tab_frame_items
        self.tab_frame_battle = app_root.tab_frame_battle
        self.tab_frame_settings = app_root.tab_frame_settings
        self.client_checkboxes = app_root.client_checkboxes
        self.setting_widgets = app_root.setting_widgets
        
        # [修正] 視窗高度不再鎖定 600，改為跟隨 BASE_HEIGHT (但保留 Debug 面板高度以免被切掉)
        # Debug panel 大約 400-500px，我們取較大值
        debug_panel_req_h = 500 
        total_width = self.current_base_width + 300 + 30
        total_height = max(debug_panel_req_h, self.base_window_height + 50)
        self.geometry(f"{total_width}x{total_height}")
        
        self.refresh_mock_data()
        self.update_idletasks()

    def save_params(self):
        content = "=== DSA Helper Layout Configuration ===\n\n"
        content += "請將以下數值填入 app_ui.py 的 update_layout_params 函式中：\n\n"
        for key, var in self.entries.items(): content += f"{key}: {var.get()}\n"
        try:
            with open("layout_config.txt", "w", encoding="utf-8") as f: f.write(content)
            messagebox.showinfo("成功", f"參數已保存！\n請查看 {os.path.abspath('layout_config.txt')}")
        except Exception as e: messagebox.showerror("錯誤", f"保存失敗: {e}")

    def refresh_mock_data(self):
        if hasattr(self, "tab_frame_char") and hasattr(app_ui, "create_client_info_canvas"):
            for widget in self.tab_frame_char.inner_frame.winfo_children(): widget.destroy()
            self.client_canvas_ui = [None] * 6
            for i in range(6):
                if self.client_selection_vars[i].get():
                    frame = ttk.Labelframe(self.tab_frame_char.inner_frame, text=f"測試帳號_{i+1}")
                    cv, items = app_ui.create_client_info_canvas(frame, self)
                    self.client_canvas_ui[i] = {"frame": frame, "canvas": cv, "items": items}
                    frame.pack(fill="x", padx=5, pady=5)
                    dummy_char = {"name": f"玩家{i+1}", "nickname": "傳說人物", "lv": 140, "hp": "2500/2500", "mp": "500/500", "atk": 450, "def": 300, "agi": 280, "charm": 100, "rebirth": "轉生伍", "element_raw": (100, 0, 0, 0), "vit": 100, "str": 200, "sta": 50, "spd": 150}
                    app_ui.update_char_canvas(cv, items[0], dummy_char)
                    for p in range(5):
                        dummy_pet = {"name": f"白虎{p+1}", "nickname": "阿寶", "lv": 140, "hp": "5000/5000", "atk": 800, "def": 600, "agi": 350, "exp": 999999, "lack": 0, "loyal": 100, "rebirth": "轉生貳", "status_text": "戰" if p==0 else "休", "status_color_key": "轉生肆" if p==0 else "未轉生", "element_raw": (0, 100, 0, 0)}
                        app_ui.update_pet_canvas(cv, items[p+1], dummy_pet, p)

        if hasattr(self, "tab_frame_items"):
            for widget in self.tab_frame_items.inner_frame.winfo_children(): widget.destroy()
            self.client_item_ui = {}
            for i in range(6):
                if self.client_selection_vars[i].get():
                    ui = app_ui.create_item_client_panel(self.tab_frame_items.inner_frame, f"測試帳號_{i+1}")
                    self.client_item_ui[i] = ui
                    dummy_items = {}
                    for idx in range(-9, 15): dummy_items[idx] = {"stack": 1, "name": f"道具_{idx}", "dur": "100/100", "desc": "說明"}
                    dummy_items[-7] = {"stack": 1, "name": "月神之槍", "dur": "300/300", "desc": "強大的槍"}
                    app_ui.update_items_canvas(ui["canvas"], ui["ids"], dummy_items)

        if hasattr(self, "tab_frame_battle"):
            for widget in self.tab_frame_battle.inner_frame.winfo_children(): widget.destroy()
            self.client_battle_ui = {}
            for i in range(6):
                if self.client_selection_vars[i].get():
                    ui = app_ui.create_battle_client_panel(self.tab_frame_battle.inner_frame, f"測試帳號_{i+1}")
                    self.client_battle_ui[i] = ui
                    dummy_battle = {}
                    from constants import BATTLE_LEFT_ORDER, BATTLE_RIGHT_ORDER
                    for b_idx in BATTLE_LEFT_ORDER + BATTLE_RIGHT_ORDER: dummy_battle[b_idx] = f"[140]敵人_{b_idx} (5000/5000)"
                    app_ui.update_battle_canvas(ui["canvas"], ui["ids"], dummy_battle, 10)

if __name__ == "__main__":
    app = MockApp()
    app.mainloop()