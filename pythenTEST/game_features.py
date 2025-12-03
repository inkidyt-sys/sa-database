# game_features.py
# 負責執行記憶體修改與功能開關

import ctypes
from constants import *
from logger import logger

def toggle_memory_feature(slot, feature_key, addr_key, orig_bytes_key, patch_bytes, is_enable, is_byte_mode=False):
    """通用記憶體開關函式"""
    pm = slot.get("pm_handle")
    addr = slot.get(addr_key)
    
    if not pm or not addr: 
        logger.warning(f"Feature {feature_key}: no pm_handle or address")
        return False

    try:
        if is_enable:
            target = patch_bytes
        else:
            target = slot.get(orig_bytes_key)
            if target is None: 
                logger.warning(f"Feature {feature_key}: no original bytes to restore")
                return False

        if is_byte_mode:
            # 單字節模式 (例如: 穿牆/行走)
            # patch_bytes 傳入時可能是 int 或 bytes，需統一
            val = target if isinstance(target, int) else target[0]
            pm.write_uchar(addr, val)
            logger.info(f"Feature {feature_key}: write_uchar @ 0x{addr:X} = 0x{val:02X}")
        else:
            # 多字節模式
            pm.write_bytes(addr, target, len(target))
            logger.info(f"Feature {feature_key}: write_bytes @ 0x{addr:X} ({len(target)} bytes)")
            
        slot[feature_key] = is_enable
        return True
    except Exception as e:
        logger.error(f"Feature {feature_key} toggle failed: {e}")
        return False

def toggle_speed(slot, is_enable):
    """特例：加速需要修改兩個地址"""
    pm = slot.get("pm_handle")
    a1, a2 = slot.get("speed_address_1"), slot.get("speed_address_2")
    
    if not pm or not a1:
        logger.warning("Speed feature: missing addresses")
        return False

    try:
        if is_enable:
            t1, t2 = NOP_PATCH, NOP_PATCH
        else:
            t1, t2 = slot.get("speed_original_bytes_1"), slot.get("speed_original_bytes_2")
            if not t1:
                logger.warning("Speed feature: no original bytes")
                return False

        pm.write_bytes(a1, t1, 6)
        pm.write_bytes(a2, t2, 6)
        slot["speed_is_patched"] = is_enable
        logger.info(f"Speed feature: {'enabled' if is_enable else 'disabled'}")
        return True
    except Exception as e:
        logger.error(f"Speed toggle failed: {e}")
        return False

def toggle_hide_window(slot, is_hide):
    """隱藏/顯示視窗"""
    hwnd = slot.get("hwnd")
    if not hwnd:
        logger.warning("Hide window: no hwnd")
        return False
    try:
        cmd = SW_HIDE if is_hide else SW_SHOW
        ctypes.windll.user32.ShowWindow(hwnd, cmd)
        slot["is_hidden"] = is_hide
        logger.info(f"Window visibility: {'hidden' if is_hide else 'shown'}")
        return True
    except Exception as e:
        logger.error(f"Hide window failed: {e}")
        return False