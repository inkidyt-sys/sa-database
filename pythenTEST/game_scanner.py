# game_scanner.py
# 負責尋找遊戲視窗與記憶體特徵掃描

import ctypes
import ctypes.wintypes
import psutil
import pymem
import pymem.pattern
from constants import *

def find_game_windows():
    """尋找所有符合 PROCESS_NAME 的遊戲視窗"""
    wins = []
    def cb(hwnd, _):
        if ctypes.windll.user32.IsWindowVisible(hwnd) and ctypes.windll.user32.GetWindowTextLengthW(hwnd) > 0:
            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                try:
                    if psutil.Process(pid.value).name().lower() == PROCESS_NAME.lower():
                        wins.append((hwnd, pid.value))
                except: pass
        return True
    ctypes.windll.user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)(cb), 0)
    return wins

def scan_slot(slot):
    """對單一 Slot 進行記憶體掃描與綁定"""
    try:
        pm = pymem.Pymem(slot["pid"])
        slot["pm_handle"] = pm
        mod = pymem.process.module_from_name(pm.process_handle, PROCESS_NAME)
        if not mod: raise Exception("Module not found")
        slot["module_base"] = mod.lpBaseOfDll
        
        # 1. 掃描行走
        _scan_pattern(slot, mod, AOB_PATTERN_WALK, WALK_PATCH_OFFSET, "walk", 1)
        
        # 2. 掃描加速
        _scan_speed(slot, mod)
        
        # 3. 掃描穿牆 (含備用特徵)
        _scan_pattern(slot, mod, AOB_PATTERN_NOCLIP_ORIGINAL, NOCLIP_PATCH_OFFSET, "noclip", 
                      len(NOCLIP_PATCHED_BYTES), AOB_PATTERN_NOCLIP_PATCHED)
        
        slot["status"] = "已綁定"
        return True
    except:
        slot["status"] = "掃描失敗"
        if slot.get("pm_handle"): 
            try: slot["pm_handle"].close_process()
            except: pass
        slot["pm_handle"] = None
        return False

def _scan_pattern(slot, mod, pattern, offset, key_prefix, size, alt_pattern=None):
    pm = slot["pm_handle"]
    try:
        addr = pymem.pattern.pattern_scan_module(pm.process_handle, mod, pattern)
        patched = False
        if not addr and alt_pattern:
            addr = pymem.pattern.pattern_scan_module(pm.process_handle, mod, alt_pattern)
            patched = True
        
        if addr:
            final = addr + offset
            slot[f"{key_prefix}_address"] = final
            slot[f"{key_prefix}_is_patched"] = patched
            if not patched:
                data = pm.read_bytes(final, size)
                slot[f"{key_prefix}_original_byte" if size==1 else f"{key_prefix}_original_bytes"] = data[0] if size==1 else data
    except: pass

def _scan_speed(slot, mod):
    pm = slot["pm_handle"]
    try:
        a1 = pymem.pattern.pattern_scan_module(pm.process_handle, mod, AOB_PATTERN_SPEED_1_ORIGINAL)
        a2 = pymem.pattern.pattern_scan_module(pm.process_handle, mod, AOB_PATTERN_SPEED_2_ORIGINAL)
        patched = False
        if not a1:
            a1 = pymem.pattern.pattern_scan_module(pm.process_handle, mod, AOB_PATTERN_SPEED_1_PATCHED)
            a2 = pymem.pattern.pattern_scan_module(pm.process_handle, mod, AOB_PATTERN_SPEED_2_PATCHED)
            patched = True
        
        if a1 and a2:
            slot["speed_address_1"], slot["speed_address_2"] = a1 + SPEED_AOB_OFFSET, a2 + SPEED_AOB_OFFSET
            slot["speed_is_patched"] = patched
            if not patched:
                slot["speed_original_bytes_1"] = pm.read_bytes(slot["speed_address_1"], 6)
                slot["speed_original_bytes_2"] = pm.read_bytes(slot["speed_address_2"], 6)
    except: pass