# app_ui.py
# 負責 UI 佈局定義、DPI 參數與 Canvas 繪圖邏輯

import tkinter as tk
from tkinter import ttk

from ui_components import ScrollableFrame
from constants import MAX_CLIENTS, DEFAULT_FG_COLOR, ELEMENT_COLOR_MAP
from utils import num_to_chinese

# --- UI 佈局參數設定 (DPI 適配) ---
# main.py 會根據偵測到的 DPI 選擇下列其中一組參數，並乘以縮放比例

# 適用於 100% DPI (4K 螢幕)
PARAMS_4K_100 = {
    "APP_BASE_WIDTH": 950, "APP_BASE_HEIGHT": 250,
    "LEFT_PANEL_WIDTH": 150, "NON_CONTENT_HEIGHT": 150,
    "CANVAS_ROW_PADDING": 15,
    "LEFT_CHECKBOX_PADY": 1, "SETTINGS_CHECKBOX_PADY": 1,
    "CANVAS_FONT_SIZE": 8.5,
    "CANVAS_Y_START": 8, "CANVAS_Y_STEP": 15,
    "CANVAS_COL_WIDTH": 110, "CANVAS_COL_PADDING": 8, "CANVAS_START_X": 5,
    "CANVAS_X_VAL_1": 25, "CANVAS_X_LBL_2": 60, "CANVAS_X_VAL_2": 85,
    "CANVAS_ELEM_VAL_OFFSET": 13, "CANVAS_ELEM_STEP": 30,
    "CANVAS_PERSON_Y_ADJ_1": 0, "CANVAS_PERSON_Y_ADJ_2": 0,
    # --- 7. 道具列表 Canvas 設定 (v4.9.4 背景分隔線版) ---
    "ITEM_CANVAS_HEIGHT": 230,
    "ITEM_FONT_SIZE": 9,
    "ITEM_ROW_HEIGHT": 14,
    # (修改) 將左欄起點設為 10
    "ITEM_COL_1_X": 10,
    # (修改) 將右欄起點設為 360 (讓左欄有約 340px 的空間)
    "ITEM_COL_2_X": 410,
    # (新增) 分隔線的 X 座標 (在兩欄中間)
    "ITEM_SEPARATOR_X": 400, 
    "ITEM_HEADER_Y_OFFSET": 5,
    "ITEM_ACCOUNT_PAD_Y": 5,

    # --- 8. 戰鬥狀態 Canvas 設定 (v4.10) ---
    "BATTLE_CANVAS_HEIGHT": 200,    # 戰鬥畫布高度 (10行 + 標題)
    "BATTLE_FONT_SIZE": 9,
    "BATTLE_ROW_HEIGHT": 16,        # 行高
    "BATTLE_COL_1_X": 10,           # 左欄 X
    "BATTLE_COL_2_X": 180,          # 右欄 X
    "BATTLE_SEPARATOR_X": 170,      # 分隔線 X
    "BATTLE_HEADER_Y_OFFSET": 5,
    "BATTLE_ACCOUNT_PAD_Y": 5,
}

