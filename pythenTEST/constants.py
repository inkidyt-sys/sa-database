# constants.py
# 儲存所有靜態記憶體位址、偏移量、AOB 特徵碼和對應表

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

# --- 寵物資料 Offsets (v2.4 Struct 邏輯修正) ---
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

# 顏色定義
REBIRTH_COLOR_MAP = {
    "未轉生": "black",
    "轉生壹": "#E5C100", 
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
    "風": "#E5C100"
}
DEFAULT_FG_COLOR = "black"

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
SW_MINIMIZE = 6
SW_RESTORE = 9