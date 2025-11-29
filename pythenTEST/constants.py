# constants.py
# 靜態記憶體位址、偏移量、AOB 特徵碼和對應表

PROCESS_NAME = "sadsa.exe"
MAX_CLIENTS = 6

# --- 狀態/帳號 Offsets ---
GAME_STATE_OFFSET = 0x1042EAE4
ACCOUNT_STRING_OFFSET = 0x1DE37C

# --- 人物資料 Offsets ---
CHAR_NAME_OFFSET = 0x1041E318
CHAR_NICKNAME_OFFSET = 0x1041E329
CHAR_REBIRTH_OFFSET = 0x10421854
CHAR_LV_OFFSET = 0x1041E2E0
CHAR_HP_CUR_OFFSET = 0x1041E2B8
CHAR_HP_MAX_OFFSET = 0x1041E2BC
CHAR_MP_CUR_OFFSET = 0x1041E2C0
CHAR_MP_MAX_OFFSET = 0x1041E2C4
CHAR_ATK_OFFSET = 0x1041E2E4
CHAR_DEF_OFFSET = 0x1041E2E8
CHAR_AGI_OFFSET = 0x1041E2EC
CHAR_CHARM_OFFSET = 0x1041E2F0
CHAR_ELEM_EARTH_OFFSET = 0x1041E2F8
CHAR_ELEM_WATER_OFFSET = 0x1041E2FC
CHAR_ELEM_FIRE_OFFSET = 0x1041E300
CHAR_ELEM_WIND_OFFSET = 0x1041E304
CHAR_VIT_OFFSET = 0x1041E2C8
CHAR_STR_OFFSET = 0x1041E2CC
CHAR_STA_OFFSET = 0x1041E2D0
CHAR_SPD_OFFSET = 0x1041E2D4
CHAR_GOLD_OFFSET = 0x1041E308  # [新增] 石幣記憶體位置

# --- 寵物資料 Offsets ---
PET_1_BASE_OFFSET = 0x104252A0
PET_STRUCT_SIZE = 0xFE8
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

# --- 寵物狀態 Offsets ---
CHAR_BATTLE_PET_OFFSET = 0x1041E352
PET_WAIT_FLAGS_BASE    = 0x1041E354
CHAR_MAIL_PET_OFFSET   = 0x1041E35E
CHAR_RIDING_PET_OFFSET = 0x104218B4

# --- 道具與裝備 Offsets ---
ITEM_BASE_OFFSET = 0x1041F74C
ITEM_STRUCT_SIZE = 0x234
ITEM_STACK_REL = 0x0
ITEM_EXIST_REL = 0xD0
ITEM_NAME_REL  = 0xDA
ITEM_DESC_REL  = 0x134
ITEM_DUR_REL   = 0x1DD

# --- 戰鬥資訊 ---
BATTLE_STRING_OFFSET = 0x1E410D
BATTLE_STATE_ID = 10
BATTLE_ROUND_OFFSET = 0x1E9130  # [新增] 回合數記憶體位置

# --- 特徵碼 (AOB) ---
AOB_PATTERN_WALK = rb"\x0F\x2F\x45\xEC..\xF3\x0F\x10\x45\xF4"
WALK_PATCH_OFFSET = 4
WALK_PATCHED_BYTE = 0x74

AOB_PATTERN_SPEED_1_ORIGINAL = rb"\x8B\x95\xD8\xFB\xFF\xFF\x03\x15....\x89\x95\xA4\xFB\xFF\xFF"
AOB_PATTERN_SPEED_1_PATCHED  = rb"\x8B\x95\xD8\xFB\xFF\xFF\x90\x90\x90\x90\x90\x90\x89\x95\xA4\xFB\xFF\xFF"
AOB_PATTERN_SPEED_2_ORIGINAL = rb"\x8B\x85\xD8\xFB\xFF\xFF\x03\x05....\x89\x85\xB4\xFB\xFF\xFF"
AOB_PATTERN_SPEED_2_PATCHED  = rb"\x8B\x85\D8\xFB\xFF\xFF\x90\x90\x90\x90\x90\x90\x89\x85\xB4\xFB\xFF\xFF"
SPEED_AOB_OFFSET = 6
NOP_PATCH = b"\x90\x90\x90\x90\x90\x90"