# 適用於 125% DPI (4K 螢幕)
PARAMS_4K_125 = {
    "APP_BASE_WIDTH": 1380, "APP_BASE_HEIGHT": 350,
    "LEFT_PANEL_WIDTH": 150, "NON_CONTENT_HEIGHT": 150,
    "CANVAS_ROW_PADDING": 20,
    "LEFT_CHECKBOX_PADY": 1, "SETTINGS_CHECKBOX_PADY": 1,
    "CANVAS_FONT_SIZE": 9,
    "CANVAS_Y_START": 8, "CANVAS_Y_STEP": 18,
    "CANVAS_COL_WIDTH": 180, "CANVAS_COL_PADDING": 10, "CANVAS_START_X": 5,
    "CANVAS_X_VAL_1": 40, "CANVAS_X_LBL_2": 100, "CANVAS_X_VAL_2": 140,
    "CANVAS_ELEM_VAL_OFFSET": 20, "CANVAS_ELEM_STEP": 45,
    "CANVAS_PERSON_Y_ADJ_1": 0, "CANVAS_PERSON_Y_ADJ_2": 0,
    # --- 7. 道具列表 Canvas 設定 (v4.9.4 背景分隔線版) ---
    "ITEM_CANVAS_HEIGHT": 230,
    "ITEM_FONT_SIZE": 9,
    "ITEM_ROW_HEIGHT": 14,
    # (修改) 將左欄起點設為 10
    "ITEM_COL_1_X": 10,
    # (修改) 將右欄起點設為 360 (讓左欄有約 340px 的空間)
    "ITEM_COL_2_X": 360,
    # (新增) 分隔線的 X 座標 (在兩欄中間)
    "ITEM_SEPARATOR_X": 350, 
    "ITEM_HEADER_Y_OFFSET": 5,
    "ITEM_ACCOUNT_PAD_Y": 5,

    # ...
    "BATTLE_CANVAS_HEIGHT": 250,
    "BATTLE_FONT_SIZE": 10,
    "BATTLE_ROW_HEIGHT": 20,
    "BATTLE_COL_1_X": 12,
    "BATTLE_COL_2_X": 225,
    "BATTLE_SEPARATOR_X": 212,
    "BATTLE_HEADER_Y_OFFSET": 6,
    "BATTLE_ACCOUNT_PAD_Y": 6,

}

# 適用於 150% DPI (4K 螢幕)
PARAMS_4K_150 = {
    "APP_BASE_WIDTH": 1600, "APP_BASE_HEIGHT": 400,
    "LEFT_PANEL_WIDTH": 150, "NON_CONTENT_HEIGHT": 150,
    "CANVAS_ROW_PADDING": 30,
    "LEFT_CHECKBOX_PADY": 1, "SETTINGS_CHECKBOX_PADY": 1,
    "CANVAS_FONT_SIZE": 10,
    "CANVAS_Y_START": 10, "CANVAS_Y_STEP": 20,
    "CANVAS_COL_WIDTH": 210, "CANVAS_COL_PADDING": 10, "CANVAS_START_X": 5,
    "CANVAS_X_VAL_1": 50, "CANVAS_X_LBL_2": 110, "CANVAS_X_VAL_2": 160,
    "CANVAS_ELEM_VAL_OFFSET": 20, "CANVAS_ELEM_STEP": 45,
    "CANVAS_PERSON_Y_ADJ_1": 0, "CANVAS_PERSON_Y_ADJ_2": 0,
    # --- 7. 道具列表 Canvas 設定 (v4.9.4 背景分隔線版) ---
    "ITEM_CANVAS_HEIGHT": 300,
    "ITEM_FONT_SIZE": 10,
    "ITEM_ROW_HEIGHT": 20,
    "ITEM_COL_1_X": 5,
    # 1.5倍
    "ITEM_COL_2_X": 660,
    "ITEM_SEPARATOR_X": 650,
    "ITEM_HEADER_Y_OFFSET": 0,
    "ITEM_ACCOUNT_PAD_Y": 0,

    # ...
    "BATTLE_CANVAS_HEIGHT": 300,
    "BATTLE_FONT_SIZE": 10,
    "BATTLE_ROW_HEIGHT": 20,
    "BATTLE_COL_1_X": 5,
    "BATTLE_COL_2_X": 660,
    "BATTLE_SEPARATOR_X": 650,
    "BATTLE_HEADER_Y_OFFSET": 0,
    "BATTLE_ACCOUNT_PAD_Y": 0,
}

# --- 最終佈局參數 (由 main.py 計算並覆寫) ---
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
# 2. 全域變數宣告 (供 main.py 寫入)
LAYOUT_ITEM_CANVAS_HEIGHT = 230
LAYOUT_ITEM_FONT_SIZE = 9
LAYOUT_ITEM_ROW_HEIGHT = 14
LAYOUT_ITEM_COL_1_X = 10
LAYOUT_ITEM_COL_2_X = 360
LAYOUT_ITEM_SEPARATOR_X = 350
LAYOUT_ITEM_HEADER_Y_OFFSET = 5
LAYOUT_ITEM_ACCOUNT_PAD_Y = 5

