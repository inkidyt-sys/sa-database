# app_ui.py
# 負責 UI 佈局定義與 Canvas 繪圖邏輯

import tkinter as tk
from tkinter import ttk
import sys

from ui_components import ScrollableFrame
from constants import MAX_CLIENTS, DEFAULT_FG_COLOR, ELEMENT_COLOR_MAP
from utils import num_to_chinese

# --- UI 佈局基礎參數 (以 100% 為基準) ---
BASE_PARAMS = {
    "APP_BASE_WIDTH": 950, "APP_BASE_HEIGHT": 250,
    "LEFT_PANEL_WIDTH": 150, "NON_CONTENT_HEIGHT": 150,
    "CANVAS_ROW_PADDING": 15,
    "LEFT_CHECKBOX_PADY": 1, "SETTINGS_CHECKBOX_PADY": 1,
    
    # 人寵 Canvas
    "CANVAS_FONT_SIZE": 8.5,
    "CANVAS_Y_START": 8, "CANVAS_Y_STEP": 15,
    "CANVAS_COL_WIDTH": 110, "CANVAS_COL_PADDING": 8, "CANVAS_START_X": 5,
    "CANVAS_X_VAL_1": 25, "CANVAS_X_LBL_2": 60, "CANVAS_X_VAL_2": 85,
    "CANVAS_ELEM_VAL_OFFSET": 13, "CANVAS_ELEM_STEP": 30,
    "CANVAS_PERSON_Y_ADJ_1": 0, "CANVAS_PERSON_Y_ADJ_2": 0,
    
    # 道具列表
    "ITEM_CANVAS_HEIGHT": 230,
    "ITEM_FONT_SIZE": 9,
    "ITEM_ROW_HEIGHT": 14,
    "ITEM_COL_1_X": 10, "ITEM_COL_2_X": 410, "ITEM_SEPARATOR_X": 400,
    "ITEM_HEADER_Y_OFFSET": 5, "ITEM_ACCOUNT_PAD_Y": 5,

    # 戰鬥狀態
    "BATTLE_CANVAS_HEIGHT": 200,
    "BATTLE_FONT_SIZE": 9,
    "BATTLE_ROW_HEIGHT": 16,
    "BATTLE_COL_1_X": 10, "BATTLE_COL_2_X": 180, "BATTLE_SEPARATOR_X": 170,
    "BATTLE_HEADER_Y_OFFSET": 5, "BATTLE_ACCOUNT_PAD_Y": 5,
}

# --- 當前使用的佈局參數 (全域) ---
# 將由 update_layout_params 動態寫入
CURRENT_PARAMS = {}

# 為了兼容 main.py 的舊調用方式，保留這些全域變數的映射
RESOLUTION_RATIO = 1.0
LAYOUT_APP_BASE_WIDTH = 0
LAYOUT_APP_BASE_HEIGHT = 0
LAYOUT_LEFT_PANEL_WIDTH = 0
LAYOUT_NON_CONTENT_HEIGHT = 0
LAYOUT_CANVAS_ROW_PADDING = 0
LAYOUT_LEFT_CHECKBOX_PADY = 0
LAYOUT_SETTINGS_CHECKBOX_PADY = 0
LAYOUT_CANVAS_BASE_FONT_SIZE = 1
LAYOUT_CANVAS_BASE_Y_START = 0
LAYOUT_CANVAS_BASE_Y_STEP = 0
LAYOUT_CANVAS_BASE_COL_WIDTH = 0
LAYOUT_CANVAS_BASE_COL_PADDING = 0
LAYOUT_CANVAS_BASE_START_X = 0
LAYOUT_CANVAS_X_VALUE_1 = 0
LAYOUT_CANVAS_X_LABEL_2 = 0
LAYOUT_CANVAS_X_VALUE_2 = 0
LAYOUT_CANVAS_ELEM_VAL_OFFSET = 0
LAYOUT_CANVAS_ELEM_STEP = 0
LAYOUT_CANVAS_PERSON_Y_ADJUST_1 = 0
LAYOUT_CANVAS_PERSON_Y_ADJUST_2 = 0
BASE_CANVAS_ROW_HEIGHT = 0
FINAL_CANVAS_ROW_TOTAL_HEIGHT = 0

