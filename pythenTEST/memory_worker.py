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
        """(Worker) 監控單個 slot (強制除錯版)"""
        slot = self.client_data_slots[slot_index]
        pm = slot.get("pm_handle")
        base = slot.get("module_base")

        update_package = {
            "status": slot["status"], 
            "game_state": "unbound",
            "account_name": "",
            "char_data_cache": None,
            "pet_data_cache": [None] * 5,
            "item_data_cache": {},
            "battle_data_cache": {} 
        }

        if not pm or not base or not slot["pid"]:
            update_package["status"] = "未綁定"
            return update_package

        try:
            state_addr = base + GAME_STATE_OFFSET
            game_state = pm.read_int(state_addr)
            
            update_package["game_state"] = game_state
            update_package["status"] = "已綁定" 
            
            # (除錯) 當狀態大於 3 時，印出狀態碼，確認是否有變成 10
            # 為了避免洗頻，您可以只看這行
            if game_state >= 10:
                print(f"[Debug] 窗口 {slot_index+1} (PID {slot['pid']}) 當前狀態: {game_state}")

            new_display_text = f"狀態: {game_state}"
            
            if game_state == 11:
                new_display_text = "斷線"
            elif game_state in (1, 2):
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
                except Exception:
                    new_display_text = "登入完成"
                
                update_package["char_data_cache"] = self._read_character_data(pm, base)
                update_package["pet_data_cache"] = self._update_and_read_pet_data(pm, base, slot["pet_data_cache"])
                update_package["item_data_cache"] = self._read_items(pm, base)
                
                # (除錯) 只要狀態 >= 10 就嘗試讀取戰鬥數據 (包含戰鬥中與戰鬥結束結算畫面等)
                # 這樣可以確保即使狀態不是 10 也能測試讀取
                if game_state == 10:
                    print(f"[Debug] 偵測到戰鬥狀態 (10)，準備讀取數據...")
                    update_package["battle_data_cache"] = self._read_battle_data(pm, base)

            update_package["account_name"] = new_display_text
            return update_package

        except Exception as e:
            update_package["status"] = "已失效" 
            update_package["game_state"] = "unbound"
            return update_package

    def _read_battle_data(self, pm, base):
        """(Worker) 讀取並解析戰鬥字串 (固定間距 13)"""
        battle_map = {}
        try:
            # 1. 讀取長字串
            raw_str = read_big5_string(pm, base + BATTLE_STRING_OFFSET, 4096)
            if not raw_str: return {}

            # 2. 分割字串
            tokens = raw_str.split('|')
            
            # 每一組資料有 13 個欄位 (根據您的說明)
            # 0:編號, 1:名稱, 2:稱號, 3:編號A, 4:等級, 5:現血, 6:最大血
            # 7:?, 8:?, 9:騎寵名, 10:騎寵等級, 11:騎寵現血, 12:騎寵最大血
            step = 13
            
            for i in range(0, len(tokens), step):
                # 確保這一組有完整的 13 個欄位 (避免最後一段不完整導致報錯)
                if i + 12 >= len(tokens):
                    break
                
                try:
                    # --- 解析人物 ---
                    # 欄位 1: 名稱
                    unit_name = tokens[i+1]
                    
                    # 過濾雜訊 (名稱為空或 "0" 則跳過)
                    if not unit_name or unit_name == "0": 
                        continue

                    # 欄位 0: 編號 (ID)
                    pos_id = int(tokens[i], 16)
                    
                    # 欄位 4, 5, 6: 等級, 現血, 最大血 (Hex)
                    lv = int(tokens[i+4], 16)
                    cur_hp = int(tokens[i+5], 16)
                    max_hp = int(tokens[i+6], 16)
                    
                    display_str = f"[{lv}]{unit_name} ({cur_hp}/{max_hp})"

                    # --- 解析騎寵 ---
                    # 欄位 9: 騎寵名稱
                    pet_name = tokens[i+9]
                    
                    # 判斷是否有騎寵 (有名稱且不是 "0")
                    if pet_name and pet_name != "0":
                        try:
                            # 欄位 10, 11, 12: 騎寵等級, 現血, 最大血 (Hex)
                            pet_lv = int(tokens[i+10], 16)
                            pet_cur = int(tokens[i+11], 16)
                            pet_max = int(tokens[i+12], 16)
                            
                            display_str += f" ;[{pet_lv}]{pet_name} ({pet_cur}/{pet_max})"
                        except ValueError:
                            pass # 騎寵數值解析失敗則忽略騎寵部分
                    
                    # 存入 Map
                    battle_map[pos_id] = display_str

                except (ValueError, IndexError):
                    # 解析單一隻失敗 (例如數值不是 Hex)，跳過該隻，繼續下一組
                    continue

            return battle_map

        except Exception as e:
            print(f"[Worker] 讀取戰鬥數據失敗: {e}")
            return {}
        
    # --- memory_worker.py 修改部分 ---

    def _read_battle_data(self, pm, base):
        """(Worker) 讀取並解析戰鬥字串 (固定間距 13 - 修正版)"""
        battle_map = {}
        try:
            # 1. 讀取長字串
            raw_str = read_big5_string(pm, base + BATTLE_STRING_OFFSET, 4096)
            if not raw_str: return {}

            # 2. 分割字串
            tokens = raw_str.split('|')
            
            # 每一組資料有 13 個欄位
            # 0:編號, 1:名稱, 2:稱號, 3:編號A, 4:等級, 5:現血, 6:最大血
            # 7:?, 8:?, 9:騎寵名, 10:騎寵等級, 11:騎寵現血, 12:騎寵最大血
            step = 13
            
            for i in range(0, len(tokens), step):
                # 確保這一組有完整的 13 個欄位
                if i + 12 >= len(tokens):
                    break
                
                try:
                    # --- 解析人物 ---
                    unit_name = tokens[i+1] # 名稱
                    
                    # 過濾雜訊 (名稱為空或 "0" 則跳過)
                    if not unit_name or unit_name == "0": 
                        continue

                    pos_id = int(tokens[i], 16) # 編號
                    
                    lv = int(tokens[i+4], 16) # 等級
                    cur_hp = int(tokens[i+5], 16) # 現血
                    max_hp = int(tokens[i+6], 16) # 最大血
                    
                    display_str = f"[{lv}]{unit_name} ({cur_hp}/{max_hp})"

                    # --- 解析騎寵 ---
                    pet_name = tokens[i+9] # 騎寵名稱
                    
                    # 判斷是否有騎寵 (有名稱且不是 "0")
                    if pet_name and pet_name != "0":
                        try:
                            pet_lv = int(tokens[i+10], 16)
                            pet_cur = int(tokens[i+11], 16)
                            pet_max = int(tokens[i+12], 16)
                            
                            display_str += f" ;[{pet_lv}]{pet_name} ({pet_cur}/{pet_max})"
                        except ValueError:
                            pass 
                    
                    # 存入 Map
                    battle_map[pos_id] = display_str
                    # print(f"[Debug] 解析成功 -> ID: {pos_id} | 內容: {display_str}") # 除錯用

                except (ValueError, IndexError):
                    continue

            return battle_map

        except Exception as e:
            print(f"[Worker] 讀取戰鬥數據失敗: {e}")
            return {}
        
    def _read_items(self, pm, base):
        """(Worker) 讀取裝備(-9~-1) 與 道具(0~14)"""
        items_dict = {}
        start_addr = base + ITEM_BASE_OFFSET
        
        # 範圍：從 -9 (頭部) 到 14 (道具15)，共 24 格
        for i in range(-9, 15):
            current_item_addr = start_addr + (i * ITEM_STRUCT_SIZE)
            
            try:
                exist = pm.read_uchar(current_item_addr + ITEM_EXIST_REL)
                if exist == 0:
                    items_dict[i] = None
                    continue
                
                item_data = {}
                item_data["idx"] = i
                item_data["stack"] = pm.read_int(current_item_addr + ITEM_STACK_REL)
                
                # 讀取字串
                item_data["name"] = read_big5_string(pm, current_item_addr + ITEM_NAME_REL, 40)
                item_data["desc"] = read_big5_string(pm, current_item_addr + ITEM_DESC_REL, 100)
                item_data["dur"]  = read_big5_string(pm, current_item_addr + ITEM_DUR_REL, 20)
                
                items_dict[i] = item_data
                
            except Exception:
                items_dict[i] = None
                
        return items_dict

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