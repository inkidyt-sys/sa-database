# app_ui.py
# (v4.21 - Attribute Dynamic Shift & Pet Line Removed)

import tkinter as tk
from tkinter import ttk
from constants import MAX_CLIENTS, REBIRTH_COLOR_MAP, ITEM_COLOR_RULES, DEFAULT_ITEM_COLOR
from utils import num_to_chinese
import re

# --- 全域佈局參數 ---
LAYOUT_PARAMS = {
    "SCALE": 1.0,
    "FONT_SIZE_NORMAL": 10,
    "FONT_SIZE_BOLD": 10,
    "ROW_HEIGHT": 14,
    "PADDING": 5,
    
    "CHECKBOX_PADY": 2,      
    "CHAR_COL_WIDTH": 140,   
    "GRID_BASE_WIDTH": 60,   
}

def update_layout_params(scale):
    """更新佈局縮放比例"""
    LAYOUT_PARAMS["SCALE"] = scale
    
    # [修正] 改用負數 (Pixels) 來定義字體大小
    # 原理：正數代表 Points (會被系統DPI再次放大)，負數代表 Pixels (絕對大小)
    # 經驗值：原本 10pt 約等於 13px
    base_font_px = 13 
    
    # 注意這裡加了負號 "-"
    LAYOUT_PARAMS["FONT_SIZE_NORMAL"] = -max(int(base_font_px * scale), 1)
    LAYOUT_PARAMS["FONT_SIZE_BOLD"] = -max(int(base_font_px * scale), 1)
    
    LAYOUT_PARAMS["ROW_HEIGHT"] = int(16 * scale) # 稍微加高一點行高以容納像素字體 (14->16)
    LAYOUT_PARAMS["PADDING"] = int(5 * scale)
    
    LAYOUT_PARAMS["CHECKBOX_PADY"] = int(2 * scale)
    LAYOUT_PARAMS["CHAR_COL_WIDTH"] = int(140 * scale)
    LAYOUT_PARAMS["GRID_BASE_WIDTH"] = int(60 * scale)

    return {
        "APP_WIDTH": int(1050 * scale),
        "APP_HEIGHT": int(280 * scale), 
        "LEFT_PANEL_WIDTH": int(120 * scale),
    }

