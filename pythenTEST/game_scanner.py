# game_scanner.py
# 負責尋找遊戲視窗與記憶體特徵掃描

import ctypes
import ctypes.wintypes
import psutil
import pymem
import pymem.pattern
import json
import os
from constants import *
from logger import logger

# AOB 掃描快取檔案
AOB_CACHE_FILE = "aob_cache.json"

def load_aob_cache():
    """從快取檔案加載 AOB 掃描結果"""
    if os.path.exists(AOB_CACHE_FILE):
        try:
            with open(AOB_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
                logger.info(f"AOB cache loaded: {len(cache)} entries")
                return cache
        except Exception as e:
            logger.warning(f"Failed to load AOB cache: {e}")
    return {}

def save_aob_cache(cache):
    """將 AOB 掃描結果保存到快取檔案"""
    try:
        with open(AOB_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
            logger.debug(f"AOB cache saved: {len(cache)} entries")
    except Exception as e:
        logger.warning(f"Failed to save AOB cache: {e}")

# 全域快取
_aob_cache = load_aob_cache()

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
        if not mod: 
            logger.error(f"[PID {slot['pid']}] 模組 {PROCESS_NAME} 未找到")
            raise Exception("Module not found")
        slot["module_base"] = mod.lpBaseOfDll
        logger.info(f"[PID {slot['pid']}] 綁定成功，模組基址: 0x{mod.lpBaseOfDll:X}")
        
        # 1. 掃描行走
        _scan_pattern(slot, mod, AOB_PATTERN_WALK, WALK_PATCH_OFFSET, "walk", 1)
        
        # 2. 掃描加速
        _scan_speed(slot, mod)
        
        # 3. 掃描穿牆 (含備用特徵)
        _scan_pattern(slot, mod, AOB_PATTERN_NOCLIP_ORIGINAL, NOCLIP_PATCH_OFFSET, "noclip", 
                      len(NOCLIP_PATCHED_BYTES), AOB_PATTERN_NOCLIP_PATCHED)
        
        slot["status"] = "已綁定"
        logger.info(f"[PID {slot['pid']}] 掃描完成")
        return True
    except Exception as e:
        logger.error(f"[PID {slot.get('pid', '?')}] 掃描失敗: {e}")
        slot["status"] = "掃描失敗"
        if slot.get("pm_handle"): 
            try: slot["pm_handle"].close_process()
            except: pass
        slot["pm_handle"] = None
        return False

def _scan_pattern(slot, mod, pattern, offset, key_prefix, size, alt_pattern=None):
    pm = slot["pm_handle"]
    
    # 生成快取鍵 (以模組基址 + pattern 的前 16 字節作為快取鍵)
    cache_key = f"{mod.lpBaseOfDll:X}_{key_prefix}"
    
    # 先從快取查找
    if cache_key in _aob_cache:
        cached = _aob_cache[cache_key]
        slot[f"{key_prefix}_address"] = cached["address"]
        slot[f"{key_prefix}_is_patched"] = cached.get("is_patched", False)
        logger.debug(f"[{key_prefix}] 使用快取 @ 0x{cached['address']:X}")
        
        # 若未 patch 且有原始數據，還原
        if not cached.get("is_patched", False) and "original_bytes" in cached:
            orig_bytes_key = f"{key_prefix}_original_byte" if size == 1 else f"{key_prefix}_original_bytes"
            if size == 1:
                slot[orig_bytes_key] = cached["original_bytes"]
            else:
                slot[orig_bytes_key] = bytes(cached["original_bytes"])
        return
    
    # 快取未命中，執行掃描
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
            
            # 保存到快取
            cache_entry = {
                "address": final,
                "is_patched": patched,
                "timestamp": __import__('time').time()
            }
            
            if not patched:
                data = pm.read_bytes(final, size)
                slot[f"{key_prefix}_original_byte" if size==1 else f"{key_prefix}_original_bytes"] = data[0] if size==1 else data
                # 快取原始數據 (轉為 list 便於 JSON 序列化)
                cache_entry["original_bytes"] = list(data if size > 1 else [data[0]])
            
            _aob_cache[cache_key] = cache_entry
            save_aob_cache(_aob_cache)
            logger.info(f"[{key_prefix}] 掃描並快取 @ 0x{final:X}")
        else:
            logger.warning(f"[{key_prefix}] 特徵碼未找到")
    except Exception as e:
        logger.warning(f"[{key_prefix}] 掃描失敗: {e}")

def _scan_speed(slot, mod):
    pm = slot["pm_handle"]
    
    # 快取鍵
    cache_key_1 = f"{mod.lpBaseOfDll:X}_speed_1"
    cache_key_2 = f"{mod.lpBaseOfDll:X}_speed_2"
    
    # 從快取查找
    if cache_key_1 in _aob_cache and cache_key_2 in _aob_cache:
        c1 = _aob_cache[cache_key_1]
        c2 = _aob_cache[cache_key_2]
        slot["speed_address_1"] = c1["address"]
        slot["speed_address_2"] = c2["address"]
        slot["speed_is_patched"] = c1.get("is_patched", False)
        logger.debug(f"[speed] 使用快取 @ 0x{c1['address']:X}, 0x{c2['address']:X}")
        
        if not c1.get("is_patched") and "original_bytes" in c1:
            slot["speed_original_bytes_1"] = bytes(c1["original_bytes"])
            slot["speed_original_bytes_2"] = bytes(c2["original_bytes"])
        return
    
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
            
            # 保存到快取
            b1 = b2 = None
            if not patched:
                b1 = pm.read_bytes(slot["speed_address_1"], 6)
                b2 = pm.read_bytes(slot["speed_address_2"], 6)
                slot["speed_original_bytes_1"] = b1
                slot["speed_original_bytes_2"] = b2
            
            _aob_cache[cache_key_1] = {
                "address": slot["speed_address_1"],
                "is_patched": patched,
                "original_bytes": list(b1) if b1 else None,
                "timestamp": __import__('time').time()
            }
            _aob_cache[cache_key_2] = {
                "address": slot["speed_address_2"],
                "is_patched": patched,
                "original_bytes": list(b2) if b2 else None,
                "timestamp": __import__('time').time()
            }
            save_aob_cache(_aob_cache)
            logger.info(f"[speed] 掃描並快取 @ 0x{a1:X}, 0x{a2:X}")
        else:
            logger.warning("[speed] 加速特徵碼未找到")
    except Exception as e:
        logger.warning(f"[speed] 掃描失敗: {e}")