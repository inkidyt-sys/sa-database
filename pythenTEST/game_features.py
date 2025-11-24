# game_features.py
# 負責執行記憶體修改與功能開關

import ctypes
from constants import *

def toggle_memory_feature(slot, feature_key, addr_key, orig_bytes_key, patch_bytes, is_enable, is_byte_mode=False):
    """通用記憶體開關函式"""
    pm = slot.get("pm_handle")
    addr = slot.get(addr_key)
    
    if not pm or not addr: return False

    try:
        if is_enable:
            target = patch_bytes
        else:
            target = slot.get(orig_bytes_key)
            if target is None: return False # 無原始數據，無法還原

        if is_byte_mode:
            # 單字節模式 (例如: 穿牆/行走)
            # patch_bytes 傳入時可能是 int 或 bytes，需統一
            val = target if isinstance(target, int) else target[0]
            pm.write_uchar(addr, val)
        else:
            # 多字節模式
            pm.write_bytes(addr, target, len(target))
            
        slot[feature_key] = is_enable
        return True
    except Exception as e:
        print(f"Feature Error: {e}")
        return False

def toggle_speed(slot, is_enable):
    """特例：加速需要修改兩個地址"""
    pm = slot.get("pm_handle")
    a1, a2 = slot.get("speed_address_1"), slot.get("speed_address_2")
    
    if not pm or not a1: return False

    try:
        if is_enable:
            t1, t2 = NOP_PATCH, NOP_PATCH
        else:
            t1, t2 = slot.get("speed_original_bytes_1"), slot.get("speed_original_bytes_2")
            if not t1: return False

        pm.write_bytes(a1, t1, 6)
        pm.write_bytes(a2, t2, 6)
        slot["speed_is_patched"] = is_enable
        return True
    except:
        return False

def toggle_hide_window(slot, is_hide):
    """隱藏/顯示視窗"""
    hwnd = slot.get("hwnd")
    if not hwnd: return False
    try:
        cmd = SW_HIDE if is_hide else SW_SHOW
        ctypes.windll.user32.ShowWindow(hwnd, cmd)
        slot["is_hidden"] = is_hide
        return True
    except:
        return False