# --- 佈局輔助類別 ---
class GridDrawer:
    def __init__(self, canvas, start_x, start_y, row_height, font_norm, font_bold):
        self.cv = canvas
        self.x = start_x
        self.y = start_y
        self.h = row_height
        self.fn = font_norm
        self.fb = font_bold
        self.start_x = start_x

    def new_row(self):
        """換行"""
        self.y += self.h
        self.x = self.start_x

    def draw_text(self, text, width_factor, key=None, align="w", color="black", is_bold=False, items_dict=None):
        base_width = int(LAYOUT_PARAMS["GRID_BASE_WIDTH"]) 
        cell_width = int(base_width * width_factor)
        
        draw_x = self.x
        anchor = "w"
        if align == "center":
            draw_x = self.x + (cell_width // 2)
            anchor = "center"
        elif align == "e":
            draw_x = self.x + cell_width - 2
            anchor = "e"
        
        tid = self.cv.create_text(draw_x, self.y, text=text, font=self.fb if is_bold else self.fn, 
                                  anchor=anchor, fill=color)
        
        if key is not None and items_dict is not None:
            items_dict[key] = tid
            
        self.x += cell_width
        return tid

    def draw_line_below(self, width_factor=2.2):
        """在當前行底部畫線"""
        base_width = int(LAYOUT_PARAMS["GRID_BASE_WIDTH"])
        w = int(base_width * width_factor)
        line_y = self.y + (self.h // 2) 
        self.cv.create_line(self.start_x, line_y, self.start_x + w, line_y, fill="#AAAAAA")

    def draw_separator(self, width_factor=10):
        """畫分隔線並換行"""
        base_width = int(LAYOUT_PARAMS["GRID_BASE_WIDTH"])
        w = int(base_width * width_factor)
        y_mid = self.y + (self.h // 2)
        self.cv.create_line(self.start_x, y_mid, self.start_x + w, y_mid, fill="#DDDDDD")
        self.new_row()

# --- 主要 UI 建構函式 ---

def create_main_widgets(app):
    main_frame = ttk.Frame(app, padding=LAYOUT_PARAMS["PADDING"])
    main_frame.pack(fill="both", expand=True)

    left_frame = ttk.Frame(main_frame, width=app.scaled_left_panel_width, padding=5, relief="groove")
    left_frame.pack(side="left", fill="y", padx=(0, 5))
    left_frame.pack_propagate(False)

    ttk.Button(left_frame, text="綁定石器", command=app.on_bind_click).pack(fill="x", pady=5)

    bg = app.cget('background')
    for i in range(MAX_CLIENTS):
        cb = tk.Checkbutton(
            left_frame, text=f"窗口 {i+1}: 未綁定",
            variable=app.client_selection_vars[i],
            onvalue=1, offvalue=0, command=app.on_selection_change,
            state="disabled", disabledforeground="grey", anchor="w",
            bg=bg, selectcolor=bg, padx=0
        )
        cb.pack(anchor="w", pady=LAYOUT_PARAMS["CHECKBOX_PADY"])
        cb.bind("<Button-3>", lambda e, idx=i: app.on_client_right_click_single(e, idx))
        cb.bind("<Double-Button-3>", lambda e, idx=i: app.on_client_right_click_double(e, idx))
        app.client_checkboxes.append(cb)

    right_frame = ttk.Frame(main_frame, relief="sunken")
    right_frame.pack(side="right", fill="both", expand=True)

    app.notebook = ttk.Notebook(right_frame)
    app.notebook.pack(fill="both", expand=True)
    app.notebook.bind("<<NotebookTabChanged>>", app.on_tab_changed)

    from ui_components import ScrollableFrame
    
    f_set = ttk.Frame(app.notebook, padding=5); app.notebook.add(f_set, text="遊戲設置")
    _create_settings_tab_content(f_set, app)
    app.tabs["遊戲設置"] = f_set

    f_char = ttk.Frame(app.notebook, padding=5); app.notebook.add(f_char, text="人寵資料")
    app.tab_frame_char = ScrollableFrame(f_char, orient="vertical")
    app.tab_frame_char.pack(fill="both", expand=True)
    app.tab_frame_char.inner_frame.columnconfigure(0, weight=1)
    
    f_item = ttk.Frame(app.notebook, padding=5); app.notebook.add(f_item, text="道具列表")
    app.tab_frame_items = ScrollableFrame(f_item, orient="vertical")
    app.tab_frame_items.pack(fill="both", expand=True)
    
    f_bat = ttk.Frame(app.notebook, padding=5); app.notebook.add(f_bat, text="戰鬥狀態")
    app.tab_frame_battle = ScrollableFrame(f_bat, orient="vertical")
    app.tab_frame_battle.pack(fill="both", expand=True)
    
    f_chat = ttk.Frame(app.notebook); app.notebook.add(f_chat, text="聊天窗口", state="disabled")

def _create_settings_tab_content(parent, app):
    top = ttk.Frame(parent)
    top.pack(fill="x", pady=5)
    
    ttk.Label(top, text="刷新:").pack(side="left", padx=2)
    c1 = ttk.Combobox(top, textvariable=app.refresh_rate_var, values=['0.5s', '1s', '3s', '5s', '10s', '不刷新'], width=5, state="readonly")
    c1.pack(side="left", padx=5); c1.bind("<<ComboboxSelected>>", app.on_refresh_rate_change)
    
    ttk.Label(top, text="縮放:").pack(side="left", padx=2)
    c2 = ttk.Combobox(top, textvariable=app.zoom_var, values=['75%', '100%', '125%', '150%'], width=5, state="readonly")
    c2.pack(side="left", padx=5); c2.bind("<<ComboboxSelected>>", app.on_zoom_change)
    
    ttk.Checkbutton(top, text="自動高度", variable=app.auto_height_var, command=app.adjust_window_height).pack(side="left", padx=10)
    
    ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=5)
    
    from ui_components import ScrollableFrame
    sf = ScrollableFrame(parent, orient="horizontal")
    sf.pack(fill="both", expand=True)
    app.tab_frame_settings = sf
    
    app.setting_widgets = []
    for i in range(MAX_CLIENTS):
        lf = ttk.Labelframe(sf.inner_frame, text=f"窗口 {i+1}", padding=5)
        vars_d = {"game_speed": tk.IntVar(), "fast_walk": tk.IntVar(), "no_clip": tk.IntVar(), "hide_sa": tk.IntVar()}
        widgets_d = {}
        
        def mk_cmd(func, idx): return lambda: func(idx)
        settings_list = [("game_speed", "遊戲加速", app.on_toggle_speed, "speed"),
                         ("fast_walk", "快速行走", app.on_toggle_walk, "walk"),
                         ("no_clip", "穿牆行走", app.on_toggle_noclip, "noclip"),
                         ("hide_sa", "隱藏石器", app.on_toggle_hide, "hide")]
        
        for var_key, text, func, widget_key in settings_list:
            cb = ttk.Checkbutton(lf, text=text, variable=vars_d[var_key], command=mk_cmd(func, i))
            cb.pack(anchor="w")
            widgets_d[widget_key] = cb
        app.setting_widgets.append({"frame": lf, "vars": vars_d, "widgets": widgets_d})

# --- Canvas 繪圖 ---

def create_client_info_canvas(parent, app):
    scale = LAYOUT_PARAMS["SCALE"]
    col_w = int(LAYOUT_PARAMS["CHAR_COL_WIDTH"])
    row_h = LAYOUT_PARAMS["ROW_HEIGHT"]
    
    total_w = (col_w * 6) + int(20 * scale)
    total_h = (row_h * 11) + 5
    
    bg = app.cget("background")
    cv = tk.Canvas(parent, width=total_w, height=total_h, bg=bg, highlightthickness=0)
    cv.pack(anchor="w", padx=5, pady=5)
    
    items_list = []
    fn = ("微軟正黑體", LAYOUT_PARAMS["FONT_SIZE_NORMAL"])
    fb = ("微軟正黑體", LAYOUT_PARAMS["FONT_SIZE_BOLD"], "bold")
    
    gd = GridDrawer(cv, 5, 10, row_h, fn, fb)
    items_list.append(_draw_person_grid(gd))
    
    for i in range(5):
        line_x = (col_w * (i+1)) + 15
        cv.create_line(line_x, 10, line_x, total_h - 10, fill="#CCCCCC")
        gd = GridDrawer(cv, line_x + 10, 10, row_h, fn, fb)
        items_list.append(_draw_pet_grid(gd, i))
        
    return cv, items_list

def _draw_person_grid(gd):
    """人物欄位繪製 (v4.22 修正魅力位置)"""
    d = {}
    
    # 1. 名稱
    gd.draw_text("人物", 2.2, "name", is_bold=True, items_dict=d); gd.new_row()
    
    # 2. 稱號
    gd.draw_text("稱號", 2.2, "nickname", items_dict=d); gd.new_row()
    
    # 3. LV 轉生
    gd.draw_text("LV:", 0.5)
    gd.draw_text("--", 0.3, "lv", items_dict=d)
    gd.draw_text("--", 1.1, "rebirth", align="e", items_dict=d)
    gd.new_row()
    
    # 4. HP [修正: 位置對調]
    gd.draw_text("HP:", 0.5); gd.draw_text("--/--", 1.7, "hp", items_dict=d); gd.new_row()
    
    # 5. MP [修正: 位置對調]
    gd.draw_text("MP:", 0.5); gd.draw_text("--/--", 1.7, "mp", items_dict=d); gd.new_row()
    
    # 6. 攻擊
    gd.draw_text("攻擊:", 0.5); gd.draw_text("--", 1.7, "atk", items_dict=d); gd.new_row()
    
    # 7. 防禦
    gd.draw_text("防禦:", 0.5); gd.draw_text("--", 1.7, "def", items_dict=d); gd.new_row()
    
    # 8. 敏捷
    gd.draw_text("敏捷:", 0.5); gd.draw_text("--", 1.7, "agi", items_dict=d); gd.new_row()
    
    # 9. 屬性 + 魅力 (修正：將魅力移回此行末端)
    # 空間分配: 屬性標題(0.35) + 4個數值(1.28) + 魅標題(0.25) + 魅數值(0.32) = 2.2
    gd.draw_text("屬性:", 0.5)
    for i in range(4): 
        gd.draw_text("", 0.35, f"elem_{i+1}_val", items_dict=d)
    
    # [關鍵修改] 手動將 X 座標往回拉 (數值可自行調整)
    # 這裡扣掉 50px (隨縮放比例調整)，讓魅力無視前面屬性的空位，直接往左貼
    from app_ui import LAYOUT_PARAMS
    gd.x -= int(42 * LAYOUT_PARAMS["SCALE"]) 
    
    gd.draw_text("魅力:", 0.54)
    gd.draw_text("--", 0.32, "charm", items_dict=d)
    
    # 只有人物畫底線
    gd.draw_line_below(2.2) 
    gd.new_row()
    
    # 10. 體腕
    gd.draw_text("體力:", 0.5); gd.draw_text("--", 0.7, "vit", items_dict=d)
    gd.draw_text("腕力:", 0.54); gd.draw_text("--", 0.6, "str", items_dict=d); gd.new_row()
    
    # 11. 耐速
    gd.draw_text("耐力:", 0.5); gd.draw_text("--", 0.7, "sta", items_dict=d)
    gd.draw_text("速度:", 0.54); gd.draw_text("--", 0.6, "spd", items_dict=d)

    return d

def _draw_pet_grid(gd, idx):
    d = {}
    title = f"寵物{num_to_chinese(idx+1)}"
    gd.draw_text(title, 2.2, "name", is_bold=True, items_dict=d); gd.new_row()
    gd.draw_text("", 2.2, "nickname", items_dict=d); gd.new_row()
    
    # [修改] 為標籤 (Label) 加上 key (例如 "lbl_lv") 以便後續隱藏
    gd.draw_text("LV:", 0.5, "lbl_lv", items_dict=d)
    gd.draw_text("--", 0.3, "lv", items_dict=d)
    gd.draw_text("--", 1.1, "rebirth", align="e", items_dict=d)
    gd.new_row()
    
    gd.draw_text("HP:", 0.45, "lbl_hp", items_dict=d)
    gd.draw_text("--/--", 1.75, "hp", items_dict=d); gd.new_row()
    
    gd.new_row() # 空行
    
    gd.draw_text("攻擊:", 0.5, "lbl_atk", items_dict=d); gd.draw_text("--", 1.7, "atk", items_dict=d); gd.new_row()
    gd.draw_text("防禦:", 0.5, "lbl_def", items_dict=d); gd.draw_text("--", 1.7, "def", items_dict=d); gd.new_row()
    gd.draw_text("敏捷:", 0.5, "lbl_agi", items_dict=d); gd.draw_text("--", 1.7, "agi", items_dict=d); gd.new_row()
    
    gd.draw_text("屬性:", 0.5, "lbl_elem", items_dict=d)
    for i in range(4): gd.draw_text("", 0.35, f"elem_{i+1}_val", items_dict=d)
    
    # 手動拉回 X 座標繪製忠誠
    gd.x -= int(42 * LAYOUT_PARAMS["SCALE"])
    gd.draw_text("忠誠:", 0.54, "lbl_loyal", items_dict=d)
    gd.draw_text("--", 0.9, "loyal", items_dict=d)
    gd.new_row()
    
    gd.draw_text("經驗:", 0.5, "lbl_exp", items_dict=d); gd.draw_text("--", 1.7, "exp", items_dict=d); gd.new_row()
    
    gd.draw_text("還欠:", 0.5, "lbl_lack", items_dict=d); gd.draw_text("--", 1.7, "lack", items_dict=d)
    # 最後一行
    return d

def create_item_client_panel(parent, account_name):
    # [修改] 這裡指定道具面板的基礎寬度為 850 (維持原樣)
    return _create_dual_col_panel(parent, account_name, _draw_items_content, base_width=850)

def create_battle_client_panel(parent, account_name):
    # [修改] 這裡指定戰鬥面板的基礎寬度為 600
    return _create_dual_col_panel(parent, account_name, _draw_battle_content, base_width=600)

def _create_dual_col_panel(parent, title, content_func, base_width=850):
    lf = ttk.Labelframe(parent, text=title, padding=2)
    lf.pack(fill="x", padx=5, pady=2, anchor="n")
    row_h = LAYOUT_PARAMS["ROW_HEIGHT"]
    
    is_item = "item" in content_func.__name__
    
    # [關鍵修改] 將 else (戰鬥面板) 的預設行數改為 16 (原本是 12)
    # 這樣外框高度才足夠容納拉長的陣型
    lines = 14 if is_item else 16
    
    h = lines * row_h + 10
    
    try: bg = ttk.Style().lookup("TFrame", "background") or "#f0f0f0"
    except: bg = "#f0f0f0"

    scale = LAYOUT_PARAMS["SCALE"]
    final_width = int(base_width * scale) 

    cv = tk.Canvas(lf, width=final_width, height=h, bg=bg, highlightthickness=0)
    cv.pack(fill="both", expand=True)
    
    ids_container = content_func(cv, row_h, width=final_width)
    
    return {"frame": lf, "canvas": cv, "ids": ids_container}

def _draw_items_content(cv, rh, width=None):
    width = 1000
    if width is None: width = 2000
    mid = width // 2
    ids = {}
    fn = ("微軟正黑體", LAYOUT_PARAMS["FONT_SIZE_NORMAL"])
    fb = ("微軟正黑體", LAYOUT_PARAMS["FONT_SIZE_BOLD"], "bold")
    from constants import EQUIP_DISPLAY_ORDER, EQUIP_MAPPING
    
    # 畫中間的垂直分隔線
    cv.create_line(mid, 5, mid, rh*14, fill="#AAAAAA", tags="sep_line")
    
    # --- 左欄 (裝備 + 道具1-2) ---
    gd = GridDrawer(cv, 10, 10, rh, fn, fb)
    gd.draw_text("【裝備】", 4.0, is_bold=True, color="#0000AA"); gd.new_row()
    
    for idx in EQUIP_DISPLAY_ORDER:
        prefix = EQUIP_MAPPING.get(idx, "??")
        ids[idx] = gd.draw_text(f"{prefix}: --", 5.0); gd.new_row()
    
    # [修改 1] 垂直置中：直接使用 gd.y (行中心) 畫線，移除原本的 (rh // 2) 偏移
    # 這樣線條就會位於 "最後一個裝備" 和 "道具1-2標題" 的正中間
    line_y = gd.y 
    
    # [修改 2] 寬度調整：長度改為整體寬度的一半 (即左欄寬度 mid)
    # 設定左右留 10px 邊距，使其橫跨左欄
    cv.create_line(10, line_y, mid - 10, line_y, fill="#DDDDDD")
    
    gd.new_row() # 換行準備寫標題
    
    gd.draw_text("【道具 1-2】", 4.0, is_bold=True, color="#0000AA"); gd.new_row()
    for idx in range(2):
        ids[idx] = gd.draw_text(f"{idx+1:02d}: --", 5.0); gd.new_row()
        
    # --- 右欄 (道具 3-15) ---
    gd = GridDrawer(cv, mid + 10, 10, rh, fn, fb)
    gd.draw_text("【道具 3-15】", 4.0, is_bold=True, color="#0000AA"); gd.new_row()
    for idx in range(2, 15):
        ids[idx] = gd.draw_text(f"{idx+1:02d}: --", 5.0); gd.new_row()
        
    return ids

def _draw_battle_content(cv, rh, width=None):
    if width is None: width = 600
    
    unit_w = width // 6
    mid_x = width // 2
    
    step_compact = int(rh * 2.0)
    step_spread = int(rh * 2.3)
    
    center_y = 10 + (2 * step_spread)
    pet_offset = int(100 * LAYOUT_PARAMS["SCALE"])
    
    # 定義各欄位 X 座標
    col1_x = 10
    col2_x = mid_x - unit_w + 10 
    col3_x = mid_x + 10
    col4_x = mid_x + unit_w + 10

    # [修改重點 1] 移動目標 target_x 改為 "col1_x + pet_offset"
    # 這樣人物就會移動到 "原本該欄位騎寵的位置" (視覺上的前排)
    target_pos_x = col1_x + pet_offset

    cols_config = [
        {"ids": [14, 12, 10, 11, 13], "x": col1_x, "step": step_spread, "allow_move": True, "target_x": target_pos_x},
        {"ids": [19, 17, 15, 16, 18], "x": col2_x, "step": step_compact, "allow_move": False},
        {"ids": [9, 7, 5, 6, 8],      "x": col3_x, "step": step_compact, "allow_move": False},
        {"ids": [4, 2, 0, 1, 3],      "x": col4_x, "step": step_spread, "allow_move": False},
    ]

    ids = {}
    fn = ("微軟正黑體", LAYOUT_PARAMS["FONT_SIZE_NORMAL"])
    
    for cfg in cols_config:
        item_ids = cfg["ids"]
        base_x = cfg["x"]
        step = cfg["step"]
        can_move = cfg.get("allow_move", False)
        tgt_x = cfg.get("target_x", None)
        
        for i, pid in enumerate(item_ids):
            offset = (i - 2) * step
            draw_y = center_y + offset
            
            tid_h = cv.create_text(base_x, draw_y, text="", font=fn, anchor="nw", fill="black")
            tid_p = cv.create_text(base_x + pet_offset, draw_y, text="", font=fn, anchor="nw", fill="black")
            
            ids[pid] = {
                "h": tid_h,
                "p": tid_p,
                "ox": base_x,       
                "oy": draw_y,       
                "off": pet_offset,
                "allow_move": can_move,
                "target_x": tgt_x
            }

    max_y = center_y + (2 * step_spread) + int(rh * 3.5)
    cv.create_line(mid_x, 5, mid_x, max_y - 5, fill="#DDDDDD", dash=(4, 2))
    cv.configure(height=max_y)
    
    return ids

def update_battle_canvas(cv, ids, cache, state):
    cmd_idx = cache.get("cmd_idx", -1)
    
    # [修改重點 2] 判斷目標 ID 
    target_pids = []
    if isinstance(cmd_idx, int) and 0 <= cmd_idx <= 20:
        target_pids = [cmd_idx, cmd_idx + 5]

    fn = ("微軟正黑體", LAYOUT_PARAMS["FONT_SIZE_NORMAL"])
    fb = ("微軟正黑體", LAYOUT_PARAMS["FONT_SIZE_BOLD"], "bold")

    for pid, info in ids.items():
        tid_h = info["h"]
        tid_p = info["p"]
        ox = info["ox"]
        oy = info["oy"]
        off = info["off"]
        
        allow_move = info.get("allow_move", False)
        target_x = info.get("target_x")

        if state != 10: 
            cv.itemconfigure(tid_h, text=""); cv.itemconfigure(tid_p, text="")
            continue
            
        data = cache.get(pid)
        if not data:
            cv.itemconfigure(tid_h, text=""); cv.itemconfigure(tid_p, text="")
            continue

        # 移動邏輯：若無騎寵，移動到 target_x (現在是 pet_offset 的位置)
        cur_x = ox 
        if allow_move and target_x is not None:
            if not data.get("pet_info"): 
                cur_x = target_x
        
        cv.coords(tid_h, cur_x, oy)
        cv.coords(tid_p, cur_x + off, oy)

        name = data.get("name", "??")
        hp = data.get("hp", 0)
        max_hp = data.get("max_hp", 0)
        pet_data = data.get("pet_info")
        
        # [修改重點 3] 樣式處理
        is_target = (pid in target_pids)
        
        # 名稱處理：選中時加 *
        display_name_h = f"* {name}" if is_target else name
        text_h = f"{display_name_h}\n  ({hp}/{max_hp})"
        
        text_p = ""
        if pet_data:
            p_name = pet_data.get("name", "??")
            p_hp = pet_data.get("hp", 0)
            p_max = pet_data.get("max_hp", 0)
            display_name_p = f"* {p_name}" if is_target else p_name
            text_p = f"{display_name_p}\n  ({p_hp}/{p_max})"
        
        # 字體處理：選中時變粗體
        font_style = fb if is_target else fn
        
        # 顏色處理：死亡優先顯示紅色，取消藍色，其餘黑色
        color_h = "red" if int(hp) <= 0 else "black"
        color_p = "black"
        
        cv.itemconfigure(tid_h, text=text_h, fill=color_h, font=font_style)
        cv.itemconfigure(tid_p, text=text_p, fill=color_p, font=font_style)

def update_char_canvas(cv, items, d):
    if not d:
        cv.itemconfigure(items["name"], text="人物"); cv.itemconfigure(items["hp"], text="--/--")
        return
    cv.itemconfigure(items["name"], text=d.get("name", "人物"))
    cv.itemconfigure(items["nickname"], text=d.get("nickname", "稱號"))
    cv.itemconfigure(items["lv"], text=d.get("lv", "--"))
    cv.itemconfigure(items["hp"], text=d.get("hp", "--/--"))
    cv.itemconfigure(items["mp"], text=d.get("mp", "--/--"))
    for k in ["atk", "def", "agi", "vit", "str", "sta", "spd"]:
        cv.itemconfigure(items[k], text=d.get(k, "--"))
    cv.itemconfigure(items["charm"], text=d.get("charm", 0), fill="red" if d.get("charm", 0) <= 60 else "black")
    rt = d.get("rebirth", "未知")
    cv.itemconfigure(items["rebirth"], text=rt, fill=REBIRTH_COLOR_MAP.get(rt, "black"))
    
    # [修正] 屬性動態遞補邏輯
    raw = d.get("element_raw", (0,0,0,0))
    # 定義標籤與顏色
    attr_defs = [("地", "green"), ("水", "blue"), ("火", "red"), ("風", "#E5C100")]
    
    # 找出所有大於 0 的屬性
    valid_attrs = []
    for i, val in enumerate(raw):
        if val > 0:
            text_str = f"{attr_defs[i][0]}{val//10}"
            color = attr_defs[i][1]
            valid_attrs.append((text_str, color))
            
    # 依序填入插槽
    for i in range(4):
        tid = items[f"elem_{i+1}_val"]
        if i < len(valid_attrs):
            cv.itemconfigure(tid, text=valid_attrs[i][0], fill=valid_attrs[i][1])
        else:
            cv.itemconfigure(tid, text="") # 清空多餘插槽

def update_pet_canvas(cv, items, d, idx):
    default = f"寵物{num_to_chinese(idx+1)}"
    
    # 定義需要控制顯示/隱藏的標籤
    label_map = {
        "lbl_lv": "LV:", "lbl_hp": "HP:", "lbl_atk": "攻擊:", 
        "lbl_def": "防禦:", "lbl_agi": "敏捷:", "lbl_elem": "屬性:", 
        "lbl_loyal": "忠誠:", "lbl_exp": "經驗:", "lbl_lack": "還欠:"
    }

    if not d:
        # [修改] 若無寵物資料：清空所有欄位與標籤，只保留標題
        cv.itemconfigure(items["name"], text=default, fill="black")
        cv.itemconfigure(items["nickname"], text="")
        
        # 清空數值
        for k in ["lv", "rebirth", "hp", "atk", "def", "agi", "loyal", "exp", "lack"]:
             if k in items: cv.itemconfigure(items[k], text="")
        
        # 清空屬性圖示
        for i in range(4):
            if f"elem_{i+1}_val" in items: cv.itemconfigure(items[f"elem_{i+1}_val"], text="")

        # 清空標籤 (LV:, HP: 等)
        for k in label_map:
            if k in items: cv.itemconfigure(items[k], text="")
            
        return

    # [修改] 若有寵物資料：先還原標籤文字
    for k, txt in label_map.items():
        if k in items: cv.itemconfigure(items[k], text=txt)

    # 以下為原本的數值更新邏輯
    st = d.get("status_text", "休")
    col = REBIRTH_COLOR_MAP.get(d.get("status_color_key"), "black")
    cv.itemconfigure(items["name"], text=f"[{st}] {d.get('name', default)}", fill=col)
    cv.itemconfigure(items["nickname"], text=d.get("nickname", ""))
    cv.itemconfigure(items["lv"], text=d.get("lv", "--"))
    cv.itemconfigure(items["exp"], text=d.get("exp", "--"))
    cv.itemconfigure(items["lack"], text=d.get("lack", "--"))
    cv.itemconfigure(items["hp"], text=d.get("hp", "--/--"))
    cv.itemconfigure(items["atk"], text=d.get("atk", "--"))
    cv.itemconfigure(items["def"], text=d.get("def", "--"))
    cv.itemconfigure(items["agi"], text=d.get("agi", "--"))
    
    rt = d.get("rebirth", "未知")
    cv.itemconfigure(items["rebirth"], text=rt, fill=REBIRTH_COLOR_MAP.get(rt, "black"))
    
    loyal = d.get("loyal", 100)
    cv.itemconfigure(items["loyal"], text=loyal, fill="red" if loyal <= 20 else "black")
    
    # 屬性動態顯示
    raw = d.get("element_raw", (0,0,0,0))
    attr_defs = [("地", "green"), ("水", "blue"), ("火", "red"), ("風", "#E5C100")]
    
    valid_attrs = []
    for i, val in enumerate(raw):
        if val > 0:
            text_str = f"{attr_defs[i][0]}{val//10}"
            color = attr_defs[i][1]
            valid_attrs.append((text_str, color))
            
    for i in range(4):
        tid = items[f"elem_{i+1}_val"]
        if i < len(valid_attrs):
            cv.itemconfigure(tid, text=valid_attrs[i][0], fill=valid_attrs[i][1])
        else:
            cv.itemconfigure(tid, text="")

def update_items_canvas(cv, ids, cache):
    from constants import EQUIP_MAPPING
    for idx, tid in ids.items():
        item = cache.get(idx)
        if not item:
            prefix = EQUIP_MAPPING.get(idx, f"{idx+1:02d}")
            cv.itemconfigure(tid, text=f"{prefix}: (空)", fill="#888888")
        else:
            stack = f" [{item['stack']}]" if item['stack'] > 1 else ""
            dur = f" {item['dur']}" if item['dur'] and "不會損壞" not in item['dur'] else ""
            
            # [修改] 處理說明文字
            desc_str = ""
            if item['desc']:
                # 1. 先將連續2個以上的空白縮減為1個
                d_clean = re.sub(r' {2,}', ' ', item['desc'])
                # 2. 原有的邏輯：移除 +/- 號周圍的空白
                d_clean = re.sub(r'\s*([+-])\s*', r'\1', d_clean)
                desc_str = f" {{{d_clean}}}"
            
            full = f"{EQUIP_MAPPING.get(idx, f'{idx+1:02d}')}:{stack} {item['name']}{desc_str}{dur}"
            
            color = DEFAULT_ITEM_COLOR
            for c, kws in ITEM_COLOR_RULES.items():
                if any(k in item['name'] for k in kws): color = c; break
            cv.itemconfigure(tid, text=full, fill=color)
