# app_ui.py (v4.3 - 單一畫布, 寬網格)

import tkinter as tk
from tkinter import ttk

from ui_components import ScrollableFrame
from constants import MAX_CLIENTS, DEFAULT_FG_COLOR, ELEMENT_COLOR_MAP
from utils import num_to_chinese

# (★★★) (修正 #3) Canvas 基礎高度
CANVAS_ROW_HEIGHT = 140 

# --- 靜態 UI 建立函式 ---

def create_main_widgets(app):
    """建立主視窗介面 (左右佈局)"""
    main_frame = ttk.Frame(app, padding=10)
    main_frame.pack(fill="both", expand=True)

    # 左側框架
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
        checkbox.pack(anchor="w", pady=3)
        checkbox.bind("<Button-3>", lambda e, idx=i: app.on_client_right_click_single(e, idx))
        checkbox.bind("<Double-Button-3>", lambda e, idx=i: app.on_client_right_click_double(e, idx))
        app.client_checkboxes.append(checkbox)

    # 右側 Notebook
    right_frame = ttk.Frame(main_frame, relief="sunken")
    right_frame.pack(side="right", fill="both", expand=True)

    app.notebook = ttk.Notebook(right_frame)
    app.notebook.pack(fill="both", expand=True)
    
    # (★★★) (修正 #3) 綁定頁籤切換事件
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
                              
    cb_speed.pack(anchor="w", pady=3)
    cb_walk.pack(anchor="w", pady=3)
    cb_noclip.pack(anchor="w", pady=3)
    cb_hide.pack(anchor="w", pady=3)
    
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
    (★★★) (修正 #1)
    建立單一的 Canvas，並在上面繪製所有文字物件。
    所有 6 欄都基於「人物」的 4 欄位寬網格。
    """
    
    # (★★★) (修正 #1) 依人物欄位為基準的寬度 (未縮放)
    base_col_width = 120 
    
    col_width = int(base_col_width * app_instance.scaling_factor)
    x_padding = 10
    start_x = 10
    
    # (★★★) (修正 #1) 總寬度 = 6 * 欄寬 + 5 * 間距 + 2 * 邊距
    canvas_width = (col_width * 6) + (x_padding * 5) + (start_x * 2)
    canvas_height = int(CANVAS_ROW_HEIGHT * app_instance.scaling_factor)
    
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
        # (★★★) (修正 #1) 嚴格等寬
        x_offset = start_x + (col_width + x_padding) * (i + 1)
        
        canvas.create_line(
            x_offset - (x_padding // 2) - 1, 10, 
            x_offset - (x_padding // 2) - 1, canvas_height - 10, 
            fill="#CCCCCC"
        )
        
        pet_vars = _draw_pet_canvas_items(canvas, x_offset, i)
        all_vars_list.append(pet_vars)
        
    return canvas, all_vars_list


def _draw_person_canvas_items(canvas, x):
    """(★★★) (修正 #1) 繪製人物欄位 (使用 4 欄位寬網格)"""
    
    vars_dict = {} 
    y = 15
    y_step = 24
    
    x_label_1 = x
    x_value_1 = x + 45
    
    # (★★★) 修正座標：將第 2 欄向右移動，避免重疊
    x_label_2 = x + 100 # (原為 105) 
    x_value_2 = x + 145 # (原為 140)
    
    vars_dict["name"] = canvas.create_text(x_label_1, y, text="人物", font=("Arial", 9, "bold"), anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    
    vars_dict["nickname"] = canvas.create_text(x_label_1, y, text="稱號", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="LV:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["lv"] = canvas.create_text(x_value_1, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["rebirth"] = canvas.create_text(x_label_2, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="HP:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["hp"] = canvas.create_text(x_value_1, y, text="--/--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    canvas.create_text(x_label_1, y, text="MP:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["mp"] = canvas.create_text(x_value_1, y, text="--/--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="攻擊:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["atk"] = canvas.create_text(x_value_1, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    canvas.create_text(x_label_2, y, text="防禦:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["def"] = canvas.create_text(x_value_2, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    
    canvas.create_text(x_label_1, y, text="敏捷:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["agi"] = canvas.create_text(x_value_1, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    canvas.create_text(x_label_2, y, text="魅力:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["charm"] = canvas.create_text(x_value_2, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    
    canvas.create_text(x_label_1, y, text="屬性:", anchor="w", fill=DEFAULT_FG_COLOR)
    elem_x = x_value_1
    elem_step = 45
    val_offset = 15 # (修正) 增加 "地" 和 "10" 之間的距離 (原為 12)
    
    canvas.create_text(elem_x, y, text="地", anchor="w", fill=ELEMENT_COLOR_MAP["地"])
    vars_dict["elem_e_val"] = canvas.create_text(elem_x + 12, y, text="", anchor="w", fill=ELEMENT_COLOR_MAP["地"])
    elem_x += elem_step
    
    canvas.create_text(elem_x, y, text="水", anchor="w", fill=ELEMENT_COLOR_MAP["水"])
    vars_dict["elem_w_val"] = canvas.create_text(elem_x + 12, y, text="", anchor="w", fill=ELEMENT_COLOR_MAP["水"])
    elem_x += elem_step

    canvas.create_text(elem_x, y, text="火", anchor="w", fill=ELEMENT_COLOR_MAP["火"])
    vars_dict["elem_f_val"] = canvas.create_text(elem_x + 12, y, text="", anchor="w", fill=ELEMENT_COLOR_MAP["火"])
    elem_x += elem_step
    
    canvas.create_text(elem_x, y, text="風", anchor="w", fill=ELEMENT_COLOR_MAP["風"])
    vars_dict["elem_wi_val"] = canvas.create_text(elem_x + 12, y, text="", anchor="w", fill=ELEMENT_COLOR_MAP["風"])
    y += (y_step - 4)

    canvas.create_line(x_label_1, y, x_value_2 + 30, y, fill="#DDDDDD") # (原為 + 45)
    y += (y_step - 8)

    canvas.create_text(x_label_1, y, text="體力:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["vit"] = canvas.create_text(x_value_1, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    canvas.create_text(x_label_2, y, text="腕力:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["str"] = canvas.create_text(x_value_2, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    
    canvas.create_text(x_label_1, y, text="耐力:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["sta"] = canvas.create_text(x_value_1, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    canvas.create_text(x_label_2, y, text="速度:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["spd"] = canvas.create_text(x_value_2, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    
    return vars_dict
    

def _draw_pet_canvas_items(canvas, x, pet_index):
    """(★★★) (修正 #1) 繪製寵物欄位 (也使用 4 欄位寬網格)"""
    
    vars_dict = {} 
    y = 15
    y_step = 24
    
    x_label_1 = x
    x_value_1 = x + 45
    x_label_2 = x + 100 # 轉生專用
    
    vars_dict["name"] = canvas.create_text(x_label_1, y, text=f"寵物{num_to_chinese(pet_index + 1)}", font=("Arial", 9, "bold"), anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    
    vars_dict["nickname"] = canvas.create_text(x_label_1, y, text="", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="LV:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["lv"] = canvas.create_text(x_value_1, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["rebirth"] = canvas.create_text(x_label_2, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="經驗:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["exp"] = canvas.create_text(x_value_1, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    canvas.create_text(x_label_1, y, text="還欠:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["lack"] = canvas.create_text(x_value_1, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    canvas.create_text(x_label_1, y, text="HP:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["hp"] = canvas.create_text(x_value_1, y, text="--/--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    
    canvas.create_text(x_label_1, y, text="攻擊:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["atk"] = canvas.create_text(x_value_1, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    canvas.create_text(x_label_1, y, text="防禦:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["def"] = canvas.create_text(x_value_1, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step
    canvas.create_text(x_label_1, y, text="敏捷:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["agi"] = canvas.create_text(x_value_1, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    y += y_step

    # (★★★) (修正 #1) 寵物的屬性也使用更寬的佈局
    canvas.create_text(x_label_1, y, text="屬性:", anchor="w", fill=DEFAULT_FG_COLOR)
    elem_x = x_value_1 # 您的 x_value_1 (x + 45)
    elem_step = 30 # (修正) 增加元素間的總寬度 (原為 35)
    val_offset = 0 # (修正) 增加 "地" 和 "10" 之間的距離 (原為 12)
    
    canvas.create_text(elem_x, y, text="地", anchor="w", fill=ELEMENT_COLOR_MAP["地"])
    vars_dict["elem_e_val"] = canvas.create_text(elem_x + 12, y, text="", anchor="w", fill=ELEMENT_COLOR_MAP["地"])
    elem_x += elem_step
    
    canvas.create_text(elem_x, y, text="水", anchor="w", fill=ELEMENT_COLOR_MAP["水"])
    vars_dict["elem_w_val"] = canvas.create_text(elem_x + 12, y, text="", anchor="w", fill=ELEMENT_COLOR_MAP["水"])
    elem_x += elem_step

    canvas.create_text(elem_x, y, text="火", anchor="w", fill=ELEMENT_COLOR_MAP["火"])
    vars_dict["elem_f_val"] = canvas.create_text(elem_x + 12, y, text="", anchor="w", fill=ELEMENT_COLOR_MAP["火"])
    elem_x += elem_step
    
    canvas.create_text(elem_x, y, text="風", anchor="w", fill=ELEMENT_COLOR_MAP["風"])
    vars_dict["elem_wi_val"] = canvas.create_text(elem_x + 12, y, text="", anchor="w", fill=ELEMENT_COLOR_MAP["風"])
    y += y_step

    canvas.create_text(x_label_1, y, text="忠誠:", anchor="w", fill=DEFAULT_FG_COLOR)
    vars_dict["loyal"] = canvas.create_text(x_value_1, y, text="--", anchor="w", fill=DEFAULT_FG_COLOR)
    
    return vars_dict