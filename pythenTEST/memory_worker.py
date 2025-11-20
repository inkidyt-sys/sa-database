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
        self.data_queue = data_queue           # (Worker -> UI) 傳送資料
        self.command_queue = command_queue     # (UI -> Worker) 接收命令
        self.client_data_slots = client_data_slots_ref 
        
        self.stopped = threading.Event()       
        self.refresh_interval_sec = 3.0        
        self.daemon = True                     

    def stop(self):
        """設置停止信號"""
        self.stopped.set()

    def set_refresh_rate(self, seconds):
        """從外部設置刷新率"""
        self.refresh_interval_sec = seconds
        print(f"[Worker] 刷新率設置為 {seconds} 秒")

    def run(self):
        """執行緒的主迴圈"""
        print("[Worker] 記憶體監控執行緒已啟動。")
        
        while not self.stopped.is_set():
            start_time = time.time()
            
            # 1. 檢查命令
            try:
                command = self.command_queue.get_nowait()
                if command.get("action") == "stop":
                    self.stop()
                    continue
                if command.get("action") == "set_rate":
                    rate_val = command.get("value")
                    if rate_val is None: 
                         self.set_refresh_rate(float('inf'))
                    else:
                        self.set_refresh_rate(rate_val)
            except queue.Empty:
                pass 
            
            if self.refresh_interval_sec == float('inf'):
                time.sleep(1)
                continue

            # 2. 執行監控
            full_update_data = []
            is_logging_in = False

            for i in range(MAX_CLIENTS):
                slot_data = self._monitor_slot(i)
                full_update_data.append(slot_data)
                
                state = slot_data.get("game_state")
                if state in (1, 2, 3) or state == "unbound":
                    is_logging_in = True

            # 3. 發送資料
            if not self.stopped.is_set():
                self.data_queue.put(full_update_data)

            # 4. 睡眠控制
            elapsed = time.time() - start_time
            target_sleep = self.refresh_interval_sec
            if is_logging_in and target_sleep > 1.0:
                target_sleep = 1.0
            sleep_duration = max(0, target_sleep - elapsed)
            self.stopped.wait(sleep_duration)

        print("[Worker] 記憶體監控執行緒已停止。")

    def _monitor_slot(self, slot_index):
        """監控單個 slot，執行所有 pymem 讀取"""
        slot = self.client_data_slots[slot_index]
        pm = slot.get("pm_handle")
        base = slot.get("module_base")

        update_package = {
            "status": slot["status"], 
            "game_state": "unbound",
            "account_name": "",
            "char_data_cache": None,
            "pet_data_cache": [None] * 5
        }

        if not pm or not base or not slot["pid"]:
            update_package["status"] = "未綁定"
            return update_package

        try:
            state_addr = base + GAME_STATE_OFFSET
            game_state = pm.read_int(state_addr)
            
            update_package["game_state"] = game_state
            update_package["status"] = "已綁定"
            
            new_display_text = f"狀態: {game_state}"
            
            if game_state in (1, 2):
                new_display_text = "登入中"
            elif game_state == 3:
                new_display_text = "選擇角色"
            elif game_state > 3:
                try:
                    account_addr = base + ACCOUNT_STRING_OFFSET
                    raw_string = pm.read_string(account_addr, 100) 
                    account_name = raw_string.split("www.longzor")[0]
                    if not account_name: account_name = "登入完成"
                    new_display_text = account_name
                except Exception as e_str:
                    print(f"  > (PID: {slot['pid']}) 讀取帳號字串失敗: {e_str}")
                    new_display_text = "登入完成"
                
                update_package["char_data_cache"] = self._read_character_data(pm, base)
                update_package["pet_data_cache"] = self._update_and_read_pet_data(pm, base, slot["pet_data_cache"])

            update_package["account_name"] = new_display_text
            return update_package

        except Exception as e:
            print(f"[Worker] 監控窗口 {slot_index+1} (PID: {slot['pid']}) 時出錯: {e}")
            update_package["status"] = "已失效" 
            update_package["game_state"] = "unbound"
            return update_package

    def _read_character_data(self, pm, base):
        """讀取所有人物資料"""
        data = {}
        try:
            data["name"] = read_big5_string(pm, base + CHAR_NAME_OFFSET, 16)
            data["nickname"] = read_big5_string(pm, base + CHAR_NICKNAME_OFFSET, 12)
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
            data["element_str"] = format_elements(e, w, f, wi)
            data["element_raw"] = (e, w, f, wi)
            data["vit"] = pm.read_int(base + CHAR_VIT_OFFSET)
            data["str"] = pm.read_int(base + CHAR_STR_OFFSET)
            data["sta"] = pm.read_int(base + CHAR_STA_OFFSET)
            data["spd"] = pm.read_int(base + CHAR_SPD_OFFSET)
            return data
        except Exception as e:
            print(f"  > (PID: {pm.process_id}) 讀取人物資料時出錯: {e}")
            return None 

    def _update_and_read_pet_data(self, pm, base, old_pet_cache):
        """讀取寵物資料與狀態"""
        new_pet_cache = [None] * 5
        pet_1_base_addr = base + PET_1_BASE_OFFSET
        
        try:
            battle_val = pm.read_uchar(base + CHAR_BATTLE_PET_OFFSET)
            battle_idx = battle_val if battle_val != 255 else -1

            mail_val = pm.read_uchar(base + CHAR_MAIL_PET_OFFSET)
            mail_idx = mail_val if mail_val != 255 else -1

            ride_val = pm.read_uchar(base + CHAR_RIDING_PET_OFFSET)
            ride_idx = ride_val if ride_val != 255 else -1

        except Exception as e_global:
            print(f"  > (PID: {pm.process_id}) 讀取全局寵物狀態失敗: {e_global}")
            battle_idx, mail_idx, ride_idx = -1, -1, -1
        
        for p_idx in range(5):
            current_pet_base_addr = pet_1_base_addr + (p_idx * PET_STRUCT_SIZE)
            exist_addr = current_pet_base_addr + PET_EXIST_REL
            cache_is_filled = (old_pet_cache[p_idx] is not None)
            
            try:
                exist_val = pm.read_uchar(exist_addr)
                if exist_val == 1:
                    new_pet_cache[p_idx] = self._read_single_pet(pm, current_pet_base_addr)
                    try:
                        status_text = "休" 
                        status_color_key = "未轉生" 

                        if p_idx == ride_idx:
                            status_text = "騎"; status_color_key = "轉生伍"
                        elif p_idx == battle_idx:
                            status_text = "戰"; status_color_key = "轉生肆"
                        elif p_idx == mail_idx:
                            status_text = "郵"; status_color_key = "轉生貳"
                        else:
                            wait_addr = base + PET_WAIT_FLAGS_BASE + (p_idx * 2)
                            wait_val = pm.read_uchar(wait_addr)
                            if wait_val == 1:
                                status_text = "等"; status_color_key = "轉生叁"
                        
                        if new_pet_cache[p_idx] is not None:
                            new_pet_cache[p_idx]["status_text"] = status_text
                            new_pet_cache[p_idx]["status_color_key"] = status_color_key
                            
                    except Exception as e_status:
                         print(f"  > (PID: {pm.process_id}) 讀取寵物 {p_idx+1} 狀態細節失敗: {e_status}")
                         if new_pet_cache[p_idx] is not None:
                             new_pet_cache[p_idx]["status_text"] = "?"
                elif exist_val == 0 and cache_is_filled:
                    new_pet_cache[p_idx] = None
                else:
                    new_pet_cache[p_idx] = None
            except Exception as e:
                print(f"  > (PID: {pm.process_id}) 讀取寵物 {p_idx+1} 存在狀態時出錯: {e}")
                new_pet_cache[p_idx] = None
        return new_pet_cache
    
    def _read_single_pet(self, pm, pet_base_addr):
        """讀取單個寵物的詳細數值"""
        pet_data = {}
        try:
            pet_data["name"] = read_big5_string(pm, pet_base_addr + PET_NAME_REL, 16)
            pet_data["nickname"] = read_big5_string(pm, pet_base_addr + PET_NICKNAME_REL, 12)
            
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
            pet_data["element_str"] = format_elements(e, w, f, wi)
            pet_data["element_raw"] = (e, w, f, wi) 
            return pet_data
        except Exception as e:
            print(f"  > (PID: {pm.process_id}) 讀取寵物詳細資料時出錯: {e}")
            return None