# 2. 全域變數 (新增 BATTLE_...)
LAYOUT_BATTLE_CANVAS_HEIGHT = 200
LAYOUT_BATTLE_FONT_SIZE = 9
LAYOUT_BATTLE_ROW_HEIGHT = 16
LAYOUT_BATTLE_COL_1_X = 10
LAYOUT_BATTLE_COL_2_X = 180
LAYOUT_BATTLE_SEPARATOR_X = 170
LAYOUT_BATTLE_HEADER_Y_OFFSET = 5
LAYOUT_BATTLE_ACCOUNT_PAD_Y = 5

# --- 靜態 UI 建立函式 ---
def create_main_widgets(app):
    """建立主視窗介面 (左右佈局)"""
    main_frame = ttk.Frame(app, padding=10)
    main_frame.pack(fill="both", expand=True)

    # 左側面板
    left_frame = ttk.Frame(main_frame, width=app.scaled_left_panel_width, padding=(5,5,5,5), relief="groove")
    left_frame.pack(side="left", fill="y", padx=(0, 10))
    left_frame.pack_propagate(False)

    bind_button = ttk.Button(left_frame, text="綁定石器", command=app.on_bind_click)
    bind_button.pack(fill="x", pady=(5, 10), ipady=3)

    parent_bg = app.cget('background')
    for i in range(MAX_CLIENTS):
        checkbox = tk.Checkbutton(
            left_frame, text=f"窗口 {i+1}: 未綁定", 
            variable=app.client_selection_vars[i],
            onvalue=1, offvalue=0, command=app.on_selection_change, 
            state="disabled", disabledforeground="grey", anchor="w",                
            bg=parent_bg, selectcolor=parent_bg, padx=0                     
        )
        checkbox.pack(anchor="w", pady=LAYOUT_LEFT_CHECKBOX_PADY) 
        checkbox.bind("<Button-3>", lambda e, idx=i: app.on_client_right_click_single(e, idx))
        checkbox.bind("<Double-Button-3>", lambda e, idx=i: app.on_client_right_click_double(e, idx))
        app.client_checkboxes.append(checkbox)

    # 右側 Notebook
    right_frame = ttk.Frame(main_frame, relief="sunken")
    right_frame.pack(side="right", fill="both", expand=True)

    app.notebook = ttk.Notebook(right_frame)
    app.notebook.pack(fill="both", expand=True)
    
    app.notebook.bind("<<NotebookTabChanged>>", app.on_tab_changed)

    tab_names = ["遊戲設置", "人寵資料", "道具列表", "戰鬥狀態", "聊天窗口"]
    for name in tab_names:
        tab_frame = ttk.Frame(app.notebook, padding=5) 
        app.notebook.add(tab_frame, text=name)
        app.tabs[name] = tab_frame
        
    create_settings_tab(app.tabs["遊戲設置"], app)
    create_character_tab(app.tabs["人寵資料"], app)
    create_items_tab(app.tabs["道具列表"], app)
    create_battle_tab(app.tabs["戰鬥狀態"], app)
    
    # 尚未開放的功能 (只剩聊天窗口)
    app.notebook.tab(4, state="disabled")

# 4. 新增 create_battle_tab 函式
def create_battle_tab(tab_frame, app):
    """建立「戰鬥狀態」頁籤 UI"""
    # 建立可捲動區域
    app.tab_frame_battle = ScrollableFrame(tab_frame, orient="vertical")
    app.tab_frame_battle.pack(fill="both", expand=True)
    
    # 初始化存放 UI 參照的字典
    app.client_battle_ui = {}