# 道具與戰鬥參數
LAYOUT_ITEM_CANVAS_HEIGHT = 0
LAYOUT_ITEM_FONT_SIZE = 0
LAYOUT_ITEM_ROW_HEIGHT = 0
LAYOUT_ITEM_COL_1_X = 0
LAYOUT_ITEM_COL_2_X = 0
LAYOUT_ITEM_SEPARATOR_X = 0
LAYOUT_ITEM_HEADER_Y_OFFSET = 0
LAYOUT_ITEM_ACCOUNT_PAD_Y = 0
LAYOUT_BATTLE_CANVAS_HEIGHT = 0
LAYOUT_BATTLE_FONT_SIZE = 0
LAYOUT_BATTLE_ROW_HEIGHT = 0
LAYOUT_BATTLE_COL_1_X = 0
LAYOUT_BATTLE_COL_2_X = 0
LAYOUT_BATTLE_SEPARATOR_X = 0
LAYOUT_BATTLE_HEADER_Y_OFFSET = 0
LAYOUT_BATTLE_ACCOUNT_PAD_Y = 0


def update_layout_params(user_scale):
    """根據縮放比例重新計算全域佈局參數"""
    global RESOLUTION_RATIO, CURRENT_PARAMS
    global LAYOUT_APP_BASE_WIDTH, LAYOUT_APP_BASE_HEIGHT, LAYOUT_LEFT_PANEL_WIDTH, LAYOUT_NON_CONTENT_HEIGHT
    global LAYOUT_CANVAS_ROW_PADDING, LAYOUT_LEFT_CHECKBOX_PADY, LAYOUT_SETTINGS_CHECKBOX_PADY
    global LAYOUT_CANVAS_BASE_FONT_SIZE, LAYOUT_CANVAS_BASE_Y_START, LAYOUT_CANVAS_BASE_Y_STEP
    global LAYOUT_CANVAS_BASE_COL_WIDTH, LAYOUT_CANVAS_BASE_COL_PADDING, LAYOUT_CANVAS_BASE_START_X
    global LAYOUT_CANVAS_X_VALUE_1, LAYOUT_CANVAS_X_LABEL_2, LAYOUT_CANVAS_X_VALUE_2
    global LAYOUT_CANVAS_ELEM_VAL_OFFSET, LAYOUT_CANVAS_ELEM_STEP, LAYOUT_CANVAS_PERSON_Y_ADJUST_1, LAYOUT_CANVAS_PERSON_Y_ADJUST_2
    global BASE_CANVAS_ROW_HEIGHT, FINAL_CANVAS_ROW_TOTAL_HEIGHT
    global LAYOUT_ITEM_CANVAS_HEIGHT, LAYOUT_ITEM_FONT_SIZE, LAYOUT_ITEM_ROW_HEIGHT, LAYOUT_ITEM_COL_1_X, LAYOUT_ITEM_COL_2_X, LAYOUT_ITEM_SEPARATOR_X, LAYOUT_ITEM_HEADER_Y_OFFSET, LAYOUT_ITEM_ACCOUNT_PAD_Y
    global LAYOUT_BATTLE_CANVAS_HEIGHT, LAYOUT_BATTLE_FONT_SIZE, LAYOUT_BATTLE_ROW_HEIGHT, LAYOUT_BATTLE_COL_1_X, LAYOUT_BATTLE_COL_2_X, LAYOUT_BATTLE_SEPARATOR_X, LAYOUT_BATTLE_HEADER_Y_OFFSET, LAYOUT_BATTLE_ACCOUNT_PAD_Y

    RESOLUTION_RATIO = user_scale
    
    # 映射函數：根據比例計算新數值
    def S(val): return int(val * user_scale)
    def SF(val): return max(int(val * user_scale), 1)

    # 寫入全域變數
    LAYOUT_APP_BASE_WIDTH = S(BASE_PARAMS["APP_BASE_WIDTH"])
    LAYOUT_APP_BASE_HEIGHT = S(BASE_PARAMS["APP_BASE_HEIGHT"])
    LAYOUT_LEFT_PANEL_WIDTH = S(BASE_PARAMS["LEFT_PANEL_WIDTH"])
    LAYOUT_NON_CONTENT_HEIGHT = S(BASE_PARAMS["NON_CONTENT_HEIGHT"])
    LAYOUT_CANVAS_ROW_PADDING = S(BASE_PARAMS["CANVAS_ROW_PADDING"])
    LAYOUT_LEFT_CHECKBOX_PADY = S(BASE_PARAMS["LEFT_CHECKBOX_PADY"])
    LAYOUT_SETTINGS_CHECKBOX_PADY = S(BASE_PARAMS["SETTINGS_CHECKBOX_PADY"])

    LAYOUT_CANVAS_BASE_FONT_SIZE = SF(BASE_PARAMS["CANVAS_FONT_SIZE"])
    LAYOUT_CANVAS_BASE_Y_START = S(BASE_PARAMS["CANVAS_Y_START"])
    LAYOUT_CANVAS_BASE_Y_STEP = S(BASE_PARAMS["CANVAS_Y_STEP"])
    LAYOUT_CANVAS_BASE_COL_WIDTH = S(BASE_PARAMS["CANVAS_COL_WIDTH"])
    LAYOUT_CANVAS_BASE_COL_PADDING = S(BASE_PARAMS["CANVAS_COL_PADDING"])
    LAYOUT_CANVAS_BASE_START_X = S(BASE_PARAMS["CANVAS_START_X"])
    LAYOUT_CANVAS_X_VALUE_1 = S(BASE_PARAMS["CANVAS_X_VAL_1"])
    LAYOUT_CANVAS_X_LABEL_2 = S(BASE_PARAMS["CANVAS_X_LBL_2"])
    LAYOUT_CANVAS_X_VALUE_2 = S(BASE_PARAMS["CANVAS_X_VAL_2"])
    LAYOUT_CANVAS_ELEM_VAL_OFFSET = S(BASE_PARAMS["CANVAS_ELEM_VAL_OFFSET"])
    LAYOUT_CANVAS_ELEM_STEP = S(BASE_PARAMS["CANVAS_ELEM_STEP"])
    LAYOUT_CANVAS_PERSON_Y_ADJUST_1 = S(BASE_PARAMS["CANVAS_PERSON_Y_ADJ_1"])
    LAYOUT_CANVAS_PERSON_Y_ADJUST_2 = S(BASE_PARAMS["CANVAS_PERSON_Y_ADJ_2"])

    # 道具參數
    LAYOUT_ITEM_CANVAS_HEIGHT = S(BASE_PARAMS["ITEM_CANVAS_HEIGHT"])
    LAYOUT_ITEM_FONT_SIZE = SF(BASE_PARAMS["ITEM_FONT_SIZE"])
    LAYOUT_ITEM_ROW_HEIGHT = S(BASE_PARAMS["ITEM_ROW_HEIGHT"])
    LAYOUT_ITEM_COL_1_X = S(BASE_PARAMS["ITEM_COL_1_X"])
    LAYOUT_ITEM_COL_2_X = S(BASE_PARAMS["ITEM_COL_2_X"])
    LAYOUT_ITEM_SEPARATOR_X = S(BASE_PARAMS["ITEM_SEPARATOR_X"])
    LAYOUT_ITEM_HEADER_Y_OFFSET = S(BASE_PARAMS["ITEM_HEADER_Y_OFFSET"])
    LAYOUT_ITEM_ACCOUNT_PAD_Y = S(BASE_PARAMS["ITEM_ACCOUNT_PAD_Y"])

    # 戰鬥參數
    LAYOUT_BATTLE_CANVAS_HEIGHT = S(BASE_PARAMS["BATTLE_CANVAS_HEIGHT"])
    LAYOUT_BATTLE_FONT_SIZE = SF(BASE_PARAMS["BATTLE_FONT_SIZE"])
    LAYOUT_BATTLE_ROW_HEIGHT = S(BASE_PARAMS["BATTLE_ROW_HEIGHT"])
    LAYOUT_BATTLE_COL_1_X = S(BASE_PARAMS["BATTLE_COL_1_X"])
    LAYOUT_BATTLE_COL_2_X = S(BASE_PARAMS["BATTLE_COL_2_X"])
    LAYOUT_BATTLE_SEPARATOR_X = S(BASE_PARAMS["BATTLE_SEPARATOR_X"])
    LAYOUT_BATTLE_HEADER_Y_OFFSET = S(BASE_PARAMS["BATTLE_HEADER_Y_OFFSET"])
    LAYOUT_BATTLE_ACCOUNT_PAD_Y = S(BASE_PARAMS["BATTLE_ACCOUNT_PAD_Y"])

    # 計算衍生高度
    BASE_CANVAS_ROW_HEIGHT = (LAYOUT_CANVAS_BASE_Y_START + (10 * LAYOUT_CANVAS_BASE_Y_STEP) + LAYOUT_CANVAS_BASE_Y_START)
    FINAL_CANVAS_ROW_TOTAL_HEIGHT = (BASE_CANVAS_ROW_HEIGHT + LAYOUT_CANVAS_ROW_PADDING)


