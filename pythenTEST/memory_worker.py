# memory_worker.py
# 獨立執行緒，負責 Pymem 讀取操作

import threading
import time
import queue
import pymem
import psutil

from constants import *
from utils import read_big5_string, format_elements

class MemoryMonitorThread(threading.Thread):
    def __init__(self, data_queue, command_queue, client_data_slots_ref):
        super().__init__()
        self.data_queue = data_queue
        self.command_queue = command_queue
        self.client_data_slots = client_data_slots_ref
        self.stopped = threading.Event()
        self.refresh_interval_sec = 3.0
        self.daemon = True

    def run(self):
        print("[Worker] 記憶體監控執行緒已啟動。")
        while not self.stopped.is_set():
            start_time = time.time()
            
            # 1. 處理命令
            try:
                cmd = self.command_queue.get_nowait()
                if cmd["action"] == "stop": self.stopped.set(); continue
                if cmd["action"] == "set_rate": 
                    self.refresh_interval_sec = cmd["value"] if cmd["value"] is not None else float('inf')
            except queue.Empty: pass

            if self.refresh_interval_sec == float('inf'):
                time.sleep(1)
                continue

            # 2. 執行掃描
            data_package = []
            active_login = False
            
            for i in range(MAX_CLIENTS):
                res = self._monitor_slot(i)
                data_package.append(res)
                if res["game_state"] in (1, 2, 3) or res["game_state"] == "unbound":
                    active_login = True
            
            self.data_queue.put(data_package)

            # 3. 智能休眠
            elapsed = time.time() - start_time
            sleep_time = max(0, self.refresh_interval_sec - elapsed)
            # 若處於登入階段，強制加速刷新以獲得即時反饋
            if active_login and sleep_time > 1.0: sleep_time = 1.0
            
            self.stopped.wait(sleep_time)
        print("[Worker] 停止。")

    def _monitor_slot(self, idx):
        slot = self.client_data_slots[idx]
        pm, base = slot.get("pm_handle"), slot.get("module_base")
        res = {
            "status": slot["status"], "game_state": "unbound", "account_name": "",
            "char_data_cache": None, "pet_data_cache": [None]*5, 
            "item_data_cache": {}, "battle_data_cache": {}
        }
        
        if not pm or not base or not slot["pid"]:
            res["status"] = "未綁定"
            return res

        try:
            state = pm.read_int(base + GAME_STATE_OFFSET)
            res["game_state"] = state
            res["status"] = "已綁定"

            # 狀態文字處理
            if state == 11: txt = "斷線"
            elif state in (1, 2): txt = "登入中"
            elif state == 3: txt = "選擇角色"
            elif state > 3:
                try:
                    s = pm.read_string(base + ACCOUNT_STRING_OFFSET, 100)
                    txt = s.split("www.")[0] if s else "登入完成"
                except: txt = "登入完成"
                
                # 讀取詳細資料
                res["char_data_cache"] = self._read_char(pm, base)
                res["pet_data_cache"] = self._read_pets(pm, base, slot["pet_data_cache"])
                res["item_data_cache"] = self._read_items(pm, base)
                
                # 戰鬥數據 (狀態 10 或測試需求)
                if state == 10:
                    res["battle_data_cache"] = self._read_battle(pm, base)
            else:
                txt = f"狀態: {state}"
            
            res["account_name"] = txt
            return res
        except Exception:
            res["status"] = "已失效"
            return res

    def _read_char(self, pm, base):
        try:
            d = {}
            d["name"] = read_big5_string(pm, base + CHAR_NAME_OFFSET, 16)
            d["nickname"] = read_big5_string(pm, base + CHAR_NICKNAME_OFFSET, 12)
            d["rebirth"] = REBIRTH_MAP.get(pm.read_int(base + CHAR_REBIRTH_OFFSET), "未知")
            d["lv"] = pm.read_int(base + CHAR_LV_OFFSET)
            d["hp"] = f"{pm.read_int(base + CHAR_HP_CUR_OFFSET)}/{pm.read_int(base + CHAR_HP_MAX_OFFSET)}"
            d["mp"] = f"{pm.read_int(base + CHAR_MP_CUR_OFFSET)}/{pm.read_int(base + CHAR_MP_MAX_OFFSET)}"
            
            for k, off in [("atk", CHAR_ATK_OFFSET), ("def", CHAR_DEF_OFFSET), 
                           ("agi", CHAR_AGI_OFFSET), ("charm", CHAR_CHARM_OFFSET),
                           ("vit", CHAR_VIT_OFFSET), ("str", CHAR_STR_OFFSET),
                           ("sta", CHAR_STA_OFFSET), ("spd", CHAR_SPD_OFFSET)]:
                d[k] = pm.read_int(base + off)

            e = pm.read_int(base + CHAR_ELEM_EARTH_OFFSET)
            w = pm.read_int(base + CHAR_ELEM_WATER_OFFSET)
            f = pm.read_int(base + CHAR_ELEM_FIRE_OFFSET)
            wi = pm.read_int(base + CHAR_ELEM_WIND_OFFSET)
            d["element_raw"] = (e, w, f, wi)
            return d
        except: return None

    def _read_pets(self, pm, base, old_cache):
        new_cache = [None] * 5
        base_addr = base + PET_1_BASE_OFFSET
        
        # 讀取特殊狀態索引
        try:
            b_idx = pm.read_uchar(base + CHAR_BATTLE_PET_OFFSET)
            m_idx = pm.read_uchar(base + CHAR_MAIL_PET_OFFSET)
            r_idx = pm.read_uchar(base + CHAR_RIDING_PET_OFFSET)
            if b_idx == 255: b_idx = -1
            if m_idx == 255: m_idx = -1
            if r_idx == 255: r_idx = -1
        except: b_idx, m_idx, r_idx = -1, -1, -1

        for i in range(5):
            addr = base_addr + (i * PET_STRUCT_SIZE)
            try:
                if pm.read_uchar(addr + PET_EXIST_REL) == 1:
                    d = self._read_single_pet(pm, addr)
                    # 狀態標記
                    st, sk = "休", "未轉生"
                    if i == r_idx: st, sk = "騎", "轉生伍"
                    elif i == b_idx: st, sk = "戰", "轉生肆"
                    elif i == m_idx: st, sk = "郵", "轉生貳"
                    elif pm.read_uchar(base + PET_WAIT_FLAGS_BASE + (i*2)) == 1: st, sk = "等", "轉生叁"
                    
                    if d:
                        d["status_text"] = st
                        d["status_color_key"] = sk
                    new_cache[i] = d
                # 若不存在但舊快取有值，設為 None
            except: pass
        return new_cache

    def _read_single_pet(self, pm, addr):
        try:
            d = {}
            d["name"] = read_big5_string(pm, addr + PET_NAME_REL, 16)
            d["nickname"] = read_big5_string(pm, addr + PET_NICKNAME_REL, 12)
            d["rebirth"] = REBIRTH_MAP.get(pm.read_int(addr + PET_REBIRTH_REL), "未知")
            d["lv"] = pm.read_int(addr + PET_LV_REL)
            d["exp"] = pm.read_int(addr + PET_EXP_REL)
            
            lack = pm.read_int(addr + PET_LACK_REL)
            d["lack"] = max(0, lack - d["exp"]) if lack not in (-1, PET_LACK_EXP_MAX) else "--"
            
            d["hp"] = f"{pm.read_int(addr + PET_HP_CUR_REL)}/{pm.read_int(addr + PET_HP_MAX_REL)}"
            d["atk"] = pm.read_int(addr + PET_ATK_REL)
            d["def"] = pm.read_int(addr + PET_DEF_REL)
            d["agi"] = pm.read_int(addr + PET_AGI_REL)
            d["loyal"] = pm.read_int(addr + PET_LOYALTY_REL)
            
            e = pm.read_int(addr + PET_ELEM_EARTH_REL)
            w = pm.read_int(addr + PET_ELEM_WATER_REL)
            f = pm.read_int(addr + PET_ELEM_FIRE_REL)
            wi = pm.read_int(addr + PET_ELEM_WIND_REL)
            d["element_raw"] = (e, w, f, wi)
            return d
        except: return None

    def _read_items(self, pm, base):
        res = {}
        start = base + ITEM_BASE_OFFSET
        for i in range(-9, 15):
            addr = start + (i * ITEM_STRUCT_SIZE)
            try:
                if pm.read_uchar(addr + ITEM_EXIST_REL) == 0:
                    res[i] = None
                    continue
                d = {
                    "idx": i,
                    "stack": pm.read_int(addr + ITEM_STACK_REL),
                    "name": read_big5_string(pm, addr + ITEM_NAME_REL, 40),
                    "desc": read_big5_string(pm, addr + ITEM_DESC_REL, 100),
                    "dur": read_big5_string(pm, addr + ITEM_DUR_REL, 20)
                }
                res[i] = d
            except: res[i] = None
        return res

    def _read_battle(self, pm, base):
        res = {}
        try:
            from constants import BATTLE_STRING_OFFSET
            from utils import read_big5_string
            
            # [新增] 讀取指定位置 (sadsa.exe+1E9110) 用於判斷藍色文字
            try:
                # 讀取 1 byte
                cmd_idx = pm.read_uchar(base + 0x1E9110)
                res["cmd_idx"] = cmd_idx
            except:
                res["cmd_idx"] = -1

            # 讀取原本的戰鬥字串
            raw = read_big5_string(pm, base + BATTLE_STRING_OFFSET, 4096)
            if not raw: return res
            
            tokens = raw.split('|')
            # 13 欄位一組
            for i in range(0, len(tokens), 13):
                if i + 12 >= len(tokens): break
                try:
                    name = tokens[i+1]
                    if not name or name == "0": continue
                    
                    pid = int(tokens[i], 16)
                    lv = int(tokens[i+4], 16)
                    hp = int(tokens[i+5], 16)
                    max_hp = int(tokens[i+6], 16)
                    
                    data = {
                        "name": name,
                        "lv": lv,
                        "hp": hp,
                        "max_hp": max_hp,
                        "pet_info": None
                    }
                    
                    pet_name = tokens[i+9]
                    if pet_name and pet_name != "0":
                        plv = int(tokens[i+10], 16)
                        php = int(tokens[i+11], 16)
                        pmax = int(tokens[i+12], 16)
                        data["pet_info"] = {
                            "name": pet_name,
                            "lv": plv,
                            "hp": php,
                            "max_hp": pmax
                        }
                    
                    res[pid] = data
                except: continue
            return res
        except: return {}