# 5. 新增 create_battle_client_panel 函式 (戰鬥畫布繪製)
def create_battle_client_panel(parent, account_name):
    """
    (戰鬥版) 建立單一客戶端的戰鬥面板
    結構：左方隊伍 (10行) | 右方隊伍 (10行)
    """
    # 外框 (帳號)
    lf_account = ttk.Labelframe(parent, text=account_name, padding=2)
    lf_account.pack(fill="x", padx=5, pady=LAYOUT_BATTLE_ACCOUNT_PAD_Y, anchor="n")
    
    # 安全取得背景色
    try:
        style = ttk.Style()
        sys_bg = style.lookup("TFrame", "background")
        if not sys_bg: sys_bg = "#f0f0f0"
    except: sys_bg = "#f0f0f0"

    # 計算請求寬度
    req_width = LAYOUT_BATTLE_COL_2_X * 2
    
    # 建立畫布
    canvas = tk.Canvas(
        lf_account, 
        height=LAYOUT_BATTLE_CANVAS_HEIGHT,
        width=req_width,      
        bg=sys_bg,            
        highlightthickness=0, 
        bd=0                  
    )
    canvas.pack(fill="both", expand=True)

    # 繪製垂直分隔線
    sep_x = LAYOUT_BATTLE_SEPARATOR_X
    canvas.create_line(sep_x, 5, sep_x, LAYOUT_BATTLE_CANVAS_HEIGHT - 5, fill="#AAAAAA")

    font_normal = ("微軟正黑體", LAYOUT_BATTLE_FONT_SIZE)
    font_bold   = ("微軟正黑體", LAYOUT_BATTLE_FONT_SIZE, "bold")
    
    text_ids = {} # index -> canvas_id
    row_h = LAYOUT_BATTLE_ROW_HEIGHT
    
    from constants import BATTLE_LEFT_ORDER, BATTLE_RIGHT_ORDER

    # === 左方隊伍 ===
    x_left = LAYOUT_BATTLE_COL_1_X
    current_y = 5
    
    # 標題
    canvas.create_text(x_left, current_y, text="【左方隊伍】", anchor="nw", font=font_bold, fill="#A00000") # 深紅
    current_y += row_h + LAYOUT_BATTLE_HEADER_Y_OFFSET
    
    # 列表 (10行)
    for idx in BATTLE_LEFT_ORDER:
        # 預設顯示： "編號: --"
        tid = canvas.create_text(x_left, current_y, text=f"{idx}: --", anchor="nw", font=font_normal)
        text_ids[idx] = tid
        current_y += row_h

    # === 右方隊伍 ===
    x_right = LAYOUT_BATTLE_COL_2_X
    current_y = 5 # 重置 Y
    
    # 標題
    canvas.create_text(x_right, current_y, text="【右方隊伍】", anchor="nw", font=font_bold, fill="#0000A0") # 深藍
    current_y += row_h + LAYOUT_BATTLE_HEADER_Y_OFFSET
    
    # 列表 (10行)
    for idx in BATTLE_RIGHT_ORDER:
        tid = canvas.create_text(x_right, current_y, text=f"{idx}: --", anchor="nw", font=font_normal)
        text_ids[idx] = tid
        current_y += row_h

    return {
        "frame": lf_account,
        "canvas": canvas,
        "ids": text_ids
    }