# --- UI 建構函式 ---

def create_main_widgets(app):
    """建立主視窗框架"""
    main_frame = ttk.Frame(app, padding=10)
    main_frame.pack(fill="both", expand=True)

    # 左側控制區
    left_frame = ttk.Frame(main_frame, width=app.scaled_left_panel_width, padding=(5,5,5,5), relief="groove")
    left_frame.pack(side="left", fill="y", padx=(0, 10))
    left_frame.pack_propagate(False)

    ttk.Button(left_frame, text="綁定石器", command=app.on_bind_click).pack(fill="x", pady=(5, 10), ipady=3)

    bg = app.cget('background')
    for i in range(MAX_CLIENTS):
        cb = tk.Checkbutton(
            left_frame, text=f"窗口 {i+1}: 未綁定",
            variable=app.client_selection_vars[i],
            onvalue=1, offvalue=0, command=app.on_selection_change,
            state="disabled", disabledforeground="grey", anchor="w",
            bg=bg, selectcolor=bg, padx=0
        )
        cb.pack(anchor="w", pady=LAYOUT_LEFT_CHECKBOX_PADY)
        cb.bind("<Button-3>", lambda e, idx=i: app.on_client_right_click_single(e, idx))
        cb.bind("<Double-Button-3>", lambda e, idx=i: app.on_client_right_click_double(e, idx))
        app.client_checkboxes.append(cb)

    # 右側 Notebook
    right_frame = ttk.Frame(main_frame, relief="sunken")
    right_frame.pack(side="right", fill="both", expand=True)

    app.notebook = ttk.Notebook(right_frame)
    app.notebook.pack(fill="both", expand=True)
    app.notebook.bind("<<NotebookTabChanged>>", app.on_tab_changed)

    tabs = [("遊戲設置", create_settings_tab), ("人寵資料", create_character_tab), 
            ("道具列表", create_items_tab), ("戰鬥狀態", create_battle_tab), ("聊天窗口", None)]

    for name, builder in tabs:
        frame = ttk.Frame(app.notebook, padding=5)
        app.notebook.add(frame, text=name)
        app.tabs[name] = frame
        if builder: builder(frame, app)
    
    app.notebook.tab(4, state="disabled")

