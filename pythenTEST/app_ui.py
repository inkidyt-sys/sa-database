# app_ui.py (v4.8.2 - DPI 選擇版面 + 解析度縮放)

import tkinter as tk
from tkinter import ttk
# (★★★) v4.8: DPI 偵測已移至 main.py

from ui_components import ScrollableFrame
from constants import MAX_CLIENTS, DEFAULT_FG_COLOR, ELEMENT_COLOR_MAP
from utils import num_to_chinese

# --- (★★★) v4.8 手動佈局調適區 (4K 基礎參數) (★★★) ---
# 說明: main.py 將會:
# 1. 偵測真實的 DPI
# 2. 根據 DPI 選擇以下三組 4K 參數之一
# 3. 偵測真實的螢幕解析度並計算比例 (例如 1080p / 2160p = 0.5)
# 4. 將選中的 4K 參數 * 比例，存入下方的「最終參數」區塊

# --- (★★★) 適用於 100% DPI (4K 螢幕) ---
PARAMS_4K_100 = {
    # --- 1. 主視窗與面板 ---
    "APP_BASE_WIDTH": 950,         # 主視窗的基礎寬度
    "APP_BASE_HEIGHT": 250,         # 主視窗的基礎高度 (用於「遊戲設置」等非動態頁籤)
    "LEFT_PANEL_WIDTH": 150,        # 左側「綁定」面板的寬度
    "NON_CONTENT_HEIGHT": 150,      # 「人寵資料」頁籤的「非內容」高度 (頂部頁籤 + 底部空白的總和)
    "CANVAS_ROW_PADDING": 15,       # 「人寵資料」中，每個客戶端 (窗口1, 窗口2...) 之間的*垂直*間距

    # --- 2. 頁籤內部間距 ---
    "LEFT_CHECKBOX_PADY": 1,        # 左側「窗口 1~6」複選框的*垂直*行距
    "SETTINGS_CHECKBOX_PADY": 1,    # 「遊戲設置」頁籤中「遊戲加速」等選項的*垂直*行距

    # --- 3. Canvas 畫布全域 ---
    "CANVAS_FONT_SIZE": 8.5,         # 「人寵資料」畫布上所有文字的基礎字體大小
    "CANVAS_Y_START": 8,           # 「人寵資料」畫布上第一行文字的 Y 座標 (頂部邊距)
    "CANVAS_Y_STEP": 15,            # 「人寵資料」畫布上每行文字之間的*垂直*行距
    "CANVAS_COL_WIDTH": 110,        # 「人寵資料」畫布上每一欄 (人物、寵物1、寵物2...) 的*寬度*
    "CANVAS_COL_PADDING": 8,        # 「人寵資料」畫布上每一欄之間的*水平*間距
    "CANVAS_START_X": 5,           # 「人寵資料」畫布上第一欄 (人物) 的 X 座標 (左側邊距)

    # --- 4. Canvas 內部座標 (人物/寵物欄位) ---
    "CANVAS_X_VAL_1": 25,           # 畫布中第一欄數值 (例如 LV: *45*) 的 X 座標偏移
    "CANVAS_X_LBL_2": 60,          # 畫布中第二欄標籤 (例如 防禦: *100*) 的 X 座標偏移
    "CANVAS_X_VAL_2": 85,          # 畫布中第二欄數值 (例如 防禦: -- *145*) 的 X 座標偏移

    # --- 5. 屬性欄位座標 ---
    "CANVAS_ELEM_VAL_OFFSET": 13,   # 屬性欄位: 標籤 (地) 到 數值 (10) 之間的水平間距
    "CANVAS_ELEM_STEP": 30,         # 屬性欄位: 每個屬性之間 (地 10 到 水 10) 的總水平寬度

    # --- 6. 人物欄位 Y 軸微調 (分隔線) ---
    "CANVAS_PERSON_Y_ADJ_1": 0,     # 人物: 縮短「屬性」與「分隔線」的間距
    "CANVAS_PERSON_Y_ADJ_2": 0,    # 人物: 縮短「分隔線」與「體力」的間距
}
# --- (★★★) 適用於 125% DPI (4K 螢幕) ---
PARAMS_4K_125 = {
    # (★★★) 請手動修改這些 4K @ 125% DPI 的參數 (範例為 100% * 1.25)
    
    # --- 1. 主視窗與面板 ---
    "APP_BASE_WIDTH": 1380,         # 主視窗的基礎寬度
    "APP_BASE_HEIGHT": 350,         # 主視窗的基礎高度 (用於「遊戲設置」等非動態頁籤)
    "LEFT_PANEL_WIDTH": 150,        # 左側「綁定」面板的寬度
    "NON_CONTENT_HEIGHT": 150,      # 「人寵資料」頁籤的「非內容」高度 (頂部頁籤 + 底部空白的總和)
    "CANVAS_ROW_PADDING": 20,       # 「人寵資料」中，每個客戶端 (窗口1, 窗口2...) 之間的*垂直*間距

    # --- 2. 頁籤內部間距 ---
    "LEFT_CHECKBOX_PADY": 1,        # 左側「窗口 1~6」複選框的*垂直*行距
    "SETTINGS_CHECKBOX_PADY": 1,    # 「遊戲設置」頁籤中「遊戲加速」等選項的*垂直*行距

    # --- 3. Canvas 畫布全域 ---
    "CANVAS_FONT_SIZE": 9,         # 「人寵資料」畫布上所有文字的基礎字體大小
    "CANVAS_Y_START": 8,           # 「人寵資料」畫布上第一行文字的 Y 座標 (頂部邊距)
    "CANVAS_Y_STEP": 18,            # 「人寵資料」畫布上每行文字之間的*垂直*行距
    "CANVAS_COL_WIDTH": 180,        # 「人寵資料」畫布上每一欄 (人物、寵物1、寵物2...) 的*寬度*
    "CANVAS_COL_PADDING": 10,        # 「人寵資料」畫布上每一欄之間的*水平*間距
    "CANVAS_START_X": 5,           # 「人寵資料」畫布上第一欄 (人物) 的 X 座標 (左側邊距)

    # --- 4. Canvas 內部座標 (人物/寵物欄位) ---
    "CANVAS_X_VAL_1": 40,           # 畫布中第一欄數值 (例如 LV: *45*) 的 X 座標偏移
    "CANVAS_X_LBL_2": 100,          # 畫布中第二欄標籤 (例如 防禦: *100*) 的 X 座標偏移
    "CANVAS_X_VAL_2": 140,          # 畫布中第二欄數值 (例如 防禦: -- *145*) 的 X 座標偏移

    # --- 5. 屬性欄位座標 ---
    "CANVAS_ELEM_VAL_OFFSET": 20,   # 屬性欄位: 標籤 (地) 到 數值 (10) 之間的水平間距
    "CANVAS_ELEM_STEP": 45,         # 屬性欄位: 每個屬性之間 (地 10 到 水 10) 的總水平寬度

    # --- 6. 人物欄位 Y 軸微調 (分隔線) ---
    "CANVAS_PERSON_Y_ADJ_1": 0,     # 人物: 縮短「屬性」與「分隔線」的間距
    "CANVAS_PERSON_Y_ADJ_2": 0,    # 人物: 縮短「分隔線」與「體力」的間距
}
# --- (★★★) 適用於 150% DPI (4K 螢幕) ---
PARAMS_4K_150 = {
    # (★★★) 請手動修改這些 4K @ 150% DPI 的參數 (範例為 100% * 1.5)

    # --- 1. 主視窗與面板 ---
    "APP_BASE_WIDTH": 1600,         # 主視窗的基礎寬度
    "APP_BASE_HEIGHT": 390,         # 主視窗的基礎高度 (用於「遊戲設置」等非動態頁籤)
    "LEFT_PANEL_WIDTH": 150,        # 左側「綁定」面板的寬度
    "NON_CONTENT_HEIGHT": 150,      # 「人寵資料」頁籤的「非內容」高度 (頂部頁籤 + 底部空白的總和)
    "CANVAS_ROW_PADDING": 30,       # 「人寵資料」中，每個客戶端 (窗口1, 窗口2...) 之間的*垂直*間距

    # --- 2. 頁籤內部間距 ---
    "LEFT_CHECKBOX_PADY": 1,        # 左側「窗口 1~6」複選框的*垂直*行距
    "SETTINGS_CHECKBOX_PADY": 1,    # 「遊戲設置」頁籤中「遊戲加速」等選項的*垂直*行距

    # --- 3. Canvas 畫布全域 ---
    "CANVAS_FONT_SIZE": 10,         # 「人寵資料」畫布上所有文字的基礎字體大小
    "CANVAS_Y_START": 10,           # 「人寵資料」畫布上第一行文字的 Y 座標 (頂部邊距)
    "CANVAS_Y_STEP": 20,            # 「人寵資料」畫布上每行文字之間的*垂直*行距
    "CANVAS_COL_WIDTH": 210,        # 「人寵資料」畫布上每一欄 (人物、寵物1、寵物2...) 的*寬度*
    "CANVAS_COL_PADDING": 10,        # 「人寵資料」畫布上每一欄之間的*水平*間距
    "CANVAS_START_X": 5,           # 「人寵資料」畫布上第一欄 (人物) 的 X 座標 (左側邊距)

    # --- 4. Canvas 內部座標 (人物/寵物欄位) ---
    "CANVAS_X_VAL_1": 50,           # 畫布中第一欄數值 (例如 LV: *45*) 的 X 座標偏移
    "CANVAS_X_LBL_2": 110,          # 畫布中第二欄標籤 (例如 防禦: *100*) 的 X 座標偏移
    "CANVAS_X_VAL_2": 160,          # 畫布中第二欄數值 (例如 防禦: -- *145*) 的 X 座標偏移

    # --- 5. 屬性欄位座標 ---
    "CANVAS_ELEM_VAL_OFFSET": 20,   # 屬性欄位: 標籤 (地) 到 數值 (10) 之間的水平間距
    "CANVAS_ELEM_STEP": 45,         # 屬性欄位: 每個屬性之間 (地 10 到 水 10) 的總水平寬度

    # --- 6. 人物欄位 Y 軸微調 (分隔線) ---
    "CANVAS_PERSON_Y_ADJ_1": 0,     # 人物: 縮短「屬性」與「分隔線」的間距
    "CANVAS_PERSON_Y_ADJ_2": 0,    # 人物: 縮短「分隔線」與「體力」的間距
}
# --- (★★★) UI 佈局調適區結束 (★★★) ---