def create_settings_tab(tab_frame, app):
    """(修改) 建立「遊戲設置」頁籤，新增自動高度開關"""
    global_settings_frame = ttk.Frame(tab_frame)
    global_settings_frame.pack(fill="x", pady=(0, 5))

    # 1. 刷新頻率
    ttk.Label(global_settings_frame, text="刷新頻率:").pack(side="left", padx=(5, 5))
    refresh_options = ['0.5s', '1s', '3s', '5s', '10s', '60s', '不刷新']
    app.refresh_rate_combo = ttk.Combobox(
        global_settings_frame, textvariable=app.refresh_rate_var,
        values=refresh_options, state="readonly", width=8
    )
    app.refresh_rate_combo.pack(side="left", padx=(0, 10))
    app.refresh_rate_combo.bind("<<ComboboxSelected>>", app.on_refresh_rate_change)

    # 2. 視窗縮放
    ttk.Label(global_settings_frame, text="視窗縮放:").pack(side="left", padx=(5, 5))
    zoom_options = ['75%', '90%', '100%', '110%', '125%', '150%']
    app.zoom_combo = ttk.Combobox(
        global_settings_frame, textvariable=app.zoom_var,
        values=zoom_options, state="readonly", width=8
    )
    app.zoom_combo.pack(side="left", padx=(0, 10))
    app.zoom_combo.bind("<<ComboboxSelected>>", app.on_zoom_change)

    # 3. (新增) 自動高度開關
    cb_auto_height = ttk.Checkbutton(
        global_settings_frame, 
        text="自動拉伸高度", 
        variable=app.auto_height_var,
        # 當使用者重新勾選時，立即執行一次高度調整
        command=lambda: app.adjust_window_height() if app.auto_height_var.get() else None
    )
    cb_auto_height.pack(side="left", padx=(5, 0))

    ttk.Separator(tab_frame, orient="horizontal").pack(fill="x", pady=(5, 10))
    
    # ... (保留原有 ScrollableFrame 與 Client Loop) ...
    app.tab_frame_settings = ScrollableFrame(tab_frame, orient="horizontal") 
    app.tab_frame_settings.pack(fill="both", expand=True) 

    app.setting_widgets = [] 
    for i in range(MAX_CLIENTS):
        frame = ttk.Labelframe(app.tab_frame_settings.inner_frame, text=f"窗口 {i+1}", padding=5)
        (vars_dict, widgets_dict) = _create_settings_ui_frame(
            frame, client_index=i, app_instance=app 
        )
        app.setting_widgets.append({"frame": frame, "vars": vars_dict, "widgets": widgets_dict})

def _create_settings_ui_frame(parent, client_index, app_instance):
    """輔助函式, 建立一組遊戲設置 UI"""
    setting_vars = {
        "game_speed": tk.IntVar(), "fast_walk": tk.IntVar(),
        "no_clip": tk.IntVar(), "hide_sa": tk.IntVar()
    }
    cmd_speed = lambda idx=client_index: app_instance.on_toggle_speed(idx)
    cmd_walk  = lambda idx=client_index: app_instance.on_toggle_walk(idx)
    cmd_noclip= lambda idx=client_index: app_instance.on_toggle_noclip(idx)
    cmd_hide  = lambda idx=client_index: app_instance.on_toggle_hide(idx)
    
    cb_speed = ttk.Checkbutton(parent, text="遊戲加速", variable=setting_vars["game_speed"], command=cmd_speed)
    cb_walk = ttk.Checkbutton(parent, text="快速行走", variable=setting_vars["fast_walk"], command=cmd_walk)
    cb_noclip = ttk.Checkbutton(parent, text="穿牆行走", variable=setting_vars["no_clip"], command=cmd_noclip)
    cb_hide = ttk.Checkbutton(parent, text="隱藏石器", variable=setting_vars["hide_sa"], command=cmd_hide)
                              
    cb_speed.pack(anchor="w", pady=LAYOUT_SETTINGS_CHECKBOX_PADY)
    cb_walk.pack(anchor="w", pady=LAYOUT_SETTINGS_CHECKBOX_PADY)
    cb_noclip.pack(anchor="w", pady=LAYOUT_SETTINGS_CHECKBOX_PADY)
    cb_hide.pack(anchor="w", pady=LAYOUT_SETTINGS_CHECKBOX_PADY)
    
    widgets = {"speed": cb_speed, "walk": cb_walk, "noclip": cb_noclip, "hide": cb_hide}
    return (setting_vars, widgets)

def create_character_tab(tab_frame, app):
    """建立「人寵資料」頁籤 (Canvas UI 將動態建立)"""
    app.tab_frame_char = ScrollableFrame(tab_frame, orient="vertical") 
    app.tab_frame_char.pack(fill="both", expand=True) 
    app.tab_frame_char.inner_frame.columnconfigure(0, weight=1)