def create_settings_tab(tab_frame, app):
    gs_frame = ttk.Frame(tab_frame)
    gs_frame.pack(fill="x", pady=(0, 5))

    # 設置選項
    settings = [
        ("刷新頻率:", app.refresh_rate_var, ['0.5s', '1s', '3s', '5s', '10s', '60s', '不刷新'], app.on_refresh_rate_change),
        ("視窗縮放:", app.zoom_var, ['75%', '90%', '100%', '110%', '125%', '150%'], app.on_zoom_change)
    ]

    for label, var, values, cmd in settings:
        ttk.Label(gs_frame, text=label).pack(side="left", padx=(5, 5))
        cb = ttk.Combobox(gs_frame, textvariable=var, values=values, state="readonly", width=8)
        cb.pack(side="left", padx=(0, 10))
        cb.bind("<<ComboboxSelected>>", cmd)

    # 自動高度
    ttk.Checkbutton(gs_frame, text="自動拉伸高度", variable=app.auto_height_var, 
                    command=lambda: app.adjust_window_height() if app.auto_height_var.get() else None).pack(side="left", padx=5)

    ttk.Separator(tab_frame, orient="horizontal").pack(fill="x", pady=(5, 10))
    
    # 客戶端個別設置
    app.tab_frame_settings = ScrollableFrame(tab_frame, orient="horizontal")
    app.tab_frame_settings.pack(fill="both", expand=True)
    app.setting_widgets = []
    
    for i in range(MAX_CLIENTS):
        frame = ttk.Labelframe(app.tab_frame_settings.inner_frame, text=f"窗口 {i+1}", padding=5)
        vars_dict, widgets_dict = _create_client_settings(frame, i, app)
        app.setting_widgets.append({"frame": frame, "vars": vars_dict, "widgets": widgets_dict})

