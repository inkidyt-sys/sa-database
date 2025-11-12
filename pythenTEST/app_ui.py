# app_ui.py
# 負責建立所有的 tkinter UI 元件

import tkinter as tk
from tkinter import ttk

from ui_components import ScrollableFrame
from constants import MAX_CLIENTS, DEFAULT_FG_COLOR, ELEMENT_COLOR_MAP
from utils import num_to_chinese

def create_main_widgets(app):
    """建立主視窗介面 (左右佈局)"""
    main_frame = ttk.Frame(app, padding=10)
    main_frame.pack(fill="both", expand=True)

    # 左側框架 (綁定和列表)
    left_frame = ttk.Frame(main_frame, width=app.scaled_left_panel_width, padding=(5,5,5,5), relief="groove")
    left_frame.pack(side="left", fill="y", padx=(0, 10))
    left_frame.pack_propagate(False)

    bind_button = ttk.Button(left_frame, text="綁定石器", command=app.on_bind_click)
    bind_button.pack(fill="x", pady=(5, 10), ipady=3)

    parent_bg = app.cget('background')

    for i in range(MAX_CLIENTS):
        checkbox = tk.Checkbutton(
            left_frame,
            text=f"窗口 {i+1}: 未綁定", 
            variable=app.client_selection_vars[i],
            onvalue=1, offvalue=0,
            command=app.on_selection_change, 
            state="disabled",
            disabledforeground="grey", 
            anchor="w",                
            bg=parent_bg,              
            selectcolor=parent_bg,     
            padx=0                     
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

    tab_names = ["遊戲設置", "人寵資料", "道具列表", "戰鬥狀態", "聊天窗口"]
    for name in tab_names:
        tab_frame = ttk.Frame(app.notebook, padding=5) 
        app.notebook.add(tab_frame, text=name)
        app.tabs[name] = tab_frame
        
    # 建立特定頁籤的內容
    create_settings_tab(app.tabs["遊戲設置"], app)
    create_character_tab(app.tabs["人寵資料"], app)
    
    # 鎖定未完成的分頁
    app.notebook.tab(2, state="disabled") # 道具列表
    app.notebook.tab(3, state="disabled") # 戰鬥狀態
    app.notebook.tab(4, state="disabled") # 聊天窗口


def create_settings_tab(tab_frame, app):
    """建立「遊戲設置」頁籤"""
    
    # 建立全局設定 (刷新頻率)
    global_settings_frame = ttk.Frame(tab_frame)
    global_settings_frame.pack(fill="x", pady=(0, 5))

    ttk.Label(global_settings_frame, text="刷新頻率:").pack(side="left", padx=(5, 5))
    
    refresh_options = ['0.5s', '1s', '3s', '5s', '10s', '60s', '不刷新']
    app.refresh_rate_combo = ttk.Combobox(
        global_settings_frame,
        textvariable=app.refresh_rate_var,
        values=refresh_options,
        state="readonly",
        width=10
    )
    app.refresh_rate_var.set('3s') # 預設值
    app.refresh_rate_combo.pack(side="left")
    app.refresh_rate_combo.bind("<<ComboboxSelected>>", app.on_refresh_rate_change)

    ttk.Separator(tab_frame, orient="horizontal").pack(fill="x", pady=(0, 10))
    
    # 建立客戶端專用設定
    app.tab_frame_settings = ScrollableFrame(tab_frame, orient="horizontal") 
    app.tab_frame_settings.pack(fill="both", expand=True) 

    app.setting_widgets = [] 
    for i in range(MAX_CLIENTS):
        frame = ttk.Labelframe(app.tab_frame_settings.inner_frame, text=f"窗口 {i+1}", padding=5)
        # 注意: 這裡*不* pack() - 它將由 update_all_displays 動態 pack/pack_forget
        
        (vars_dict, widgets_dict) = _create_settings_ui_frame(
            frame, 
            client_index=i,
            app_instance=app # 傳遞 app 實例以綁定 command
        )
        app.setting_widgets.append({
            "frame": frame,
            "vars": vars_dict,
            "widgets": widgets_dict
        })


def _create_settings_ui_frame(parent, client_index, app_instance):
    """輔助函式, 建立一組遊戲設置 UI"""
    setting_vars = {
        "game_speed": tk.IntVar(),
        "fast_walk": tk.IntVar(),
        "no_clip": tk.IntVar(),
        "hide_sa": tk.IntVar()
    }
    
    # 綁定到 app_instance 上的方法
    cmd_speed = lambda idx=client_index: app_instance.on_toggle_speed(idx)
    cmd_walk  = lambda idx=client_index: app_instance.on_toggle_walk(idx)
    cmd_noclip= lambda idx=client_index: app_instance.on_toggle_noclip(idx)
    cmd_hide  = lambda idx=client_index: app_instance.on_toggle_hide(idx)
    
    cb_speed = ttk.Checkbutton(parent, text="遊戲加速", 
                               variable=setting_vars["game_speed"],
                               command=cmd_speed)
    cb_walk = ttk.Checkbutton(parent, text="快速行走", 
                              variable=setting_vars["fast_walk"],
                              command=cmd_walk)
    cb_noclip = ttk.Checkbutton(parent, text="穿牆行走", 
                                variable=setting_vars["no_clip"],
                                command=cmd_noclip)
    cb_hide = ttk.Checkbutton(parent, text="隱藏石器", 
                              variable=setting_vars["hide_sa"],
                              command=cmd_hide)
                              
    cb_speed.pack(anchor="w", pady=3)
    cb_walk.pack(anchor="w", pady=3)
    cb_noclip.pack(anchor="w", pady=3)
    cb_hide.pack(anchor="w", pady=3)
    
    widgets = {
        "speed": cb_speed, "walk": cb_walk, 
        "noclip": cb_noclip, "hide": cb_hide
    }
    return (setting_vars, widgets)


def create_character_tab(tab_frame, app):
    """建立「人寵資料」頁籤 (v3.9 動態邏輯)"""
    app.tab_frame_char = ScrollableFrame(tab_frame, orient="vertical") 
    app.tab_frame_char.pack(fill="both", expand=True) 
    
    # 確保 inner_frame 會隨 grid 縮放
    app.tab_frame_char.inner_frame.columnconfigure(0, weight=1)
    
    # UI 將在 update_all_displays 中被動態建立


def create_person_column(parent_frame, grid_column, vars_dict):
    """建立 "人物" 介面 (填充傳入的 vars_dict)"""
    frame = ttk.Frame(parent_frame, padding=(5, 2))
    frame.grid(row=0, column=grid_column, sticky="nsw", padx=(5,0))
    
    vars_dict.update({
        "name": None, "nickname": None, "lv": None,
        "hp": None, "mp": None, "rebirth": None, "atk": None,
        "def": None, "agi": None, "charm": None, 
        "element_frame": None, 
        "vit": None, "str": None, "sta": None, "spd": None,
        "parent_frame": frame,
        "last_element": None # (v3.7) 屬性快取
    })
    
    r = 0 
    vars_dict["name"] = ttk.Label(frame, text="人物", font=("Arial", 9, "bold"))
    vars_dict["name"].grid(row=r, column=0, columnspan=4, sticky="w", pady=0)
    
    r += 1
    vars_dict["nickname"] = ttk.Label(frame, text="稱號")
    vars_dict["nickname"].grid(row=r, column=0, columnspan=4, sticky="w", pady=0)
    
    r += 1
    ttk.Label(frame, text="LV:").grid(row=r, column=0, sticky="w", pady=0)
    vars_dict["lv"] = ttk.Label(frame, text="--")
    vars_dict["lv"].grid(row=r, column=1, sticky="w")
    
    vars_dict["rebirth"] = ttk.Label(frame, text="--") 
    vars_dict["rebirth"].grid(row=r, column=2, columnspan=2, sticky="w", padx=(5,0))
    
    r += 1
    ttk.Label(frame, text="HP:").grid(row=r, column=0, sticky="w", pady=0)
    vars_dict["hp"] = ttk.Label(frame, text="--/--")
    vars_dict["hp"].grid(row=r, column=1, columnspan=3, sticky="w")
    
    r += 1
    ttk.Label(frame, text="MP:").grid(row=r, column=0, sticky="w", pady=0)
    vars_dict["mp"] = ttk.Label(frame, text="--/--")
    vars_dict["mp"].grid(row=r, column=1, columnspan=3, sticky="w")
    
    r += 1
    ttk.Label(frame, text="攻擊:").grid(row=r, column=0, sticky="w", pady=0)
    vars_dict["atk"] = ttk.Label(frame, text="--")
    vars_dict["atk"].grid(row=r, column=1, sticky="w")
    ttk.Label(frame, text="防禦:").grid(row=r, column=2, sticky="w", padx=(5,0))
    vars_dict["def"] = ttk.Label(frame, text="--")
    vars_dict["def"].grid(row=r, column=3, sticky="w")
    
    r += 1
    ttk.Label(frame, text="敏捷:").grid(row=r, column=0, sticky="w", pady=0)
    vars_dict["agi"] = ttk.Label(frame, text="--")
    vars_dict["agi"].grid(row=r, column=1, sticky="w")
    ttk.Label(frame, text="魅力:").grid(row=r, column=2, sticky="w", padx=(5,0))
    vars_dict["charm"] = ttk.Label(frame, text="--") 
    vars_dict["charm"].grid(row=r, column=3, sticky="w")
    
    r += 1
    ttk.Label(frame, text="屬性:").grid(row=r, column=0, sticky="w", pady=0)
    vars_dict["element_frame"] = ttk.Frame(frame) 
    vars_dict["element_frame"].grid(row=r, column=1, columnspan=3, sticky="w")
    
    r += 1
    ttk.Separator(frame, orient="horizontal").grid(row=r, column=0, columnspan=5, sticky="ew", pady=3)
    
    r += 1
    ttk.Label(frame, text="體力:").grid(row=r, column=0, sticky="w", pady=0)
    vars_dict["vit"] = ttk.Label(frame, text="--")
    vars_dict["vit"].grid(row=r, column=1, sticky="w")
    ttk.Label(frame, text="腕力:").grid(row=r, column=2, sticky="w", padx=(5,0))
    vars_dict["str"] = ttk.Label(frame, text="--")
    vars_dict["str"].grid(row=r, column=3, sticky="w")
    
    r += 1
    ttk.Label(frame, text="耐力:").grid(row=r, column=0, sticky="w", pady=0)
    vars_dict["sta"] = ttk.Label(frame, text="--")
    vars_dict["sta"].grid(row=r, column=1, sticky="w")
    ttk.Label(frame, text="速度:").grid(row=r, column=2, sticky="w", padx=(5,0))
    vars_dict["spd"] = ttk.Label(frame, text="--")
    vars_dict["spd"].grid(row=r, column=3, sticky="w")
        
def create_pet_column(parent_frame, pet_index, grid_column):
    """建立 "寵物" 介面 (建立並 *返回* pet_vars)"""
    frame = ttk.Frame(parent_frame, padding=(5, 2))
    frame.grid(row=0, column=grid_column, sticky="nsw", padx=(5,0))
    
    pet_vars = {
        "name": None, "nickname": None, "lv": None,
        "exp": None, "lack": None, "hp": None, "atk": None,
        "def": None, "agi": None, 
        "loyal": None, 
        "element_frame": None, 
        "rebirth": None,
        "parent_frame": frame,
        "last_element": None # (v3.7) 屬性快取
    }
    
    r = 0 
    pet_vars["name"] = ttk.Label(frame, text=f"寵物{num_to_chinese(pet_index + 1)}", font=("Arial", 9, "bold"))
    pet_vars["name"].grid(row=r, column=0, columnspan=4, sticky="w", pady=0)
    
    r += 1
    pet_vars["nickname"] = ttk.Label(frame, text="")
    pet_vars["nickname"].grid(row=r, column=0, columnspan=4, sticky="w", pady=0)
    
    r += 1
    ttk.Label(frame, text="LV:").grid(row=r, column=0, sticky="w", pady=0)
    pet_vars["lv"] = ttk.Label(frame, text="--")
    pet_vars["lv"].grid(row=r, column=1, sticky="w")
    pet_vars["rebirth"] = ttk.Label(frame, text="--") 
    pet_vars["rebirth"].grid(row=r, column=2, columnspan=2, sticky="w", padx=(5,0))
    
    r += 1
    ttk.Label(frame, text="經驗:").grid(row=r, column=0, sticky="w", pady=0)
    pet_vars["exp"] = ttk.Label(frame, text="--")
    pet_vars["exp"].grid(row=r, column=1, columnspan=3, sticky="w")
    
    r += 1
    ttk.Label(frame, text="還欠:").grid(row=r, column=0, sticky="w", pady=0)
    pet_vars["lack"] = ttk.Label(frame, text="--")
    pet_vars["lack"].grid(row=r, column=1, columnspan=3, sticky="w")
    
    r += 1
    ttk.Label(frame, text="HP:").grid(row=r, column=0, sticky="w", pady=0)
    pet_vars["hp"] = ttk.Label(frame, text="--/--")
    pet_vars["hp"].grid(row=r, column=1, columnspan=3, sticky="w")
    
    r += 1
    ttk.Label(frame, text="攻擊:").grid(row=r, column=0, sticky="w", pady=0)
    pet_vars["atk"] = ttk.Label(frame, text="--")
    pet_vars["atk"].grid(row=r, column=1, columnspan=3, sticky="w")
    
    r += 1
    ttk.Label(frame, text="防禦:").grid(row=r, column=0, sticky="w", pady=0)
    pet_vars["def"] = ttk.Label(frame, text="--")
    pet_vars["def"].grid(row=r, column=1, columnspan=3, sticky="w")
    
    r += 1
    ttk.Label(frame, text="敏捷:").grid(row=r, column=0, sticky="w", pady=0)
    pet_vars["agi"] = ttk.Label(frame, text="--")
    pet_vars["agi"].grid(row=r, column=1, columnspan=3, sticky="w")
    
    r += 1
    ttk.Label(frame, text="屬性:").grid(row=r, column=0, sticky="w", pady=0)
    pet_vars["element_frame"] = ttk.Frame(frame) 
    pet_vars["element_frame"].grid(row=r, column=1, columnspan=3, sticky="w")
    
    r += 1
    ttk.Label(frame, text="忠誠:").grid(row=r, column=0, sticky="w", pady=0)
    pet_vars["loyal"] = ttk.Label(frame, text="--") 
    pet_vars["loyal"].grid(row=r, column=1, columnspan=3, sticky="w")

    return pet_vars 

def update_element_display(frame_widget, element_string, app_bg_color):
    """(Refactored) 動態更新屬性標籤 (支援顏色)"""
    for widget in frame_widget.winfo_children():
        widget.destroy()
    
    try:
        bg_color = frame_widget.cget("background")
    except:
        bg_color = app_bg_color # 備用

    if not element_string or element_string == "無":
        tk.Label(
            frame_widget, 
            text="無", 
            fg=DEFAULT_FG_COLOR, 
            font=("Arial", 9), 
            bg=bg_color
        ).pack(side="left", padx=(0, 4))
        return

    parts = element_string.split(" ")
    for part in parts:
        if not part: continue
        elem_char = part[0] 
        color = ELEMENT_COLOR_MAP.get(elem_char, DEFAULT_FG_COLOR)
        
        tk.Label(
            frame_widget, 
            text=part, 
            fg=color, 
            font=("Arial", 9), 
            bg=bg_color
        ).pack(side="left", padx=(0, 4))