def create_client_info_canvas(parent_labelframe, app_instance):
    """建立單個客戶端的資訊畫布"""
    col_width = LAYOUT_CANVAS_BASE_COL_WIDTH
    x_padding = LAYOUT_CANVAS_BASE_COL_PADDING
    start_x = LAYOUT_CANVAS_BASE_START_X
    canvas_height = BASE_CANVAS_ROW_HEIGHT
    
    # 總寬度 = 6 * 欄寬 + 5 * 間距 + 2 * 邊距
    canvas_width = (col_width * 6) + (x_padding * 5) + (start_x * 2)
    
    try:
        bg_color = parent_labelframe.cget("background")
    except:
        bg_color = app_instance.cget("background") 

    canvas = tk.Canvas(
        parent_labelframe, 
        width=canvas_width, 
        height=canvas_height, 
        bg=bg_color,
        highlightthickness=0 
    )
    canvas.pack(anchor="w", padx=5, pady=5)
    
    all_vars_list = []
    
    # --- 1. 繪製人物 (第 0 欄) ---
    x_offset = start_x
    person_vars = _draw_person_canvas_items(canvas, x_offset)
    all_vars_list.append(person_vars)

    # --- 2. 繪製 5 隻寵物 (第 1-5 欄) ---
    for i in range(5):
        x_offset = start_x + (col_width + x_padding) * (i + 1)
        
        # 分隔線
        canvas.create_line(
            x_offset - (x_padding // 2) - 1, int(10 * RESOLUTION_RATIO), 
            x_offset - (x_padding // 2) - 1, canvas_height - int(10 * RESOLUTION_RATIO), 
            fill="#CCCCCC"
        )
        
        pet_vars = _draw_pet_canvas_items(canvas, x_offset, i)
        all_vars_list.append(pet_vars)
        
    return canvas, all_vars_list

def _draw_person_canvas_items(canvas, x):
    """繪製人物欄位元件"""
    vars_dict = {} 
    y = LAYOUT_CANVAS_BASE_Y_START
    y_step = LAYOUT_CANVAS_BASE_Y_STEP
    
    scaled_font_size = LAYOUT_CANVAS_BASE_FONT_SIZE
    font_bold = ("微軟正黑體", scaled_font_size, "bold")
    font_normal = ("微軟正黑體", scaled_font_size)
    
    x_label_1 = x
    x_value_1 = x + LAYOUT_CANVAS_X_VALUE_1
    x_label_2 = x + LAYOUT_CANVAS_X_LABEL_2
    x_value_2 = x + LAYOUT_CANVAS_X_VALUE_2
    
    vars_dict["name"] = canvas.create_text(x_label_1, y, text="人物", font=font_bold, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    
    vars_dict["nickname"] = canvas.create_text(x_label_1, y, text="稱號", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="LV:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["lv"] = canvas.create_text(x_value_1, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["rebirth"] = canvas.create_text(x_label_2, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="HP:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["hp"] = canvas.create_text(x_value_1, y, text="--/--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    canvas.create_text(x_label_1, y, text="MP:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["mp"] = canvas.create_text(x_value_1, y, text="--/--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="攻擊:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["atk"] = canvas.create_text(x_value_1, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    canvas.create_text(x_label_2, y, text="防禦:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["def"] = canvas.create_text(x_value_2, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    
    canvas.create_text(x_label_1, y, text="敏捷:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["agi"] = canvas.create_text(x_value_1, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    canvas.create_text(x_label_2, y, text="魅力:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["charm"] = canvas.create_text(x_value_2, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    
    canvas.create_text(x_label_1, y, text="屬性:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    
    elem_x = x_value_1
    val_offset = LAYOUT_CANVAS_ELEM_VAL_OFFSET
    elem_step = LAYOUT_CANVAS_ELEM_STEP
    
    for i in range(4):
        lbl_key = f"elem_{i+1}_lbl"
        val_key = f"elem_{i+1}_val"
        current_x = elem_x + (i * elem_step)
        vars_dict[lbl_key] = canvas.create_text(current_x, y, text="", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
        vars_dict[val_key] = canvas.create_text(current_x + val_offset, y, text="", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    
    y += (y_step - LAYOUT_CANVAS_PERSON_Y_ADJUST_1)

    canvas.create_line(x_label_1, y, x_value_2 + int(45 * RESOLUTION_RATIO), y, fill="#DDDDDD") 
    
    y += (y_step - LAYOUT_CANVAS_PERSON_Y_ADJUST_2)

    canvas.create_text(x_label_1, y, text="體力:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["vit"] = canvas.create_text(x_value_1, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    canvas.create_text(x_label_2, y, text="腕力:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["str"] = canvas.create_text(x_value_2, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    
    canvas.create_text(x_label_1, y, text="耐力:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["sta"] = canvas.create_text(x_value_1, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    canvas.create_text(x_label_2, y, text="速度:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["spd"] = canvas.create_text(x_value_2, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    
    return vars_dict
    
def _draw_pet_canvas_items(canvas, x, pet_index):
    """繪製寵物欄位元件"""
    vars_dict = {} 
    y = LAYOUT_CANVAS_BASE_Y_START
    y_step = LAYOUT_CANVAS_BASE_Y_STEP
    
    scaled_font_size = LAYOUT_CANVAS_BASE_FONT_SIZE
    font_bold = ("微軟正黑體", scaled_font_size, "bold")
    font_normal = ("微軟正黑體", scaled_font_size)
    
    x_label_1 = x
    x_value_1 = x + LAYOUT_CANVAS_X_VALUE_1
    x_label_2 = x + LAYOUT_CANVAS_X_LABEL_2
    
    vars_dict["name"] = canvas.create_text(x_label_1, y, text=f"寵物{num_to_chinese(pet_index + 1)}", font=font_bold, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    
    vars_dict["nickname"] = canvas.create_text(x_label_1, y, text="", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="LV:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["lv"] = canvas.create_text(x_value_1, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["rebirth"] = canvas.create_text(x_label_2, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="經驗:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["exp"] = canvas.create_text(x_value_1, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    canvas.create_text(x_label_1, y, text="還欠:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["lack"] = canvas.create_text(x_value_1, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="HP:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["hp"] = canvas.create_text(x_value_1, y, text="--/--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    
    canvas.create_text(x_label_1, y, text="攻擊:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["atk"] = canvas.create_text(x_value_1, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    canvas.create_text(x_label_1, y, text="防禦:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["def"] = canvas.create_text(x_value_1, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    canvas.create_text(x_label_1, y, text="敏捷:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["agi"] = canvas.create_text(x_value_1, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="屬性:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    
    elem_x = x_value_1
    val_offset = LAYOUT_CANVAS_ELEM_VAL_OFFSET
    elem_step = LAYOUT_CANVAS_ELEM_STEP
    
    for i in range(4):
        lbl_key = f"elem_{i+1}_lbl"
        val_key = f"elem_{i+1}_val"
        current_x = elem_x + (i * elem_step)
        
        vars_dict[lbl_key] = canvas.create_text(current_x, y, text="", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
        vars_dict[val_key] = canvas.create_text(current_x + val_offset, y, text="", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR) 

    y += y_step

    canvas.create_text(x_label_1, y, text="忠誠:", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["loyal"] = canvas.create_text(x_value_1, y, text="--", font=font_normal, anchor="w", fill=DEFAULT_FG_COLOR)
    
    return vars_dict

def create_items_tab(tab_frame, app):
    """(修改) 建立道具列表 UI (帳號分組 -> 裝備/道具區塊)"""
    
    # 1. 建立可捲動區域 (因為展開後會很長)
    app.tab_frame_items = ScrollableFrame(tab_frame, orient="vertical")
    app.tab_frame_items.pack(fill="both", expand=True)
    
    # 初始化存放 UI 參照的字典
    # 結構: app.client_item_ui[client_index] = { "frame": Frame, "labels": { -9: Label, 0: Label... } }
    app.client_item_ui = {}

def create_item_client_panel(parent, account_name):
    """
    (修正版 v4.9.9) 建立道具面板
    修正：調整橫向分隔線位置，使其精確位於「裝備」列表與「道具1-2」標題的視覺中間
    """
    # 外框 (帳號)
    lf_account = ttk.Labelframe(parent, text=account_name, padding=2)
    lf_account.pack(fill="x", padx=5, pady=LAYOUT_ITEM_ACCOUNT_PAD_Y, anchor="n")
    
    # --- 安全取得背景色 ---
    try:
        style = ttk.Style()
        sys_bg = style.lookup("TFrame", "background")
        if not sys_bg:
            sys_bg = "#f0f0f0"
    except:
        sys_bg = "#f0f0f0"

    # 1. 計算請求寬度
    req_width = LAYOUT_ITEM_COL_2_X * 2
    
    # 2. 建立畫布
    canvas = tk.Canvas(
        lf_account, 
        height=LAYOUT_ITEM_CANVAS_HEIGHT,
        width=req_width,      
        bg=sys_bg,            
        highlightthickness=0, 
        bd=0                  
    )
    canvas.pack(fill="both", expand=True)

    # 3. 繪製垂直分隔線
    sep_x = LAYOUT_ITEM_SEPARATOR_X
    canvas.create_line(sep_x, 5, sep_x, LAYOUT_ITEM_CANVAS_HEIGHT - 5, fill="#AAAAAA")

    font_normal = ("微軟正黑體", LAYOUT_ITEM_FONT_SIZE)
    font_bold   = ("微軟正黑體", LAYOUT_ITEM_FONT_SIZE, "bold")
    
    text_ids = {}
    
    current_y_left = 5
    current_y_right = 5
    row_h = LAYOUT_ITEM_ROW_HEIGHT
    
    # === 左欄 (裝備 + 道具1-2) ===
    x_left = LAYOUT_ITEM_COL_1_X
    
    # 標題: 裝備
    canvas.create_text(x_left, current_y_left, text="【裝備】", anchor="nw", font=font_bold, fill="#0000AA")
    current_y_left += row_h + LAYOUT_ITEM_HEADER_Y_OFFSET
    
    # 內容: 裝備
    from constants import EQUIP_DISPLAY_ORDER, EQUIP_MAPPING
    for idx in EQUIP_DISPLAY_ORDER:
        prefix = EQUIP_MAPPING.get(idx, "未知")
        tid = canvas.create_text(x_left, current_y_left, text=f"{prefix}: --", anchor="nw", font=font_normal)
        text_ids[idx] = tid
        current_y_left += row_h
        
    # (修正) 繪製橫向分隔線 (裝備 與 道具1-2 之間)
    # 計算中間位置：當前 Y + (空行高度 + 標題偏移) / 2
    gap_height = row_h + LAYOUT_ITEM_HEADER_Y_OFFSET
    line_y = current_y_left + (gap_height // 2)
    
    canvas.create_line(5, line_y, sep_x - 5, line_y, fill="#AAAAAA")

    # 增加空行 (對齊右側排版)
    current_y_left += row_h 

    # 間距 + 標題: 道具 1-2
    current_y_left += LAYOUT_ITEM_HEADER_Y_OFFSET
    canvas.create_text(x_left, current_y_left, text="【道具 1-2】", anchor="nw", font=font_bold, fill="#0000AA")
    current_y_left += row_h + LAYOUT_ITEM_HEADER_Y_OFFSET
    
    # 內容: 道具 0~1
    for idx in range(0, 2):
        prefix = f"{idx+1:02d}"
        tid = canvas.create_text(x_left, current_y_left, text=f"{prefix}: --", anchor="nw", font=font_normal)
        text_ids[idx] = tid
        current_y_left += row_h

    # === 右欄 (道具 3-15) ===
    x_right = LAYOUT_ITEM_COL_2_X
    
    # 標題: 道具 3-15
    canvas.create_text(x_right, current_y_right, text="【道具 3-15】", anchor="nw", font=font_bold, fill="#0000AA")
    current_y_right += row_h + LAYOUT_ITEM_HEADER_Y_OFFSET
    
    # 內容: 道具 2~14
    for idx in range(2, 15):
        prefix = f"{idx+1:02d}"
        tid = canvas.create_text(x_right, current_y_right, text=f"{prefix}: --", anchor="nw", font=font_normal)
        text_ids[idx] = tid
        current_y_right += row_h

    return {
        "frame": lf_account,
        "canvas": canvas,
        "ids": text_ids
    }