def _create_client_settings(parent, idx, app):
    sv = {"game_speed": tk.IntVar(), "fast_walk": tk.IntVar(), "no_clip": tk.IntVar(), "hide_sa": tk.IntVar()}
    actions = [
        ("遊戲加速", sv["game_speed"], lambda: app.on_toggle_speed(idx)),
        ("快速行走", sv["fast_walk"], lambda: app.on_toggle_walk(idx)),
        ("穿牆行走", sv["no_clip"], lambda: app.on_toggle_noclip(idx)),
        ("隱藏石器", sv["hide_sa"], lambda: app.on_toggle_hide(idx)),
    ]
    widgets = {}
    names = ["speed", "walk", "noclip", "hide"]
    
    for (txt, var, cmd), name in zip(actions, names):
        cb = ttk.Checkbutton(parent, text=txt, variable=var, command=cmd)
        cb.pack(anchor="w", pady=LAYOUT_SETTINGS_CHECKBOX_PADY)
        widgets[name] = cb
    return sv, widgets

def create_character_tab(tab_frame, app):
    app.tab_frame_char = ScrollableFrame(tab_frame, orient="vertical")
    app.tab_frame_char.pack(fill="both", expand=True)
    app.tab_frame_char.inner_frame.columnconfigure(0, weight=1)

def create_items_tab(tab_frame, app):
    app.tab_frame_items = ScrollableFrame(tab_frame, orient="vertical")
    app.tab_frame_items.pack(fill="both", expand=True)
    app.client_item_ui = {}

def create_battle_tab(tab_frame, app):
    app.tab_frame_battle = ScrollableFrame(tab_frame, orient="vertical")
    app.tab_frame_battle.pack(fill="both", expand=True)
    app.client_battle_ui = {}

# --- 繪圖邏輯 (Factory Methods) ---

