import tkinter as tk
from tkinter import ttk, scrolledtext, Canvas, Scrollbar
import ctypes
import os
import sys
import time 

import pymem
import pymem.pattern
import psutil
try:
    import ctypes.wintypes
except ImportError:
    print("缺少 ctypes.wintypes 模組")
    sys.exit(1)


# --- DPI 感知設定 (必須在 tkinter 之前) ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1) 
except (AttributeError, OSError):
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass
# --- DPI 感知結束 ---


# --- 修補設定 (全域變數) ---
PROCESS_NAME = "sadsa.exe"
MAX_CLIENTS = 6

# --- 狀態/帳號 Offsets ---
GAME_STATE_OFFSET = 0x1042EAE4
ACCOUNT_STRING_OFFSET = 0x1DE37C

# --- 人物資料 Offsets ---
CHAR_NAME_OFFSET = 0x1041E318       # Big5 (16 bytes)
CHAR_NICKNAME_OFFSET = 0x1041E329   # Big5 (12 bytes)
CHAR_REBIRTH_OFFSET = 0x10421854    # Int (0-6)
CHAR_LV_OFFSET = 0x1041E2E0         # Int
CHAR_HP_CUR_OFFSET = 0x1041E2B8     # Int
CHAR_HP_MAX_OFFSET = 0x1041E2BC     # Int
CHAR_MP_CUR_OFFSET = 0x1041E2C0     # Int
CHAR_MP_MAX_OFFSET = 0x1041E2C4     # Int
CHAR_ATK_OFFSET = 0x1041E2E4        # Int
CHAR_DEF_OFFSET = 0x1041E2E8        # Int
CHAR_AGI_OFFSET = 0x1041E2EC        # Int
CHAR_CHARM_OFFSET = 0x1041E2F0      # Int
CHAR_ELEM_EARTH_OFFSET = 0x1041E2F8 # Int
CHAR_ELEM_WATER_OFFSET = 0x1041E2FC # Int
CHAR_ELEM_FIRE_OFFSET = 0x1041E300  # Int
CHAR_ELEM_WIND_OFFSET = 0x1041E304  # Int
CHAR_VIT_OFFSET = 0x1041E2C8        # Int (體力)
CHAR_STR_OFFSET = 0x1041E2CC        # Int (腕力)
CHAR_STA_OFFSET = 0x1041E2D0        # Int (耐力)
CHAR_SPD_OFFSET = 0x1041E2D4        # Int (速度)

# --- (★★★) 寵物資料 Offsets (v2.4 Struct 邏輯修正) (★★★) ---
PET_1_BASE_OFFSET = 0x104252A0      # 寵物 1 結構的基址 (以 HP_CUR 為準)
PET_STRUCT_SIZE = 0xFE8             # 寵物 1 到 2 的偏移

# (相對於 PET_1_BASE_OFFSET 的偏移量)
PET_HP_CUR_REL = 0x0
PET_HP_MAX_REL = 0x4
PET_EXP_REL = 0x10
PET_LACK_REL = 0x14
PET_LV_REL = 0x18
PET_ATK_REL = 0x1C
PET_DEF_REL = 0x20
PET_AGI_REL = 0x24
PET_LOYALTY_REL = 0x28
PET_ELEM_EARTH_REL = 0x2C
PET_ELEM_WATER_REL = 0x30
PET_ELEM_FIRE_REL = 0x34
PET_ELEM_WIND_REL = 0x38 
PET_REBIRTH_REL = 0x40
PET_NAME_REL = 0x4C                 # (0x52EC - 0x52A0 = 0x4C)
PET_NICKNAME_REL = 0x5D             # (0x52FD - 0x52A0 = 0x5D)
PET_EXIST_REL = 0x6E                # (0x530E - 0x52A0 = 0x6E)


# 轉生對應表
REBIRTH_MAP = {
    0: "未轉生", 1: "轉生壹", 2: "轉生貳",
    3: "轉生叁", 4: "轉生肆", 5: "轉生伍", 6: "轉生陸"
}
PET_LACK_EXP_MAX = 4294967295

# (★★★) v2.6: 顏色定義
REBIRTH_COLOR_MAP = {
    "未轉生": "black",
    "轉生壹": "#E5C100",  # 暗黃色 (Yellow 在白底上看不清楚)
    "轉生貳": "#35B315",
    "轉生叁": "#45DDE2",
    "轉生肆": "red",
    "轉生伍": "purple",
    "轉生陸": "#8F8C8C"
}
ELEMENT_COLOR_MAP = {
    "地": "green",
    "水": "blue",
    "火": "red",
    "風": "#E5C100"   # 暗黃色
}
DEFAULT_FG_COLOR = "black" # 預設字體顏色


# 1. 快速行走設定
AOB_PATTERN_WALK = rb"\x0F\x2F\x45\xEC..\xF3\x0F\x10\x45\xF4"
WALK_PATCH_OFFSET = 4      
WALK_PATCHED_BYTE = 0x74   

# 2. 遊戲加速設定
AOB_PATTERN_SPEED_1_ORIGINAL = rb"\x8B\x95\xD8\xFB\xFF\xFF\x03\x15....\x89\x95\xA4\xFB\xFF\xFF"
AOB_PATTERN_SPEED_1_PATCHED  = rb"\x8B\x95\xD8\xFB\xFF\xFF\x90\x90\x90\x90\x90\x90\x89\x95\xA4\xFB\xFF\xFF"
AOB_PATTERN_SPEED_2_ORIGINAL = rb"\x8B\x85\xD8\xFB\xFF\xFF\x03\x05....\x89\x85\xB4\xFB\xFF\xFF"
AOB_PATTERN_SPEED_2_PATCHED  = rb"\x8B\x85\D8\xFB\xFF\xFF\x90\x90\x90\x90\x90\x90\x89\x85\xB4\xFB\xFF\xFF"
SPEED_AOB_OFFSET = 6       
NOP_PATCH = b"\x90\x90\x90\x90\x90\x90" 

# 3. 穿牆行走設定
AOB_PATTERN_NOCLIP_ORIGINAL = rb"\x83\xFA\x01\x75.\xB8\x01\x00\x00\x00\xEB.\x33\xC0\x8B\xE5\x5D\xC3"
AOB_PATTERN_NOCLIP_PATCHED  = rb"\x83\xFA\x01\x75.\xB8\x00\x00\x00\x00\xEB.\x33\xC0\x8B\xE5\x5D\xC3"
NOCLIP_PATCH_OFFSET = 5      
NOCLIP_PATCHED_BYTES = b"\xB8\x00\x00\x00\x00" 

# 4. 隱藏石器設定 (WinAPI)
SW_HIDE = 0
SW_SHOW = 5 
# (★★★) v3.0: 新增 WinAPI 常數
SW_MINIMIZE = 6
SW_RESTORE = 9
# --------------------------------