# --- (★★★) v4.8 最終參數 (由 main.py 在啟動時填入) (★★★) ---
# 這些變數會被 main.py 覆寫, 編輯器可能會警告 "undefined"
# 這是正常現象, 請勿修改

# (★★★) v4.8.1 修正：新增 RESOLUTION_RATIO 預留位置
RESOLUTION_RATIO = 1.0 # (Will be overwritten by main.py)

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
# --- (★★★) 最終參數區塊結束 (★★★) ---


# --- 靜態 UI 建立函式 ---
# (★★★) v4.8: 這些函式*完全不變*, 
# 它們會自動讀取上方已被 main.py 計算好的最終參數

def create_main_widgets(app):
    """建立主視窗介面 (左右佈局)"""
    main_frame = ttk.Frame(app, padding=10)
    main_frame.pack(fill="both", expand=True)

    # v4.8: 使用 app.scaled_left_panel_width (已在 main.py 中設定)
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
    
    app.notebook.tab(2, state="disabled")
    app.notebook.tab(3, state="disabled")
    app.notebook.tab(4, state="disabled")


def create_settings_tab(tab_frame, app):
    """建立「遊戲設置」頁籤"""
    global_settings_frame = ttk.Frame(tab_frame)
    global_settings_frame.pack(fill="x", pady=(0, 5))

    ttk.Label(global_settings_frame, text="刷新頻率:").pack(side="left", padx=(5, 5))
    refresh_options = ['0.5s', '1s', '3s', '5s', '10s', '60s', '不刷新']
    app.refresh_rate_combo = ttk.Combobox(
        global_settings_frame, textvariable=app.refresh_rate_var,
        values=refresh_options, state="readonly", width=10
    )
    app.refresh_rate_var.set('3s') 
    app.refresh_rate_combo.pack(side="left")
    app.refresh_rate_combo.bind("<<ComboboxSelected>>", app.on_refresh_rate_change)

    ttk.Separator(tab_frame, orient="horizontal").pack(fill="x", pady=(0, 10))
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
    