def create_client_info_canvas(parent, app):
    """建立人寵資料 Canvas"""
    col_w, pad, start_x = LAYOUT_CANVAS_BASE_COL_WIDTH, LAYOUT_CANVAS_BASE_COL_PADDING, LAYOUT_CANVAS_BASE_START_X
    w = (col_w * 6) + (pad * 5) + (start_x * 2)
    h = BASE_CANVAS_ROW_HEIGHT
    
    try: bg = parent.cget("background")
    except: bg = app.cget("background")

    cv = tk.Canvas(parent, width=w, height=h, bg=bg, highlightthickness=0)
    cv.pack(anchor="w", padx=5, pady=5)
    
    items = [_draw_person(cv, start_x)]
    for i in range(5):
        x = start_x + (col_w + pad) * (i + 1)
        # 分隔線
        line_x = x - (pad // 2) - 1
        cv.create_line(line_x, 10, line_x, h - 10, fill="#CCCCCC")
        items.append(_draw_pet(cv, x, i))
    return cv, items

def _draw_text_row(cv, x, y, label, val_x, key, font_n):
    cv.create_text(x, y, text=label, font=font_n, anchor="w", fill=DEFAULT_FG_COLOR)
    return cv.create_text(val_x, y, text="--", font=font_n, anchor="w", fill=DEFAULT_FG_COLOR)

def _draw_person(cv, x):
    d = {}
    y, step = LAYOUT_CANVAS_BASE_Y_START, LAYOUT_CANVAS_BASE_Y_STEP
    fn = ("微軟正黑體", LAYOUT_CANVAS_BASE_FONT_SIZE)
    fb = ("微軟正黑體", LAYOUT_CANVAS_BASE_FONT_SIZE, "bold")
    x1, x2, xl2 = x + LAYOUT_CANVAS_X_VALUE_1, x + LAYOUT_CANVAS_X_VALUE_2, x + LAYOUT_CANVAS_X_LABEL_2

    d["name"] = cv.create_text(x, y, text="人物", font=fb, anchor="w", fill=DEFAULT_FG_COLOR); y += step
    d["nickname"] = cv.create_text(x, y, text="稱號", font=fn, anchor="w", fill=DEFAULT_FG_COLOR); y += step
    
    cv.create_text(x, y, text="LV:", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    d["lv"] = cv.create_text(x1, y, text="--", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    d["rebirth"] = cv.create_text(xl2, y, text="--", font=fn, anchor="w", fill=DEFAULT_FG_COLOR); y += step

    d["hp"] = _draw_text_row(cv, x, y, "HP:", x1, "hp", fn); y += step
    d["mp"] = _draw_text_row(cv, x, y, "MP:", x1, "mp", fn); y += step
    
    cv.create_text(x, y, text="攻擊:", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    d["atk"] = cv.create_text(x1, y, text="--", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    cv.create_text(xl2, y, text="防禦:", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    d["def"] = cv.create_text(x2, y, text="--", font=fn, anchor="w", fill=DEFAULT_FG_COLOR); y += step
    
    cv.create_text(x, y, text="敏捷:", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    d["agi"] = cv.create_text(x1, y, text="--", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    cv.create_text(xl2, y, text="魅力:", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    d["charm"] = cv.create_text(x2, y, text="--", font=fn, anchor="w", fill=DEFAULT_FG_COLOR); y += step
    
    # 屬性
    cv.create_text(x, y, text="屬性:", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    for i in range(4):
        cx = x1 + (i * LAYOUT_CANVAS_ELEM_STEP)
        d[f"elem_{i+1}_lbl"] = cv.create_text(cx, y, text="", font=fn, anchor="w")
        d[f"elem_{i+1}_val"] = cv.create_text(cx + LAYOUT_CANVAS_ELEM_VAL_OFFSET, y, text="", font=fn, anchor="w")
    y += (step - LAYOUT_CANVAS_PERSON_Y_ADJUST_1)
    
    cv.create_line(x, y, x2 + 45, y, fill="#DDDDDD")
    y += (step - LAYOUT_CANVAS_PERSON_Y_ADJUST_2)
    
    cv.create_text(x, y, text="體力:", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    d["vit"] = cv.create_text(x1, y, text="--", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    cv.create_text(xl2, y, text="腕力:", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    d["str"] = cv.create_text(x2, y, text="--", font=fn, anchor="w", fill=DEFAULT_FG_COLOR); y += step
    
    cv.create_text(x, y, text="耐力:", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    d["sta"] = cv.create_text(x1, y, text="--", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    cv.create_text(xl2, y, text="速度:", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    d["spd"] = cv.create_text(x2, y, text="--", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    
    return d

def _draw_pet(cv, x, idx):
    d = {}
    y, step = LAYOUT_CANVAS_BASE_Y_START, LAYOUT_CANVAS_BASE_Y_STEP
    fn = ("微軟正黑體", LAYOUT_CANVAS_BASE_FONT_SIZE)
    fb = ("微軟正黑體", LAYOUT_CANVAS_BASE_FONT_SIZE, "bold")
    x1, xl2 = x + LAYOUT_CANVAS_X_VALUE_1, x + LAYOUT_CANVAS_X_LABEL_2

    d["name"] = cv.create_text(x, y, text=f"寵物{num_to_chinese(idx+1)}", font=fb, anchor="w", fill=DEFAULT_FG_COLOR); y += step
    d["nickname"] = cv.create_text(x, y, text="", font=fn, anchor="w", fill=DEFAULT_FG_COLOR); y += step
    
    cv.create_text(x, y, text="LV:", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    d["lv"] = cv.create_text(x1, y, text="--", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    d["rebirth"] = cv.create_text(xl2, y, text="--", font=fn, anchor="w", fill=DEFAULT_FG_COLOR); y += step
    
    d["exp"] = _draw_text_row(cv, x, y, "經驗:", x1, "exp", fn); y += step
    d["lack"] = _draw_text_row(cv, x, y, "還欠:", x1, "lack", fn); y += step
    d["hp"] = _draw_text_row(cv, x, y, "HP:", x1, "hp", fn); y += step
    d["atk"] = _draw_text_row(cv, x, y, "攻擊:", x1, "atk", fn); y += step
    d["def"] = _draw_text_row(cv, x, y, "防禦:", x1, "def", fn); y += step
    d["agi"] = _draw_text_row(cv, x, y, "敏捷:", x1, "agi", fn); y += step
    
    cv.create_text(x, y, text="屬性:", font=fn, anchor="w", fill=DEFAULT_FG_COLOR)
    for i in range(4):
        cx = x1 + (i * LAYOUT_CANVAS_ELEM_STEP)
        d[f"elem_{i+1}_lbl"] = cv.create_text(cx, y, text="", font=fn, anchor="w")
        d[f"elem_{i+1}_val"] = cv.create_text(cx + LAYOUT_CANVAS_ELEM_VAL_OFFSET, y, text="", font=fn, anchor="w")
    y += step
    
    d["loyal"] = _draw_text_row(cv, x, y, "忠誠:", x1, "loyal", fn)
    return d

def create_item_client_panel(parent, account_name):
    """建立道具面板 (左右欄)"""
    return _create_dual_column_canvas(
        parent, account_name,
        LAYOUT_ITEM_CANVAS_HEIGHT, LAYOUT_ITEM_FONT_SIZE, LAYOUT_ITEM_ROW_HEIGHT,
        LAYOUT_ITEM_COL_1_X, LAYOUT_ITEM_COL_2_X, LAYOUT_ITEM_SEPARATOR_X,
        _populate_item_canvas
    )

def create_battle_client_panel(parent, account_name):
    """建立戰鬥面板 (左右欄)"""
    return _create_dual_column_canvas(
        parent, account_name,
        LAYOUT_BATTLE_CANVAS_HEIGHT, LAYOUT_BATTLE_FONT_SIZE, LAYOUT_BATTLE_ROW_HEIGHT,
        LAYOUT_BATTLE_COL_1_X, LAYOUT_BATTLE_COL_2_X, LAYOUT_BATTLE_SEPARATOR_X,
        _populate_battle_canvas
    )

def _create_dual_column_canvas(parent, title, h, fs, row_h, x1, x2, sep_x, populate_func):
    """通用雙欄 Canvas 建立器"""
    lf = ttk.Labelframe(parent, text=title, padding=2)
    lf.pack(fill="x", padx=5, pady=LAYOUT_ITEM_ACCOUNT_PAD_Y, anchor="n")
    
    try: bg = ttk.Style().lookup("TFrame", "background") or "#f0f0f0"
    except: bg = "#f0f0f0"
    
    cv = tk.Canvas(lf, height=h, width=x2*2, bg=bg, highlightthickness=0, bd=0)
    cv.pack(fill="both", expand=True)
    cv.create_line(sep_x, 5, sep_x, h - 5, fill="#AAAAAA")
    
    ids = populate_func(cv, fs, row_h, x1, x2, sep_x)
    return {"frame": lf, "canvas": cv, "ids": ids}

def _populate_item_canvas(cv, fs, row_h, x1, x2, sep_x):
    from constants import EQUIP_DISPLAY_ORDER, EQUIP_MAPPING
    ids = {}
    fn, fb = ("微軟正黑體", fs), ("微軟正黑體", fs, "bold")
    y = 5
    
    # 左欄：裝備
    cv.create_text(x1, y, text="【裝備】", anchor="nw", font=fb, fill="#0000AA")
    y += row_h + LAYOUT_ITEM_HEADER_Y_OFFSET
    for idx in EQUIP_DISPLAY_ORDER:
        prefix = EQUIP_MAPPING.get(idx, "??")
        ids[idx] = cv.create_text(x1, y, text=f"{prefix}: --", anchor="nw", font=fn)
        y += row_h
    
    # 分隔線與道具 1-2
    line_y = y + (row_h + LAYOUT_ITEM_HEADER_Y_OFFSET) // 2
    cv.create_line(5, line_y, sep_x - 5, line_y, fill="#AAAAAA")
    y += row_h + LAYOUT_ITEM_HEADER_Y_OFFSET
    
    cv.create_text(x1, y, text="【道具 1-2】", anchor="nw", font=fb, fill="#0000AA")
    y += row_h + LAYOUT_ITEM_HEADER_Y_OFFSET
    for idx in range(2):
        ids[idx] = cv.create_text(x1, y, text=f"{idx+1:02d}: --", anchor="nw", font=fn)
        y += row_h
        
    # 右欄：道具 3-15
    y = 5
    cv.create_text(x2, y, text="【道具 3-15】", anchor="nw", font=fb, fill="#0000AA")
    y += row_h + LAYOUT_ITEM_HEADER_Y_OFFSET
    for idx in range(2, 15):
        ids[idx] = cv.create_text(x2, y, text=f"{idx+1:02d}: --", anchor="nw", font=fn)
        y += row_h
    return ids

def _populate_battle_canvas(cv, fs, row_h, x1, x2, sep_x):
    from constants import BATTLE_LEFT_ORDER, BATTLE_RIGHT_ORDER
    ids = {}
    fn, fb = ("微軟正黑體", fs), ("微軟正黑體", fs, "bold")
    
    # 左隊
    y = 5
    cv.create_text(x1, y, text="【左方隊伍】", anchor="nw", font=fb, fill="#A00000")
    y += row_h + LAYOUT_BATTLE_HEADER_Y_OFFSET
    for idx in BATTLE_LEFT_ORDER:
        ids[idx] = cv.create_text(x1, y, text=f"{idx}: --", anchor="nw", font=fn)
        y += row_h
        
    # 右隊
    y = 5
    cv.create_text(x2, y, text="【右方隊伍】", anchor="nw", font=fb, fill="#0000A0")
    y += row_h + LAYOUT_BATTLE_HEADER_Y_OFFSET
    for idx in BATTLE_RIGHT_ORDER:
        ids[idx] = cv.create_text(x2, y, text=f"{idx}: --", anchor="nw", font=fn)
        y += row_h
    return ids

# --- app_ui.py (原有內容保持不變，請在最下方追加) ---

def update_char_canvas(cv, items, d):
    """更新人物資料 Canvas"""
    from constants import REBIRTH_COLOR_MAP
    if not d:
        cv.itemconfigure(items["name"], text="人物")
        cv.itemconfigure(items["hp"], text="--/--")
        return

    cv.itemconfigure(items["name"], text=d.get("name", "人物"))
    cv.itemconfigure(items["nickname"], text=d.get("nickname", "稱號"))
    cv.itemconfigure(items["lv"], text=d.get("lv", "--"))
    cv.itemconfigure(items["hp"], text=d.get("hp", "--/--"))
    cv.itemconfigure(items["mp"], text=d.get("mp", "--/--"))
    
    for k in ["atk", "def", "agi", "vit", "str", "sta", "spd"]:
        cv.itemconfigure(items[k], text=d.get(k, "--"))
        
    cv.itemconfigure(items["charm"], text=d.get("charm", 0), 
                     fill="red" if d.get("charm", 0) <= 60 else "black")
    
    rebirth_txt = d.get("rebirth", "未知")
    cv.itemconfigure(items["rebirth"], text=rebirth_txt, 
                     fill=REBIRTH_COLOR_MAP.get(rebirth_txt, "black"))
    
    # 屬性
    raw = d.get("element_raw", (0,0,0,0))
    elems = []
    if raw[0]>0: elems.append(("地", raw[0]//10, "green"))
    if raw[1]>0: elems.append(("水", raw[1]//10, "blue"))
    if raw[2]>0: elems.append(("火", raw[2]//10, "red"))
    if raw[3]>0: elems.append(("風", raw[3]//10, "#E5C100"))
    
    for i in range(4):
        l, v = items[f"elem_{i+1}_lbl"], items[f"elem_{i+1}_val"]
        if i < len(elems):
            cv.itemconfigure(l, text=elems[i][0], fill=elems[i][2])
            cv.itemconfigure(v, text=elems[i][1], fill=elems[i][2])
        else:
            cv.itemconfigure(l, text=""); cv.itemconfigure(v, text="")

def update_pet_canvas(cv, items, d, idx):
    """更新寵物資料 Canvas"""
    from constants import REBIRTH_COLOR_MAP
    default = f"寵物{num_to_chinese(idx+1)}"
    
    if not d:
        cv.itemconfigure(items["name"], text=default, fill="black")
        cv.itemconfigure(items["hp"], text="--/--")
        return
        
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
    
    rebirth_txt = d.get("rebirth", "未知")
    cv.itemconfigure(items["rebirth"], text=rebirth_txt, 
                     fill=REBIRTH_COLOR_MAP.get(rebirth_txt, "black"))
    
    loyal = d.get("loyal", 100)
    cv.itemconfigure(items["loyal"], text=loyal, fill="red" if loyal <= 20 else "black")
    
    # 屬性
    raw = d.get("element_raw", (0,0,0,0))
    elems = []
    if raw[0]>0: elems.append(("地", raw[0]//10, "green"))
    if raw[1]>0: elems.append(("水", raw[1]//10, "blue"))
    if raw[2]>0: elems.append(("火", raw[2]//10, "red"))
    if raw[3]>0: elems.append(("風", raw[3]//10, "#E5C100"))
    
    for i in range(4):
        l, v = items[f"elem_{i+1}_lbl"], items[f"elem_{i+1}_val"]
        if i < len(elems):
            cv.itemconfigure(l, text=elems[i][0], fill=elems[i][2])
            cv.itemconfigure(v, text=elems[i][1], fill=elems[i][2])
        else:
            cv.itemconfigure(l, text=""); cv.itemconfigure(v, text="")