# (★★★) v2.8: 修正滾輪綁定
class ScrollableFrame(ttk.Frame):
    """一個可滾動的 Frame (垂直或水平)"""
    def __init__(self, container, orient="vertical", *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        self.orient = orient 
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        
        if self.orient == "vertical":
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
            self.canvas.configure(yscrollcommand=self.scrollbar.set)
            self.scrollbar.pack(side="right", fill="y")
        else: # horizontal
            self.scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
            self.canvas.configure(xscrollcommand=self.scrollbar.set)
            self.scrollbar.pack(side="bottom", fill="x")
            
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.inner_frame = ttk.Frame(self.canvas)

        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.bind_mouse_wheel(self.canvas)
        self.bind_mouse_wheel(self.inner_frame)

    def bind_mouse_wheel(self, widget):
        widget.bind("<MouseWheel>", self.on_mouse_wheel)
        for child in widget.winfo_children():
            self.bind_mouse_wheel(child)
            
    def on_mouse_wheel(self, event):
        if self.orient == "vertical":
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else: 
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")


class DSAHelperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # (★★★) v3.7 修正: 更新標題
        self.title("DSA新端輔助程式 v3.7         by 石器推廣大使 陳財佑")
        
        # (★★★) 在這裡加入你的圖示 (★★★)
        try:
            self.iconbitmap("icon.ico")
        except tk.TclError:
            self.log("錯誤: 找不到 icon.ico 檔案。")
        
        # (★★★) v3.4: 指定預設高寬
        self.geometry("1420x420")

        # (★★★) v3.0: 寬度固定, 高度可拉伸
        self.resizable(False, True) 

        self.client_data_slots = [self.create_empty_slot_data() for _ in range(MAX_CLIENTS)]
        
        self.tabs = {} 
        
        self.client_selection_vars = [tk.IntVar() for _ in range(MAX_CLIENTS)]
        self.client_checkboxes = [] 
        
        # (★★★) v3.4: 新增刷新頻率變數
        self.refresh_rate_var = tk.StringVar()
        self.refresh_rate_combo = None # 儲存 Combobox 元件
        
        self.setting_widgets = []   
        self.person_vars = []       
        self.pet_vars_list = []     
        self.char_frames = []       

        self.tab_frame_settings = None 
        self.tab_frame_char = None     
        
        self.monitoring_active = False 
        
        if not self.is_admin():
            self.title(f"{self.title()} (錯誤：請以管理員權限執行)")
            label = tk.Label(self, text="錯誤：\n必須以「系統管理員」權限執行此程式！", 
                             font=("Arial", 12), fg="red", padx=50, pady=50)
            label.pack()
        else:
            self.create_widgets()

    def create_empty_slot_data(self):
        """(v3.5) 新增 pm_handle 用於儲存 pymem 物件"""
        return {
            "pid": None, "hwnd": None, "status": "未綁定", 
            "pm_handle": None, # (★★★) v3.5: 儲存 Pymem 句柄
            "module_base": None, 
            "char_data_cache": None, 
            "pet_data_cache": [None] * 5, 
            "account_name": "", 
            
            "walk_address": None, "walk_original_byte": None, "walk_is_patched": False,
            "speed_address_1": None, "speed_address_2": None, "speed_original_bytes_1": None, 
            "speed_original_bytes_2": None, "speed_is_patched": False,
            "noclip_address": None, "noclip_original_bytes": None, "noclip_is_patched": False,
            "is_hidden": False
        }

    def is_admin(self):
        try: return os.getuid() == 0
        except AttributeError: return ctypes.windll.shell32.IsUserAnAdmin() != 0

    def create_widgets(self):
        """(v3.1) 建立所有GUI元件 (綁定單/雙擊右鍵)"""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        left_frame = ttk.Frame(main_frame, width=170, padding=(5,5,5,5), relief="groove")
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        left_frame.pack_propagate(False)

        bind_button = ttk.Button(left_frame, text="綁定石器", command=self.on_bind_click)
        bind_button.pack(fill="x", pady=(5, 10), ipady=3)

        parent_bg = self.cget('background')

        for i in range(MAX_CLIENTS):
            checkbox = tk.Checkbutton(
                left_frame,
                text=f"窗口 {i+1}: 未綁定", 
                variable=self.client_selection_vars[i],
                onvalue=1, offvalue=0,
                command=self.on_selection_change, 
                state="disabled",
                disabledforeground="grey", 
                anchor="w",                
                bg=parent_bg,              
                selectcolor=parent_bg,     
                padx=0                     
            )
            checkbox.pack(anchor="w", pady=3)
            
            # (★★★) v3.1: 綁定單擊和雙擊右鍵
            checkbox.bind("<Button-3>", lambda e, idx=i: self.on_client_right_click_single(e, idx))
            checkbox.bind("<Double-Button-3>", lambda e, idx=i: self.on_client_right_click_double(e, idx))
            
            self.client_checkboxes.append(checkbox)

        # --- 右側 Notebook ---
        right_frame = ttk.Frame(main_frame, relief="sunken")
        right_frame.pack(side="right", fill="both", expand=True)

        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill="both", expand=True)

        tab_names = ["遊戲設置", "人寵資料", "道具列表", "戰鬥狀態", "聊天窗口"]
        for name in tab_names:
            tab_frame = ttk.Frame(self.notebook, padding=5) 
            self.notebook.add(tab_frame, text=name)
            self.tabs[name] = tab_frame
            
        self.create_settings_tab(self.tabs["遊戲設置"])
        self.create_character_tab(self.tabs["人寵資料"])
        
        # (★★★) v3.4: 鎖定未完成的分頁
        self.notebook.tab(2, state="disabled") # 道具列表
        self.notebook.tab(3, state="disabled") # 戰鬥狀態
        self.notebook.tab(4, state="disabled") # 聊天窗口
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log("介面初始化完成。請點擊 '綁定石器'。")


    def log(self, message):
        print(message) 

    # --- (★★★) v3.4: UI 建立 (新增刷新頻率) ---

    def create_settings_tab(self, tab_frame):
        """(v3.4) 建立「遊戲設置」頁籤 (新增全局刷新)"""
        
        # (★★★) v3.4: 建立全局設定 (刷新頻率)
        global_settings_frame = ttk.Frame(tab_frame)
        global_settings_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(global_settings_frame, text="刷新頻率:").pack(side="left", padx=(5, 5))
        
        refresh_options = ['0.5s', '1s', '3s', '5s', '10s', '60s', '不刷新']
        self.refresh_rate_combo = ttk.Combobox(
            global_settings_frame,
            textvariable=self.refresh_rate_var,
            values=refresh_options,
            state="readonly",
            width=10
        )
        self.refresh_rate_var.set('3s') # 預設值
        self.refresh_rate_combo.pack(side="left")
        self.refresh_rate_combo.bind("<<ComboboxSelected>>", self.on_refresh_rate_change)

        ttk.Separator(tab_frame, orient="horizontal").pack(fill="x", pady=(0, 10))
        
        # (★★★) v3.4: 建立客戶端專用設定
        self.tab_frame_settings = ScrollableFrame(tab_frame, orient="horizontal") 
        self.tab_frame_settings.pack(fill="both", expand=True) 

        self.setting_widgets = [] 
        for i in range(MAX_CLIENTS):
            frame = ttk.Labelframe(self.tab_frame_settings.inner_frame, text=f"窗口 {i+1}", padding=5)
            frame.pack(side="left", fill="y", anchor="n", padx=5, pady=5) 
            
            (vars_dict, widgets_dict) = self._create_settings_ui_frame(
                frame, 
                client_index=i
            )
            self.setting_widgets.append({
                "frame": frame,
                "vars": vars_dict,
                "widgets": widgets_dict
            })
            frame.pack_forget() 

        # (★★★) v3.7 修正: 滾輪綁定移至此處, 避免重複綁定
        self.tab_frame_settings.bind_mouse_wheel(self.tab_frame_settings.inner_frame)


    def _create_settings_ui_frame(self, parent, client_index=0):
        """(v2.9) 輔助函式, 建立一組遊戲設置"""
        setting_vars = {
            "game_speed": tk.IntVar(),
            "fast_walk": tk.IntVar(),
            "no_clip": tk.IntVar(),
            "hide_sa": tk.IntVar()
        }
        
        cmd_speed = lambda idx=client_index: self.on_toggle_speed(idx)
        cmd_walk  = lambda idx=client_index: self.on_toggle_walk(idx)
        cmd_noclip= lambda idx=client_index: self.on_toggle_noclip(idx)
        cmd_hide  = lambda idx=client_index: self.on_toggle_hide(idx)
        
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


    def create_character_tab(self, tab_frame):
        """v2.9: 建立「人寵資料」頁籤 (純複選, 垂直)"""
        self.tab_frame_char = ScrollableFrame(tab_frame, orient="vertical") 
        self.tab_frame_char.pack(fill="both", expand=True) 

        self._create_char_ui_all(self.tab_frame_char.inner_frame)
        
        # (★★★) v3.7 修正: 滾輪綁定移至此處, 避免重複綁定
        self.tab_frame_char.bind_mouse_wheel(self.tab_frame_char.inner_frame)


    def _create_char_ui_all(self, parent_frame):
        """(v3.1) 建立「全部」的人寵資料 UI (修正寬度)"""
        parent_frame.columnconfigure(0, weight=1) 
        
        self.person_vars = [] 
        self.pet_vars_list = [] 
        self.char_frames = [] 

        for i in range(MAX_CLIENTS):
            client_frame = ttk.Labelframe(parent_frame, text=f"窗口 {i+1}", padding=5)
            client_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=5) 
            
            # (★★★) v3.1: 預先設定最小寬度
            for col_idx in range(0, 11, 2):
                client_frame.columnconfigure(col_idx, minsize=170)
            client_frame.rowconfigure(0, weight=1)
            
            self.char_frames.append(client_frame) 
            
            person_vars_dict = {}
            self.create_person_column(client_frame, 0, person_vars_dict)
            self.person_vars.append(person_vars_dict)
            
            pet_vars_list_for_client = []
            for p_idx in range(5):
                sep = ttk.Separator(client_frame, orient="vertical")
                sep.grid(row=0, column=(p_idx*2 + 1), sticky="ns", padx=5)
                pet_vars = self.create_pet_column(client_frame, p_idx, (p_idx*2 + 2))
                pet_vars_list_for_client.append(pet_vars)
            self.pet_vars_list.append(pet_vars_list_for_client)
            
            client_frame.grid_forget() 

    def create_person_column(self, parent_frame, grid_column, vars_dict):
        """(v2.7) 建立 "人物" 介面 (填充傳入的 vars_dict)"""
        frame = ttk.Frame(parent_frame, padding=(5, 2))
        frame.grid(row=0, column=grid_column, sticky="nsw", padx=(5,0))
        
        vars_dict.update({
            "name": None, "nickname": None, "lv": None,
            "hp": None, "mp": None, "rebirth": None, "atk": None,
            "def": None, "agi": None, "charm": None, 
            "element_frame": None, 
            "vit": None, "str": None, "sta": None, "spd": None,
            "parent_frame": frame,
            "last_element": None # (★★★) v3.7 修正: 新增屬性快取
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
        
    def create_pet_column(self, parent_frame, pet_index, grid_column):
        """(v2.7) 建立 "寵物" 介面 (建立並 *返回* pet_vars)"""
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
            "last_element": None # (★★★) v3.7 修正: 新增屬性快取
        }
        
        r = 0 
        pet_vars["name"] = ttk.Label(frame, text=f"寵物{self.num_to_chinese(pet_index + 1)}", font=("Arial", 9, "bold"))
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

    def num_to_chinese(self, num):
        return ["一", "二", "三", "四", "五"][num - 1]

    # --- 核心功能：綁定與掃描 ---
    def find_game_windows(self):
        found_windows = []
        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL,
                                             ctypes.wintypes.HWND,
                                             ctypes.wintypes.LPARAM)
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
        """(★★★) v3.6: 綁定按鈕 (不重複綁定, 只添加新的)"""
        self.log(f"--- 開始檢查綁定並搜尋新窗口 ---")
        
        current_pids = set()
        
        # 1. 檢查現有綁定是否仍然有效
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            if slot["pid"] and slot["pm_handle"] and slot["module_base"]:
                try:
                    # (★★★) v3.6: 使用一個輕量的 read 來測試句柄是否有效
                    # 這比 psutil.pid_exists() 更可靠且無洩漏
                    slot["pm_handle"].read_int(slot["module_base"] + GAME_STATE_OFFSET)
                    
                    # 如果 read 成功, 說明句柄有效
                    current_pids.add(slot["pid"])
                    self.log(f"窗口 {i+1} (PID {slot['pid']}) 檢查通過, 保留綁定。")
                    continue # 跳過, 保留此 slot
                except Exception:
                    # read 失敗 (進程已關閉)
                    self.log(f"窗口 {i+1} (PID {slot['pid']}) 已失效, 清理...")
                    try:
                        slot["pm_handle"].close()
                    except Exception as e:
                        self.log(f"  > 關閉失效句柄時出錯: {e}")
            
            # (Slot 為空, 或剛被清理)
            self.client_data_slots[i] = self.create_empty_slot_data()
            self.client_selection_vars[i].set(0)
            self.update_client_list_display(i) # 更新為 "未綁定"

        # 2. 搜尋*新*的窗口
        found_windows = self.find_game_windows()
        new_windows = [w for w in found_windows if w[1] not in current_pids]

        if not new_windows:
            self.log("沒有找到新的窗口。")
            self.update_all_displays() # 確保 UI (例如剛被清理的) 已更新
            self.start_monitoring_loop() # 確保監控還在跑
            return

        # 3. 將新窗口填入空 slots
        self.log(f"找到 {len(new_windows)} 個新窗口, 正在綁定...")
        new_window_iter = iter(new_windows)
        for i in range(MAX_CLIENTS):
            if self.client_data_slots[i]["pid"] is None: # 這是個空 slot
                try:
                    hwnd, pid = next(new_window_iter)
                    slot = self.client_data_slots[i]
                    slot["pid"] = pid
                    slot["hwnd"] = hwnd
                    self.scan_client_addresses(i) # 綁定 & 獲取 pm_handle
                    self.log(f"新窗口 (PID {pid}) 已綁定到窗口 {i+1}")
                    self.update_client_list_display(i) # 更新左側列表
                except StopIteration:
                    break # 沒有更多新窗口了
        
        # 4. 統一更新 & 啟動監控
        self.update_all_displays()
        self.start_monitoring_loop()


    def scan_client_addresses(self, slot_index):
        """(v3.5) 掃描並快取 (儲存 pm_handle)"""
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
                pm.close() 
                slot["pm_handle"] = None
                return
            
            slot["module_base"] = module.lpBaseOfDll
            self.log(f"  > (PID: {pid}) 找到模組基址 @ 0x{module.lpBaseOfDll:X}")

            # --- 1. 處理「快速行走」 (v1.2 邏輯) ---
            try:
                addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_WALK)
                if not addr:
                    self.log(f"  > (PID: {pid}) 找不到「行走」特徵碼")
                    slot["walk_address"] = None 
                else:
                    patch_addr = addr + WALK_PATCH_OFFSET
                    curr_byte = pm.read_bytes(patch_addr, 1)[0]
                    slot["walk_address"] = patch_addr
                    if slot["walk_original_byte"] is None: slot["walk_original_byte"] = curr_byte
                    if curr_byte == WALK_PATCHED_BYTE: slot["walk_is_patched"] = True
                    elif curr_byte == slot["walk_original_byte"]: slot["walk_is_patched"] = False
                    self.log(f"  > (PID: {pid}) 找到「行走」 @ 0x{patch_addr:X} (狀態: {'已修補' if slot['walk_is_patched'] else '原始'})")
            except Exception as e: self.log(f"  > (PID: {pid}) 掃描「行走」出錯: {e}")

            # --- 2. 處理「遊戲加速」 (v1.3 邏輯) ---
            try:
                addr1, addr2 = None, None
                is_patched_scan = False
                addr1 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_1_ORIGINAL)
                addr2 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_2_ORIGINAL)
                if not addr1 or not addr2:
                    self.log(f"  > (PID: {pid}) 未找到「加速」原始 AOB，嘗試掃描已修補 AOB...")
                    addr1 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_1_PATCHED)
                    addr2 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_2_PATCHED)
                    if addr1 and addr2: is_patched_scan = True 
                if not addr1 or not addr2:
                    self.log(f"  > (PID: {pid}) 找不到「加速」特徵碼")
                    slot["speed_address_1"] = None; slot["speed_address_2"] = None
                else:
                    patch_addr1 = addr1 + SPEED_AOB_OFFSET
                    patch_addr2 = addr2 + SPEED_AOB_OFFSET
                    slot["speed_address_1"] = patch_addr1
                    slot["speed_address_2"] = patch_addr2
                    if is_patched_scan:
                        slot["speed_is_patched"] = True
                        if slot["speed_original_bytes_1"] is None: self.log(f"  > (PID: {pid}) 警告：找到已修補的「加速」位址，但沒有快取原始 bytes，將無法還原！")
                    else:
                        slot["speed_is_patched"] = False
                        slot["speed_original_bytes_1"] = pm.read_bytes(patch_addr1, len(NOP_PATCH))
                        slot["speed_original_bytes_2"] = pm.read_bytes(patch_addr2, len(NOP_PATCH))
                    self.log(f"  > (PID: {pid}) 找到「加速1」 @ 0x{patch_addr1:X} (狀態: {'已修補' if slot['speed_is_patched'] else '原始'})")
            except Exception as e: self.log(f"  > (PID: {pid}) 掃描「加速」出錯: {e}")

            # --- 3. 處理「穿牆行走」 (v1.3 邏輯) ---
            try:
                addr = None
                is_patched_scan = False
                addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_NOCLIP_ORIGINAL)
                if not addr:
                    self.log(f"  > (PID: {pid}) 未找到「穿牆」原始 AOB，嘗試掃描已修補 AOB...")
                    addr = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_NOCLIP_PATCHED)
                    if addr: is_patched_scan = True 
                if not addr:
                    self.log(f"  > (PID: {pid}) 找不到「穿牆」特徵碼")
                    slot["noclip_address"] = None
                else:
                    patch_addr = addr + NOCLIP_PATCH_OFFSET
                    slot["noclip_address"] = patch_addr
                    if is_patched_scan:
                        slot["noclip_is_patched"] = True
                        if slot["noclip_original_bytes"] is None: self.log(f"  > (PID: {pid}) 警告：找到已修補的「穿牆」位址，但沒有快取原始 bytes，將無法還原！")
                    else:
                        slot["noclip_is_patched"] = False
                        slot["noclip_original_bytes"] = pm.read_bytes(patch_addr, len(NOCLIP_PATCHED_BYTES))
                    self.log(f"  > (PID: {pid}) 找到「穿牆」 @ 0x{patch_addr:X} (狀態: {'已修補' if slot['noclip_is_patched'] else '原始'})")
            except Exception as e: self.log(f"  > (PID: {pid}) 掃描「穿牆」出錯: {e}")

            # --- 4. 掃描完成 ---
            slot["status"] = "已綁定"
            
        except Exception as e:
            self.log(f"掃描時發生嚴重錯誤 (PID: {pid}): {e}")
            slot["status"] = "掃描失敗"
            if slot["pm_handle"]: 
                slot["pm_handle"].close()
                slot["pm_handle"] = None


    # --- (★★★) v2.9: GUI 連動 (核心) ---
    
    def on_selection_change(self):
        """(v2.9) 當 Checkbox 被點擊時, 更新右側顯示"""
        self.update_all_displays()

    def update_all_displays(self):
        """(v2.9) 核心: 更新「複選」視圖 (依據 Checkbox 狀態)"""
        
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            
            is_selected = self.client_selection_vars[i].get() == 1
            is_bound = slot["status"] == "已綁定"
            
            settings_ui = self.setting_widgets[i]
            char_ui_frame = self.char_frames[i] 
            person_vars = self.person_vars[i]
            pet_vars_list = self.pet_vars_list[i]
            
            if is_selected and is_bound:
                # --- 1. 更新「遊戲設置」 (水平) ---
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

                # --- 2. 更新「人寵資料」 (垂直) ---
                char_ui_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=5) 
                char_ui_frame.config(text=slot.get("account_name", f"窗口 {i+1}"))
                
                self._configure_character_widgets(slot.get("char_data_cache"), person_vars)
                
                pet_caches = slot.get("pet_data_cache", [None] * 5)
                for p_idx in range(5):
                    self._configure_pet_widgets(pet_caches[p_idx], pet_vars_list[p_idx], p_idx)
                    
            else:
                # 3. 如果未勾選, 隱藏
                settings_ui["frame"].pack_forget()
                char_ui_frame.grid_forget()
        
        self.tab_frame_settings.inner_frame.event_generate("<Configure>")
        self.tab_frame_char.inner_frame.event_generate("<Configure>")
        
        # (★★★) v3.7 修正: 以下兩行被 *移除* 並 *移動* 到 UI 建立函式中
        # self.tab_frame_char.bind_mouse_wheel(self.tab_frame_char.inner_frame)
        # self.tab_frame_settings.bind_mouse_wheel(self.tab_frame_settings.inner_frame)

            
    # --- 狀態監控 (v2.5) ---

    def _read_big5_string(self, pm, address, byte_length):
        """(v3.5) 輔助函式：讀取 Big5 字串 (傳入 pm)"""
        try:
            bytes_read = pm.read_bytes(address, byte_length)
            bytes_read = bytes_read.split(b'\x00')[0]
            return bytes_read.decode('big5', errors='ignore')
        except Exception as e:
            self.log(f"  > 讀取字串失敗 @ 0x{address:X}: {e}")
            return ""

    def _format_elements(self, earth, water, fire, wind):
        """輔助函式：格式化屬性字串"""
        parts = []
        if earth > 0: parts.append(f"地{earth // 10}")
        if water > 0: parts.append(f"水{water // 10}")
        if fire > 0:  parts.append(f"火{fire // 10}")
        if wind > 0:  parts.append(f"風{wind // 10}")
        return " ".join(parts) if parts else "無"

    def read_character_data(self, i):
        """(v3.5) 讀取所有人物資料 (使用 pm_handle)"""
        slot = self.client_data_slots[i]
        pm = slot["pm_handle"] 
        if not pm: return None
        
        base = slot["module_base"]
        data = {}
        try:
            data["name"] = self._read_big5_string(pm, base + CHAR_NAME_OFFSET, 16)
            data["nickname"] = self._read_big5_string(pm, base + CHAR_NICKNAME_OFFSET, 12)
            reb_val = pm.read_int(base + CHAR_REBIRTH_OFFSET)
            data["rebirth"] = REBIRTH_MAP.get(reb_val, "未知") 
            data["lv"] = pm.read_int(base + CHAR_LV_OFFSET)
            data["hp"] = f"{pm.read_int(base + CHAR_HP_CUR_OFFSET)}/{pm.read_int(base + CHAR_HP_MAX_OFFSET)}"
            data["mp"] = f"{pm.read_int(base + CHAR_MP_CUR_OFFSET)}/{pm.read_int(base + CHAR_MP_MAX_OFFSET)}"
            data["atk"] = pm.read_int(base + CHAR_ATK_OFFSET)
            data["def"] = pm.read_int(base + CHAR_DEF_OFFSET)
            data["agi"] = pm.read_int(base + CHAR_AGI_OFFSET)
            data["charm"] = pm.read_int(base + CHAR_CHARM_OFFSET) 
            e = pm.read_int(base + CHAR_ELEM_EARTH_OFFSET)
            w = pm.read_int(base + CHAR_ELEM_WATER_OFFSET)
            f = pm.read_int(base + CHAR_ELEM_FIRE_OFFSET)
            wi = pm.read_int(base + CHAR_ELEM_WIND_OFFSET)
            data["element"] = self._format_elements(e, w, f, wi) 
            data["vit"] = pm.read_int(base + CHAR_VIT_OFFSET)
            data["str"] = pm.read_int(base + CHAR_STR_OFFSET)
            data["sta"] = pm.read_int(base + CHAR_STA_OFFSET)
            data["spd"] = pm.read_int(base + CHAR_SPD_OFFSET)
            return data
        except Exception as e:
            self.log(f"  > (PID: {slot['pid']}) 讀取人物資料時出錯: {e}")
            return None 

    def _update_element_display(self, frame_widget, element_string):
        """(v2.6) 輔助函式：動態更新屬性標籤 (支援顏色)"""
        for widget in frame_widget.winfo_children():
            widget.destroy()
        
        try:
            bg_color = frame_widget.cget("background")
        except:
            bg_color = self.cget("background") 

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

    def _configure_character_widgets(self, data, person_vars):
        """(v2.7) 輔助函式, 根據 data 設定傳入的 person_vars"""
        if data:
            person_vars["name"].config(text=data.get("name", "錯誤"))
            person_vars["nickname"].config(text=data.get("nickname", "稱號"))
            person_vars["lv"].config(text=data.get("lv", "--"))
            person_vars["hp"].config(text=data.get("hp", "--/--"))
            person_vars["mp"].config(text=data.get("mp", "--/--"))
            person_vars["atk"].config(text=data.get("atk", "--"))
            person_vars["def"].config(text=data.get("def", "--"))
            person_vars["agi"].config(text=data.get("agi", "--"))
            person_vars["vit"].config(text=data.get("vit", "--"))
            person_vars["str"].config(text=data.get("str", "--"))
            person_vars["sta"].config(text=data.get("sta", "--"))
            person_vars["spd"].config(text=data.get("spd", "--"))

            rebirth_text = data.get("rebirth", "未知")
            rebirth_color = REBIRTH_COLOR_MAP.get(rebirth_text, DEFAULT_FG_COLOR)
            person_vars["rebirth"].config(text=rebirth_text, foreground=rebirth_color)

            charm_val = data.get("charm", 0) 
            charm_color = "red" if charm_val <= 60 else DEFAULT_FG_COLOR
            person_vars["charm"].config(text=str(charm_val), foreground=charm_color)

            element_text = data.get("element", "無")
            
            # (★★★) v3.7 修正: 僅在屬性變更時才更新 UI
            if element_text != person_vars.get("last_element"):
                self._update_element_display(person_vars["element_frame"], element_text)
                person_vars["last_element"] = element_text

        else:
            person_vars["name"].config(text="人物")
            person_vars["nickname"].config(text="稱號")
            person_vars["lv"].config(text="--")
            person_vars["hp"].config(text="--/--")
            person_vars["mp"].config(text="--/--")
            person_vars["atk"].config(text="--")
            person_vars["def"].config(text="--")
            person_vars["agi"].config(text="--")
            person_vars["vit"].config(text="--")
            person_vars["str"].config(text="--")
            person_vars["sta"].config(text="--")
            person_vars["spd"].config(text="--")
            
            person_vars["rebirth"].config(text="--", foreground=DEFAULT_FG_COLOR)
            person_vars["charm"].config(text="--", foreground=DEFAULT_FG_COLOR)

            # (★★★) v3.7 修正: 僅在屬性變更時才更新 UI
            if person_vars.get("last_element") != "無":
                self._update_element_display(person_vars["element_frame"], "無")
                person_vars["last_element"] = "無"

    def _read_single_pet(self, pm, pet_base_addr):
        """(v3.2) 修正拼寫錯誤"""
        pet_data = {}
        try:
            pet_data["name"] = self._read_big5_string(pm, pet_base_addr + PET_NAME_REL, 16)
            pet_data["nickname"] = self._read_big5_string(pm, pet_base_addr + PET_NICKNAME_REL, 12)
            
            reb_val = pm.read_int(pet_base_addr + PET_REBIRTH_REL)
            pet_data["rebirth"] = REBIRTH_MAP.get(reb_val, "未知") 
            
            pet_data["lv"] = pm.read_int(pet_base_addr + PET_LV_REL) 
            
            exp_val = pm.read_int(pet_base_addr + PET_EXP_REL)
            lack_val = pm.read_int(pet_base_addr + PET_LACK_REL)
            pet_data["exp"] = exp_val
            
            if lack_val == PET_LACK_EXP_MAX or lack_val == -1:
                pet_data["lack"] = "--"
            else:
                pet_data["lack"] = max(0, lack_val - exp_val) 
            
            pet_data["hp"] = f"{pm.read_int(pet_base_addr + PET_HP_CUR_REL)}/{pm.read_int(pet_base_addr + PET_HP_MAX_REL)}"
            pet_data["atk"] = pm.read_int(pet_base_addr + PET_ATK_REL)
            pet_data["def"] = pm.read_int(pet_base_addr + PET_DEF_REL)
            pet_data["agi"] = pm.read_int(pet_base_addr + PET_AGI_REL)
            pet_data["loyal"] = pm.read_int(pet_base_addr + PET_LOYALTY_REL) 

            e = pm.read_int(pet_base_addr + PET_ELEM_EARTH_REL)
            w = pm.read_int(pet_base_addr + PET_ELEM_WATER_REL)
            f = pm.read_int(pet_base_addr + PET_ELEM_FIRE_REL)
            wi = pm.read_int(pet_base_addr + PET_ELEM_WIND_REL) 
            pet_data["element"] = self._format_elements(e, w, f, wi) 
            
            return pet_data
            
        except Exception as e:
            self.log(f"  > (PID: {pm.process_id}) 讀取寵物 *詳細資料*時出錯: {e}")
            return None 

    def update_and_read_pet_data(self, i):
        """(v3.5) 依賴快取狀態 (使用 pm_handle)"""
        slot = self.client_data_slots[i]
        pm = slot["pm_handle"] 
        if not pm: return
        
        base = slot["module_base"]
        
        pet_1_base_addr = base + PET_1_BASE_OFFSET
        
        for p_idx in range(5):
            current_pet_base_addr = pet_1_base_addr + (p_idx * PET_STRUCT_SIZE)
            exist_addr = current_pet_base_addr + PET_EXIST_REL
            
            cache_is_filled = (slot["pet_data_cache"][p_idx] is not None)
            
            try:
                exist_val = pm.read_uchar(exist_addr)

                if exist_val == 1:
                    slot["pet_data_cache"][p_idx] = self._read_single_pet(pm, current_pet_base_addr)
                
                elif exist_val == 0 and cache_is_filled:
                    self.log(f"  > (PID: {slot['pid']}) 寵物 {p_idx+1} 已移除，清空資料。")
                    slot["pet_data_cache"][p_idx] = None
                
            except Exception as e:
                self.log(f"  > (PID: {slot['pid']}) 讀取寵物 {p_idx+1} *存在狀態*時出錯: {e}")
                slot["pet_data_cache"][p_idx] = None 

    def _clear_pet_vars(self, pet_vars, pet_index):
        """(v2.6) 輔助函式, 重置寵物 widgets"""
        pet_vars["name"].config(text=f"寵物{self.num_to_chinese(pet_index + 1)}")
        pet_vars["nickname"].config(text="")
        pet_vars["lv"].config(text="--")
        pet_vars["exp"].config(text="--")
        pet_vars["lack"].config(text="--")
        pet_vars["hp"].config(text="--/--")
        pet_vars["atk"].config(text="--")
        pet_vars["def"].config(text="--")
        pet_vars["agi"].config(text="--")
        
        pet_vars["loyal"].config(text="--", foreground=DEFAULT_FG_COLOR)
        self._update_element_display(pet_vars["element_frame"], "無")
        pet_vars["rebirth"].config(text="--", foreground=DEFAULT_FG_COLOR)

    def _configure_pet_widgets(self, data, pet_vars, p_idx):
        """(v3.2) 修正拼寫錯誤"""
        if data:
            pet_vars["name"].config(text=data.get("name", "錯誤"))
            pet_vars["nickname"].config(text=data.get("nickname", ""))
            pet_vars["lv"].config(text=data.get("lv", "--"))
            pet_vars["exp"].config(text=data.get("exp", "--"))
            pet_vars["lack"].config(text=data.get("lack", "--"))
            pet_vars["hp"].config(text=data.get("hp", "--/--"))
            pet_vars["atk"].config(text=data.get("atk", "--"))
            pet_vars["def"].config(text=data.get("def", "--"))
            pet_vars["agi"].config(text=data.get("agi", "--"))

            rebirth_text = data.get("rebirth", "未知")
            rebirth_color = REBIRTH_COLOR_MAP.get(rebirth_text, DEFAULT_FG_COLOR)
            pet_vars["rebirth"].config(text=rebirth_text, foreground=rebirth_color)

            loyal_val = data.get("loyal", 100) 
            loyal_color = "red" if loyal_val <= 20 else DEFAULT_FG_COLOR
            pet_vars["loyal"].config(text=str(loyal_val), foreground=loyal_color)

            element_text = data.get("element", "無")
            
            # (★★★) v3.7 修正: 僅在屬性變更時才更新 UI
            if element_text != pet_vars.get("last_element"):
                self._update_element_display(pet_vars["element_frame"], element_text)
                pet_vars["last_element"] = element_text
            
        else:
            # (★★★) v3.7 修正: 僅在屬性變更時才更新 UI
            if pet_vars.get("last_element") is not None:
                self._clear_pet_vars(pet_vars, p_idx)
                pet_vars["last_element"] = None # 重置快取

    def update_client_list_display(self, i):
        """(★★★) v3.6: 讀取狀態 (移除 psutil.pid_exists)"""
        slot = self.client_data_slots[i]
        checkbox = self.client_checkboxes[i] 

        if not slot["pid"] or not slot["module_base"] or not slot["pm_handle"]:
            checkbox.config(text=f"窗口 {i+1}: 未綁定", state="disabled", fg="grey")
            slot["char_data_cache"] = None 
            slot["pet_data_cache"] = [None] * 5
            slot["account_name"] = "" 
            self.client_selection_vars[i].set(0)
            return "unbound"

        try:
            # (★★★) v3.6: 移除 psutil.pid_exists() 
            # if not psutil.pid_exists(slot["pid"]):
            #     raise Exception(f"PID {slot['pid']} 不存在")
                
            pm = slot["pm_handle"] 
            checkbox.config(fg="green", state="normal") 
            
            # (★★★) v3.6: 依賴此 read 操作來觸發 except (如果進程已關閉)
            state_addr = slot["module_base"] + GAME_STATE_OFFSET
            game_state = pm.read_int(state_addr)
            
            new_display_text = f"狀態: {game_state}" 
            
            if game_state in (1, 2):
                new_display_text = "登入中"
                slot["char_data_cache"] = None 
                slot["pet_data_cache"] = [None] * 5
            elif game_state == 3:
                new_display_text = "選擇角色"
                slot["char_data_cache"] = None 
                slot["pet_data_cache"] = [None] * 5
            elif game_state > 3:
                try:
                    account_addr = slot["module_base"] + ACCOUNT_STRING_OFFSET
                    raw_string = pm.read_string(account_addr, 100) 
                    account_name = raw_string.split("www.longzor")[0]
                    if not account_name: account_name = "登入完成" 
                    new_display_text = account_name
                except Exception as e_str:
                    self.log(f"  > (PID: {slot['pid']}) 讀取帳號字串失敗: {e_str}")
                    new_display_text = "登入完成"
                
                slot["char_data_cache"] = self.read_character_data(i)
                self.update_and_read_pet_data(i) 
            
            checkbox.config(text=new_display_text) 
            slot["account_name"] = new_display_text 
            
            return game_state 

        except Exception as e:
            self.log(f"監控窗口 {i+1} (PID: {slot['pid']}) 時出錯: {e}")
            checkbox.config(text=f"窗口 {i+1}: 未綁定", state="disabled", fg="grey") 
            
            # (★★★) v3.5: 關閉失效的句柄
            if slot["pm_handle"]:
                try:
                    slot["pm_handle"].close()
                except Exception as e_close:
                    self.log(f"  > 關閉失效句柄 (PID: {slot['pid']}) 時出錯: {e_close}")
            
            self.client_data_slots[i] = self.create_empty_slot_data()
            self.client_selection_vars[i].set(0) 
            
            return "unbound"


    def start_monitoring_loop(self):
        """啟動監控迴圈 (如果尚未啟動)"""
        # (★★★) v3.6: 檢查 "不刷新" 選項
        if self.get_poll_interval_ms() is None:
            self.log("--- 監控未啟動 (設定為 '不刷新') ---")
            return
        
        if self.monitoring_active:
            return
        self.monitoring_active = True
        self.log("--- 開始狀態監控 ---")
        self.monitor_game_states()

    def monitor_game_states(self):
        """(v3.4) 核心監控函式 (使用刷新頻率)"""
        if not self.monitoring_active:
            self.log("--- 監控已停止 ---")
            return
        
        base_poll_interval = self.get_poll_interval_ms()
        
        if base_poll_interval is None:
            self.monitoring_active = False
            self.log("--- 監控已暫停 (不刷新) ---")
            return 
        
        next_poll_interval = base_poll_interval 
        is_logging_in = False 
        
        for i in range(MAX_CLIENTS):
            game_state = self.update_client_list_display(i) 
            if game_state == "unbound": continue 
            if game_state in (1, 2, 3) or not isinstance(game_state, int):
                is_logging_in = True
        
        if is_logging_in and base_poll_interval > 1000:
            next_poll_interval = 1000
        
        self.update_all_displays()
        
        active_clients_still_bound = any(s["pid"] is not None for s in self.client_data_slots)

        if active_clients_still_bound:
            self.after(next_poll_interval, self.monitor_game_states)
        else:
            self.log("--- 所有客戶端均已解綁，停止監控。 ---")
            self.monitoring_active = False

    def get_poll_interval_ms(self):
        """(v3.4) 根據下拉選單A轉換刷新頻率 (ms)"""
        value = self.refresh_rate_var.get()
        mapping = {
            '0.5s': 500,
            '1s': 1000,
            '3s': 3000,
            '5s': 5000,
            '10s': 10000,
            '60s': 60000,
            '不刷新': None
        }
        return mapping.get(value, 3000) # 預設 3s

    def on_refresh_rate_change(self, event=None):
        """(v3.4) 當刷新頻率改變時呼叫"""
        new_rate = self.refresh_rate_var.get()
        self.log(f"刷新頻率變更為: {new_rate}")
        
        if not self.monitoring_active and new_rate != '不刷新':
            self.start_monitoring_loop()

    # --- (v3.5) 核心功能：執行修補 (使用 pm_handle) ---
    
    def on_toggle_walk(self, client_index):
        """(v3.5) 快速行走 (使用 pm_handle)"""
        index = client_index
            
        slot = self.client_data_slots[index]
        pm = slot["pm_handle"]
        addr, orig_byte = slot["walk_address"], slot["walk_original_byte"]
        
        if pm is None or addr is None or orig_byte is None:
            self.log(f"窗口 {index+1} 錯誤：行走功能未綁定。")
            self.setting_widgets[index]["vars"]["fast_walk"].set(not self.setting_widgets[index]["vars"]["fast_walk"].get())
            return
            
        is_checked = self.setting_widgets[index]["vars"]["fast_walk"].get()
        target_byte = WALK_PATCHED_BYTE if is_checked else orig_byte
        action_text = "啟用" if is_checked else "還原"
        self.log(f"窗口 {index+1}: 快速行走 {action_text}...")
        success = self.perform_write_byte(pm, addr, target_byte)
        if success: slot["walk_is_patched"] = is_checked
        else:
            self.log("操作失敗！")
            self.setting_widgets[index]["vars"]["fast_walk"].set(not is_checked)

    def on_toggle_speed(self, client_index):
        """(v3.5) 遊戲加速 (使用 pm_handle)"""
        index = client_index
            
        slot = self.client_data_slots[index]
        pm = slot["pm_handle"]
        
        if pm is None or not slot["speed_address_1"] or not slot["speed_original_bytes_1"]:
            self.log(f"窗口 {index+1} 錯誤：加速功能未綁定。")
            self.setting_widgets[index]["vars"]["game_speed"].set(not self.setting_widgets[index]["vars"]["game_speed"].get())
            return
            
        is_checked = self.setting_widgets[index]["vars"]["game_speed"].get()
        action_text = "啟用 (NOP)" if is_checked else "還原 (ADD)"
        self.log(f"窗口 {index+1}: 遊戲加速 {action_text}...")
        if is_checked: target1, target2 = NOP_PATCH, NOP_PATCH
        else: target1, target2 = slot["speed_original_bytes_1"], slot["speed_original_bytes_2"]
        s1 = self.perform_write_bytes(pm, slot["speed_address_1"], target1)
        s2 = self.perform_write_bytes(pm, slot["speed_address_2"], target2)
        if s1 and s2: slot["speed_is_patched"] = is_checked
        else:
            self.log("操作失敗！")
            self.setting_widgets[index]["vars"]["game_speed"].set(not is_checked)

    def on_toggle_noclip(self, client_index):
        """(v3.5) 穿牆行走 (使用 pm_handle)"""
        index = client_index
            
        slot = self.client_data_slots[index]
        pm = slot["pm_handle"]
        addr, orig_bytes = slot["noclip_address"], slot["noclip_original_bytes"]
        
        if pm is None or addr is None or orig_bytes is None:
            self.log(f"窗口 {index+1} 錯誤：穿牆功能未綁定。")
            self.setting_widgets[index]["vars"]["no_clip"].set(not self.setting_widgets[index]["vars"]["no_clip"].get())
            return
            
        is_checked = self.setting_widgets[index]["vars"]["no_clip"].get()
        target_bytes = NOCLIP_PATCHED_BYTES if is_checked else orig_bytes
        action_text = "啟用" if is_checked else "還原"
        self.log(f"窗口 {index+1}: 穿牆行走 {action_text}...")
        success = self.perform_write_bytes(pm, addr, target_bytes)
        if success: slot["noclip_is_patched"] = is_checked
        else:
            self.log("操作失敗！")
            self.setting_widgets[index]["vars"]["no_clip"].set(not is_checked)

    def on_toggle_hide(self, client_index):
        """(v2.9) 隱藏石器 (純複選) - 此函式不需 pm_handle"""
        index = client_index
            
        slot = self.client_data_slots[index]
        hwnd = slot["hwnd"]
        if hwnd is None:
            self.log(f"窗口 {index+1} 錯誤：未找到窗口句柄(HWND)。")
            return
            
        is_checked = self.setting_widgets[index]["vars"]["hide_sa"].get()
        command = SW_HIDE if is_checked else SW_SHOW
        action_text = "隱藏" if is_checked else "顯示"
        self.log(f"窗口 {index+1}: {action_text}...")
        try:
            ctypes.windll.user32.ShowWindow(hwnd, command)
            slot["is_hidden"] = is_checked
        except Exception as e:
            self.log(f"隱藏窗口時出錯: {e}")
            self.setting_widgets[index]["vars"]["hide_sa"].set(not is_checked)

    def perform_write_byte(self, pm, patch_address, target_byte):
        """(v3.5) 傳入 pm 物件, 而非 pid"""
        try:
            pm.write_uchar(patch_address, target_byte)
            written_byte = pm.read_bytes(patch_address, 1)[0]
            if written_byte == target_byte:
                self.log(f"  > 成功! (PID: {pm.process_id}) @ 0x{patch_address:X} -> 0x{target_byte:X}")
                return True
            else:
                self.log(f"  > 失敗! (PID: {pm.process_id}) 寫入後驗證失敗。")
                return False
        except Exception as e:
            self.log(f"寫入時出錯 (PID: {pm.process_id}): {e}")
            # (★★★) v3.6: 這裡*不*檢查 psutil.pid_exists, 讓它自然失敗
            return False
            
    def perform_write_bytes(self, pm, patch_address, target_bytes):
        """(v3.5) 傳入 pm 物件, 而非 pid"""
        try:
            pm.write_bytes(patch_address, target_bytes, len(target_bytes))
            written_bytes = pm.read_bytes(patch_address, len(target_bytes))
            if written_bytes == target_bytes:
                self.log(f"  > V成功! (PID: {pm.process_id}) @ 0x{patch_address:X} -> {target_bytes.hex()}")
                return True
            else:
                self.log(f"  > 失敗! (PID: {pm.process_id}) 寫入後驗證失敗。")
                return False
        except Exception as e:
            self.log(f"寫入多位元組時出錯 (PID: {pm.process_id}): {e}")
            # (★★★) v3.6: 這裡*不*檢查 psutil.pid_exists
            return False

    # (★★★) v3.1: 新增: 單擊右鍵 (激活)
    def on_client_right_click_single(self, event, client_index):
        slot = self.client_data_slots[client_index]
        if slot["status"] != "已綁定" or slot["hwnd"] is None:
            return
        
        hwnd = slot["hwnd"]
        
        try:
            self.log(f"窗口 {client_index+1}: 激活")
            # 1. 如果已縮小, 先還原
            if ctypes.windll.user32.IsIconic(hwnd):
                ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
            
            # 2. 設為前景 (這在某些 Windows 版本可能失效, 但已是標準做法)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        
        except Exception as e:
            self.log(f"右鍵單擊窗口 {client_index+1} 時出錯: {e}")

    # (★★★) v3.1: 新增: 雙擊右鍵 (縮小)
    def on_client_right_click_double(self, event, client_index):
        slot = self.client_data_slots[client_index]
        if slot["status"] != "已綁定" or slot["hwnd"] is None:
            return
        
        hwnd = slot["hwnd"]
        
        try:
            self.log(f"窗口 {client_index+1}: 縮小")
            ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE) 
        
        except Exception as e:
            self.log(f"右鍵雙擊窗口 {client_index+1} 時出錯: {e}")

    def on_closing(self):
        """(v3.5) 關閉時 (明確關閉句柄)"""
        self.monitoring_active = False 
        self.log("正在關閉程式... (嘗試還原所有補丁並關閉句柄)")
        
        for i in range(MAX_CLIENTS):
            slot = self.client_data_slots[i]
            pm = slot["pm_handle"]
            
            # (★★★) v3.6: 檢查句柄是否仍然有效, 使用 read 測試
            if pm:
                try:
                    # 輕量級測試
                    pm.read_int(slot["module_base"]) 
                except Exception:
                    self.log(f"窗口 {i+1} (PID {slot['pid']}) 句柄已失效, 跳過還原。")
                    pm.close() # 關閉失效的句柄
                    continue # 繼續下一個
            else:
                continue # pm is None, 
            
            self.log(f"正在還原窗口 {i+1} (PID: {slot['pid']})...")
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
            except Exception as e:
                self.log(f"還原 PID {slot['pid']} 時出錯: {e}")
            
            try:
                pm.close()
                self.log(f"  > (PID: {slot['pid']}) 句柄已關閉。")
            except Exception as e:
                self.log(f"關閉句柄 (PID: {slot['pid']}) 時出錯: {e}")

        self.destroy()

# --- 程式主體 ---
if __name__ == "__main__":
    app = DSAHelperApp()
    app.mainloop()