# --- (★★★) (修正 #1) 返回「單一畫布」方案 ---

def create_client_info_canvas(parent_labelframe, app_instance):
    """
    (★★★) v4.8 變更: 
    1. 移除 scaling_factor 乘法
    2. app_instance 僅用於獲取背景色
    """
    
    col_width = LAYOUT_CANVAS_BASE_COL_WIDTH
    x_padding = LAYOUT_CANVAS_BASE_COL_PADDING
    start_x = LAYOUT_CANVAS_BASE_START_X
    
    canvas_height = BASE_CANVAS_ROW_HEIGHT
    
    # 總寬度 = 6 * 欄寬 + 5 * 間距 + 2 * 邊距
    canvas_width = (col_width * 6) + (x_padding * 5) + (start_x * 2)
    
    try:
        bg_color = parent_labelframe.cget("background")
    except:
        bg_color = app_instance.cget("background") # 僅用於此處

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
        
        # (★★★) v4.8.1 修正：
        # 使用 app_ui.RESOLUTION_RATIO 縮放 10px 固定值
        canvas.create_line(
            x_offset - (x_padding // 2) - 1, int(10 * RESOLUTION_RATIO), 
            x_offset - (x_padding // 2) - 1, canvas_height - int(10 * RESOLUTION_RATIO), 
            fill="#CCCCCC"
        )
        
        pet_vars = _draw_pet_canvas_items(canvas, x_offset, i)
        all_vars_list.append(pet_vars)
        
    return canvas, all_vars_list


def _draw_person_canvas_items(canvas, x):
    """(★★★) v4.8 變更: 移除 app_instance, 直接使用全局最終參數"""
    
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

    # (★★★) v4.8.1 修正：
    # 使用 app_ui.RESOLUTION_RATIO 縮放 45px 固定值
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
    """(★★★) v4.8 變更: 移除 app_instance, 直接使用全局最終參數"""
    
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