# constants.py
# 儲存靜態記憶體位址、偏移量、AOB 特徵碼和對應表

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

# --- 寵物資料 Offsets ---
PET_1_BASE_OFFSET = 0x104252A0      # 寵物 1 結構的基址
PET_STRUCT_SIZE = 0xFE8             # 寵物結構大小間距

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
PET_NAME_REL = 0x4C                 
PET_NICKNAME_REL = 0x5D             
PET_EXIST_REL = 0x6E                

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
    "轉生叁": "blue",
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

# --- 寵物狀態 Offsets ---
CHAR_BATTLE_PET_OFFSET = 0x1041E352    # 戰鬥
PET_WAIT_FLAGS_BASE    = 0x1041E354    # 等待1
CHAR_MAIL_PET_OFFSET   = 0x1041E35E    # 郵件
CHAR_RIDING_PET_OFFSET = 0x104218B4    # 騎寵

# --- 道具列表 Offsets (v4.9 新增) ---
# 基址: sadsa.exe + 0x1041F74C
ITEM_BASE_OFFSET = 0x1041F74C
ITEM_STRUCT_SIZE = 0x234       # 道具間距

# 相對偏移量 (Relative Offsets)
# 計算方式: 目標位址 - 基址 (0x1041F74C)
ITEM_STACK_REL = 0x0           # 1041F74C - 1041F74C = 0
ITEM_EXIST_REL = 0xD0          # 1041F81C - 1041F74C = D0
ITEM_NAME_REL  = 0xDA          # 1041F826 - 1041F74C = DA
ITEM_DESC_REL  = 0x134         # 1041F880 - 1041F74C = 134
ITEM_DUR_REL   = 0x1DD         # 1041F929 - 1041F74C = 1DD

# --- 常數補充 (道具與裝備) ---
# 記憶體讀取設定
ITEM_BASE_OFFSET = 0x1041F74C
ITEM_STRUCT_SIZE = 0x234
ITEM_STACK_REL = 0x0
ITEM_EXIST_REL = 0xD0
ITEM_NAME_REL  = 0xDA
ITEM_DESC_REL  = 0x134
ITEM_DUR_REL   = 0x1DD

# 裝備對應表 (Key=記憶體相對Index, Value=顯示前綴)
# 依據您的說明：偏移-1~-9 依序為 手套、鞋子、副手、腰帶、左飾、右飾、主手、身體、頭部
EQUIP_MAPPING = {
    -9: "頭部",
    -8: "身體",
    -5: "左飾", # 注意：這裡我依照常見邏輯排序，稍後 UI 會依照您指定的順序顯示
    -6: "右飾",
    -7: "主手",
    -3: "副手",
    -1: "手套",
    -4: "腰帶",
    -2: "鞋子"
}

# UI 顯示順序 (依照您要求的顯示順序)
EQUIP_DISPLAY_ORDER = [-9, -8, -5, -6, -7, -3, -1, -4, -2]

# constants.py (新增部分)

# --- 道具名稱顏色規則 (Item Color Rules) ---
# 格式: "顏色代碼": ["關鍵字1", "關鍵字2", ...]
# 說明: 程式會優先檢查前面的顏色，一旦匹配到關鍵字就會套用。
# 顏色參考:
#   綠色: #00c400
#   橙色: #bf642f
#   黃色: #FFFF00
#   藍色: #4850b8
#   米色: #cebc86 (通常用於傳說/特殊道具)

ITEM_COLOR_RULES = {
    "#048E04": ["月神", "青蛇", "蟒蛇", "靈蛇", "響尾蛇", "雙頭蛇","飛翔", "洛克亞", "海藍", "奇普", "魔魂", "凱亞", 
                "莫奇", "威姆", "薩美", "瑪拉", "星光", "月光", "拉佛", "巨石", "龍骨",
                "夜魂", "冰鍊", "雷甲", "薩貝多", "天狼", "碧晶", "冰鍊", "枯骨", "寶斯",
                "夢魔", "硬甲"],
    "#FF8000": ["年獸", "月兔", "端午", "神兵", "彤弓","艾草","菖蒲","聖蛇","冒險者"],
    "#F30303": ["戰績","來吉卡","VIP","聲望","禮盒"],
    "#00CCFF": ["果實","水晶等值卷","珊瑚裝","蒙那工具包","空間石","始祖鳥的蛋",
                "指引地圖","蝸牛卵","月神之淚","工匠之石","磷石","鑄造石"],
    "#A334EE": ["白狼之眼","雙蛇","五素","罐頭","領養",
                "激化激素","極品人","淚之石","英雄","瑪蕾","特效藥",
                "犬神","巨人","破碎能量","騎乘", "馴騎手戒","合成手環 10","靈力鎧",
                "柳牙","雪淚","陽熾","疾翎","流星","雙頭","金蟒","褐那","溫特","洛炎","碧華","參觀券"],
                }

# 預設文字顏色 (若無匹配)
DEFAULT_ITEM_COLOR = "black"

# constants.py (新增)
# 戰鬥資訊
BATTLE_STRING_OFFSET = 0x1E410D  # (修正) 新的戰鬥數據偏移量
BATTLE_STATE_ID = 10             # 戰鬥中的狀態碼
# --- 戰鬥狀態 UI 顯示順序 (Battle UI Order) ---
# 左方隊伍 (由上至下)
BATTLE_LEFT_ORDER = [14, 19, 12, 17, 10, 15, 11, 16, 13, 18]
# 右方隊伍 (由上至下)
BATTLE_RIGHT_ORDER = [9, 4, 7, 2, 5, 0, 6, 1, 8, 3]