AOB_PATTERN_NOCLIP_ORIGINAL = rb"\x83\xFA\x01\x75.\xB8\x01\x00\x00\x00\xEB.\x33\xC0\x8B\xE5\x5D\xC3"
AOB_PATTERN_NOCLIP_PATCHED  = rb"\x83\xFA\x01\x75.\xB8\x00\x00\x00\x00\xEB.\x33\xC0\x8B\xE5\x5D\xC3"
NOCLIP_PATCH_OFFSET = 5
NOCLIP_PATCHED_BYTES = b"\xB8\x00\x00\x00\x00"

# WinAPI Constants
SW_HIDE = 0
SW_SHOW = 5
SW_MINIMIZE = 6
SW_RESTORE = 9

# --- 對應表與設定 ---
REBIRTH_MAP = {
    0: "未轉生", 1: "轉生壹", 2: "轉生貳",
    3: "轉生叁", 4: "轉生肆", 5: "轉生伍", 6: "轉生陸"
}
PET_LACK_EXP_MAX = 4294967295

REBIRTH_COLOR_MAP = {
    "未轉生": "black", "轉生壹": "#E5C100", "轉生貳": "#35B315",
    "轉生叁": "blue", "轉生肆": "red", "轉生伍": "purple", "轉生陸": "#8F8C8C"
}
ELEMENT_COLOR_MAP = {
    "地": "green", "水": "blue", "火": "red", "風": "#E5C100"
}
DEFAULT_FG_COLOR = "black"
DEFAULT_ITEM_COLOR = "black"

# 裝備欄位 (Key=相對Index)
EQUIP_MAPPING = {
    -9: "頭部", -8: "身體", -5: "左飾", -6: "右飾",
    -7: "主手", -3: "副手", -1: "手套", -4: "腰帶", -2: "鞋子"
}
EQUIP_DISPLAY_ORDER = [-9, -8, -5, -6, -7, -3, -1, -4, -2]

# 戰鬥隊伍順序
BATTLE_LEFT_ORDER = [14, 19, 12, 17, 10, 15, 11, 16, 13, 18]
BATTLE_RIGHT_ORDER = [9, 4, 7, 2, 5, 0, 6, 1, 8, 3]

# 道具上色規則
ITEM_COLOR_RULES = {
    "#048E04": ["月神", "青蛇", "蟒蛇", "靈蛇", "響尾蛇", "雙頭蛇","飛翔", "洛克亞", "海藍", "奇普", "魔魂", "凱亞", 
                "莫奇", "威姆", "薩美", "瑪拉", "星光", "月光", "拉佛", "巨石", "龍骨",
                "夜魂", "冰鍊", "雷甲", "薩貝多", "天狼", "碧晶", "冰鍊", "枯骨", "寶斯", "夢魔", "硬甲"],
    "#FF5900": ["年獸", "月兔", "端午", "神兵", "彤弓","艾草","菖蒲","聖蛇","冒險者","聖衣","朗基努斯","嘆息之牆"],
    "#F30303": ["戰績","來吉卡","VIP","聲望","禮盒"],
    "#0699BD": ["果實","水晶等值卷","珊瑚裝","蒙那工具包","空間石","始祖鳥的蛋",
                "指引地圖","蝸牛卵","月神之淚","工匠之石","磷石","鑄造石"],
    "#7E08CC": ["白狼之眼","雙蛇","五素","罐頭","領養","激化激素","極品人","淚之石","英雄","瑪蕾","特效藥",
                "犬神","巨人","破碎能量","騎乘", "馴騎手戒","合成手環 10","靈力鎧",
                "柳牙","雪淚","陽熾","疾翎","流星","雙頭","金蟒","褐那","溫特","洛炎","碧華","參觀券"],
}