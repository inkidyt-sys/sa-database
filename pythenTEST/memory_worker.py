# memory_worker.py
# 獨立的執行緒，負責所有 Pymem 讀取操作，避免 UI 卡頓

import threading
import time
import queue
import pymem
import psutil

# 從項目檔案中導入
from constants import *
from utils import read_big5_string, format_elements

class MemoryMonitorThread(threading.Thread):
    def __init__(self, data_queue, command_queue, client_data_slots_ref):
        super().__init__()
        self.data_queue = data_queue           # (Worker -> UI) 傳送資料
        self.command_queue = command_queue     # (UI -> Worker) 接收命令
        self.client_data_slots = client_data_slots_ref # (Ref) 對主線程 slot 的引用
        
        self.stopped = threading.Event()       # 用於停止執行緒的信號
        self.refresh_interval_sec = 3.0        # 預設刷新率
        self.daemon = True                     # 確保主程式退出時此執行緒也會退出

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
            
            # 1. 檢查來自 UI 的命令 (例如：停止、改變刷新率)
            try:
                command = self.command_queue.get_nowait()
                if command.get("action") == "stop":
                    self.stop()
                    continue
                if command.get("action") == "set_rate":
                    rate_val = command.get("value")
                    if rate_val is None: # "不刷新"
                         self.set_refresh_rate(float('inf'))
                    else:
                        self.set_refresh_rate(rate_val)
                        
            except queue.Empty:
                pass # 沒有命令，繼續執行
            
            # 如果設為 "不刷新"，則在此處睡眠並跳過
            if self.refresh_interval_sec == float('inf'):
                time.sleep(1) # 保持執行緒活躍以響應命令
                continue

            # 2. 執行核心監控 (I/O 操作)
            full_update_data = []
            is_logging_in = False

            for i in range(MAX_CLIENTS):
                slot_data = self._monitor_slot(i)
                full_update_data.append(slot_data)
                
                state = slot_data.get("game_state")
                if state in (1, 2, 3) or state == "unbound":
                    is_logging_in = True

            # 3. 將整包資料發送回 UI 執行緒
            if not self.stopped.is_set():
                self.data_queue.put(full_update_data)

            # 4. 睡眠控制
            elapsed = time.time() - start_time
            
            # 如果在登入中，加快刷新率 (最多 1s)
            target_sleep = self.refresh_interval_sec
            if is_logging_in and target_sleep > 1.0:
                target_sleep = 1.0
                
            sleep_duration = max(0, target_sleep - elapsed)
            
            # 使用 wait() 而非 sleep()，這樣它可以被 stop() 信號立即中斷
            self.stopped.wait(sleep_duration)

        print("[Worker] 記憶體監控執行緒已停止。")


    def _monitor_slot(self, slot_index):
        """
        (Worker 執行緒)
        監控單個 slot，執行所有 pymem 讀取。
        返回一個包含 *最新資料* 的字典，用於更新 UI 執行緒的快取。
        """
        slot = self.client_data_slots[slot_index]
        pm = slot.get("pm_handle")
        base = slot.get("module_base")

        # --- 返回的資料包 ---
        update_package = {
            "status": slot["status"], # 預設為當前狀態
            "game_state": "unbound",
            "account_name": "",
            "char_data_cache": None,
            "pet_data_cache": [None] * 5
        }

        if not pm or not base or not slot["pid"]:
            update_package["status"] = "未綁定"
            # (v3.6 邏輯) 如果句柄失效，主線程的 on_bind_click 會負責清理
            # 這裡我們只報告狀態
            return update_package

        try:
            # (v3.6 核心) 使用輕量級 read 測試句柄是否有效
            state_addr = base + GAME_STATE_OFFSET
            game_state = pm.read_int(state_addr)
            
            update_package["game_state"] = game_state
            update_package["status"] = "已綁定" # 讀取成功
            
            new_display_text = f"狀態: {game_state}"
            
            if game_state in (1, 2):
                new_display_text = "登入中"
            elif game_state == 3:
                new_display_text = "選擇角色"
            elif game_state > 3:
                try:
                    # 讀取帳號
                    account_addr = base + ACCOUNT_STRING_OFFSET
                    raw_string = pm.read_string(account_addr, 100) 
                    account_name = raw_string.split("www.longzor")[0]
                    if not account_name: account_name = "登入完成"
                    new_display_text = account_name
                except Exception as e_str:
                    print(f"  > (PID: {slot['pid']}) 讀取帳號字串失敗: {e_str}")
                    new_display_text = "登入完成"
                
                # 讀取人寵資料
                update_package["char_data_cache"] = self._read_character_data(pm, base)
                update_package["pet_data_cache"] = self._update_and_read_pet_data(pm, base, slot["pet_data_cache"])

            update_package["account_name"] = new_display_text
            return update_package

        except Exception as e:
            # (v3.6 邏輯) 讀取失敗，進程可能已關閉
            print(f"[Worker] 監控窗口 {slot_index+1} (PID: {slot['pid']}) 時出錯: {e}")
            update_package["status"] = "已失效" # 標記為已失效
            update_package["game_state"] = "unbound"
            
            # (重要) 主線程的 on_bind_click 會在下次點擊時
            # 偵測到這個 "已失效" 狀態，並清理句柄。
            # 執行緒不應主動關閉主線程的句柄。
            return update_package

    def _read_character_data(self, pm, base):
        """(Worker 執行緒) 讀取所有人物資料"""
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
            data["element"] = format_elements(e, w, f, wi) 
            data["vit"] = pm.read_int(base + CHAR_VIT_OFFSET)
            data["str"] = pm.read_int(base + CHAR_STR_OFFSET)
            data["sta"] = pm.read_int(base + CHAR_STA_OFFSET)
            data["spd"] = pm.read_int(base + CHAR_SPD_OFFSET)
            return data
        except Exception as e:
            print(f"  > (PID: {pm.process_id}) 讀取人物資料時出錯: {e}")
            return None 

    def _update_and_read_pet_data(self, pm, base, old_pet_cache):
        """(Worker 執行緒) 依賴快取狀態讀取寵物資料"""
        new_pet_cache = [None] * 5
        pet_1_base_addr = base + PET_1_BASE_OFFSET
        
        for p_idx in range(5):
            current_pet_base_addr = pet_1_base_addr + (p_idx * PET_STRUCT_SIZE)
            exist_addr = current_pet_base_addr + PET_EXIST_REL
            
            cache_is_filled = (old_pet_cache[p_idx] is not None)
            
            try:
                exist_val = pm.read_uchar(exist_addr)

                if exist_val == 1:
                    # 寵物存在，讀取/更新資料
                    new_pet_cache[p_idx] = self._read_single_pet(pm, current_pet_base_addr)
                
                elif exist_val == 0 and cache_is_filled:
                    # 寵物剛被移除
                    print(f"  > (PID: {pm.process_id}) 寵物 {p_idx+1} 已移除，清空資料。")
                    new_pet_cache[p_idx] = None
                else:
                    # 寵物不存在，且快取本來就是空的
                    new_pet_cache[p_idx] = None
                
            except Exception as e:
                print(f"  > (PID: {pm.process_id}) 讀取寵物 {p_idx+1} *存在狀態*時出錯: {e}")
                new_pet_cache[p_idx] = None
        
        return new_pet_cache

    def _read_single_pet(self, pm, pet_base_addr):
        """(Worker 執行緒) 讀取單個寵物的詳細資料"""
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
            pet_data["element"] = format_elements(e, w, f, wi) 
            
            return pet_data
            
        except Exception as e:
            print(f"  > (PID: {pm.process_id}) 讀取寵物 *詳細資料*時出錯: {e}")
            return None