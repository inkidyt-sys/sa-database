import tkinter as tk
from tkinter import ttk, scrolledtext
import pymem
import pymem.pattern
import psutil
import sys
import os
import ctypes

# --- (DPI 感知設定) ---
# (此設定必須在 tkinter 之前)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1) 
except (AttributeError, OSError):
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass
# --- (DPI 感知結束) ---


# --- 您的修補設定 (全域變數) ---
PROCESS_NAME = "sadsa.exe"
MAX_CLIENTS = 6

# --- 1. 快速行走設定 ---
AOB_PATTERN_WALK = rb"\x0F\x2F\x45\xEC..\xF3\x0F\x10\x45\xF4"
WALK_PATCH_OFFSET = 4      # 0x72 在特徵碼中的偏移量
WALK_PATCHED_BYTE = 0x74   # je

# --- 2. 遊戲加速設定 (NOP 補丁) ---
AOB_PATTERN_SPEED_1 = rb"\x8B\x95\xD8\xFB\xFF\xFF\x03\x15....\x89\x95\xA4\xFB\xFF\xFF"
AOB_PATTERN_SPEED_2 = rb"\x8B\x85\xD8\xFB\xFF\xFF\x03\x05....\x89\x85\xB4\xFB\xFF\xFF"
SPEED_AOB_OFFSET = 6       # add 指令在特徵码中的偏移量
NOP_PATCH = b"\x90\x90\x90\x90\x90\x90" # 6 個 NOP

# --- 3. 穿牆行走設定 ---
AOB_PATTERN_NOCLIP = rb"\x83\xFA\x01\x75.\xB8\x01\x00\x00\x00\xEB.\x33\xC0\x8B\xE5\x5D\xC3"
NOCLIP_PATCH_OFFSET = 5      # mov eax, 1 在特徵碼中的偏移量 (已修正)
NOCLIP_PATCHED_BYTES = b"\xB8\x00\x00\x00\x00" # mov eax, 0
# --------------------------------

class GamePatcherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DSA新端加速器v2.0 by 石器推廣大使")
        
        # (保持) 移除固定大小，讓 tkinter 自動計算
        self.resizable(False, False) 

        self.slot_widgets = []
        
        if not self.is_admin():
            self.title(f"{self.title()} (錯誤：請以管理員權限執行)")
            label = tk.Label(self, text="錯誤：\n必須以「系統管理員」權限執行此程式！", 
                             font=("Arial", 12), fg="red")
            label.pack(pady=50)
            return

        self.create_widgets()

    def is_admin(self):
        try: return os.getuid() == 0
        except AttributeError: return ctypes.windll.shell32.IsUserAnAdmin() != 0

    def create_widgets(self):
        """建立所有GUI元件"""
        
        top_frame = ttk.Frame(self, padding=(10, 10, 10, 2))
        top_frame.pack(fill="x")

        self.bind_button = ttk.Button(top_frame, text="綁定視窗 (sadsa.exe)", 
                                      command=self.bind_games)
        self.bind_button.pack(fill="x", expand=True, ipady=2)

        middle_frame = ttk.Frame(self, padding=(10, 5, 10, 10))
        middle_frame.pack(fill="both", expand=True)

        for i in range(MAX_CLIENTS):
            slot_frame = ttk.Frame(middle_frame, padding=5, relief="groove")
            slot_frame.pack(fill="x", pady=2)
            
            # --- (★★★ 已修改 1/2 ★★★) ---
            # 1. 移除 '窗口 1:' 的標籤
            # label = ttk.Label(slot_frame, text=f"窗口 {i+1}:", width=8)
            # label.pack(side="left", padx=5)

            # 2. 將文字 "窗口 1:" 合併到狀態標籤中
            # 3. 加寬狀態標籤以容納新文字
            status_label = ttk.Label(
                slot_frame, 
                text=f"窗口 {i+1}: 未綁定",  # <-- 新文字
                width=22,                 # <-- 加寬 (例如 14 -> 26)
                foreground="grey"
            )
            status_label.pack(side="left", padx=5)
            # --- (★★★ 修改結束 ★★★) ---

            # --- 快速行走 (功能 1) ---
            walk_var = tk.IntVar()
            walk_check = ttk.Checkbutton(
                slot_frame, text="快速行走", variable=walk_var, state="disabled",
                command=lambda idx=i: self.on_walk_toggle(idx)
            )
            walk_check.pack(side="left", padx=5)
            
            # --- 遊戲加速 (功能 2) ---
            speed_var = tk.IntVar()
            speed_check = ttk.Checkbutton(
                slot_frame, text="遊戲加速", variable=speed_var, state="disabled",
                command=lambda idx=i: self.on_speed_toggle(idx)
            )
            speed_check.pack(side="left", padx=5)
            
            # --- 穿牆行走 (功能 3) ---
            noclip_var = tk.IntVar()
            noclip_check = ttk.Checkbutton(
                slot_frame, text="穿牆行走", variable=noclip_var, state="disabled",
                command=lambda idx=i: self.on_noclip_toggle(idx)
            )
            noclip_check.pack(side="left", padx=5)
            
            # 儲存所有資訊
            self.slot_widgets.append({
                "frame": slot_frame,
                "status_label": status_label,
                "pid": None,
                "walk_check_var": walk_var,
                "walk_checkbox": walk_check,
                "walk_patch_address": None, 
                "walk_original_byte_cache": None, 
                "speed_check_var": speed_var,
                "speed_checkbox": speed_check,
                "speed_patch_address_1": None,
                "speed_patch_address_2": None,
                "speed_original_bytes_1": None, 
                "speed_original_bytes_2": None,
                "noclip_check_var": noclip_var,
                "noclip_checkbox": noclip_check,
                "noclip_patch_address": None,
                "noclip_original_bytes_cache": None 
            })

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log(self, message):
        """日誌函式現在只印出到主控台"""
        print(message)

    def bind_games(self):
        """搜尋所有 sadsa.exe 進程並更新GUI"""
        self.log(f"--- 開始搜尋 {PROCESS_NAME} ---")
        
        for i in range(MAX_CLIENTS):
            self.clear_slot(i)

        found_pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == PROCESS_NAME.lower():
                    found_pids.append(proc.info['pid'])
                    if len(found_pids) >= MAX_CLIENTS: break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if not found_pids:
            self.log("找不到任何執行中的 sadsa.exe！")
            return

        self.log(f"共找到 {len(found_pids)} 個進程。正在綁定並掃描位址...")
        for i in range(len(found_pids)):
            pid = found_pids[i]
            slot = self.slot_widgets[i]
            slot["pid"] = pid
            
            # --- (★★★ 已修改 2/2 ★★★) ---
            # 更新綁定時的文字，包含 "窗口 {i+1}:"
            slot["status_label"].config(text=f"窗口 {i+1}: 已綁定 (PID: {pid})", foreground="green")
            # --- (★★★ 修改結束 ★★★) ---
            
            self.bind_and_cache_addresses(i)

    def clear_slot(self, slot_index):
        """清除一個窗口的狀態"""
        slot = self.slot_widgets[slot_index]
        slot["pid"] = None
        
        slot["walk_patch_address"] = None
        slot["walk_original_byte_cache"] = None
        slot["speed_patch_address_1"] = None
        slot["speed_patch_address_2"] = None
        slot["speed_original_bytes_1"] = None
        slot["speed_original_bytes_2"] = None
        slot["noclip_patch_address"] = None
        slot["noclip_original_bytes_cache"] = None

        # --- (★★★ 已修改 3/2 ★★★) ---
        # 更新清除時的文字
        slot["status_label"].config(text=f"窗口 {slot_index+1}: 未綁定", foreground="grey")
        # --- (★★★ 修改結束 ★★★) ---
        
        slot["walk_checkbox"].config(state="disabled")
        slot["walk_check_var"].set(0)
        slot["speed_checkbox"].config(state="disabled")
        slot["speed_check_var"].set(0)
        slot["noclip_checkbox"].config(state="disabled")
        slot["noclip_check_var"].set(0)

    def bind_and_cache_addresses(self, slot_index):
        """(綁定時調用) 掃描並快取所有位址"""
        slot = self.slot_widgets[slot_index]
        pid = slot["pid"]
        walk_enabled, speed_enabled, noclip_enabled = False, False, False

        try:
            pm = pymem.Pymem(pid)
            module = pymem.process.module_from_name(pm.process_handle, PROCESS_NAME)
            if not module:
                self.log(f"錯誤 (PID: {pid}): 找不到 {PROCESS_NAME} 模組。")
                # --- (★★★ 已修改 4/2 ★★★) ---
                slot["status_label"].config(text=f"窗口 {slot_index+1}: 找不到模組", foreground="red")
                return

            # --- 1. 處理「快速行走」 (AOB 1) ---
            try:
                found_address_walk = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_WALK)
                if not found_address_walk:
                    self.log(f"警告 (PID: {pid}): 找不到「快速行走」特徵碼！")
                else:
                    patch_address = found_address_walk + WALK_PATCH_OFFSET
                    slot["walk_patch_address"] = patch_address
                    current_byte = pm.read_bytes(patch_address, 1)[0]
                    slot["walk_original_byte_cache"] = current_byte 
                    
                    if current_byte == WALK_PATCHED_BYTE:
                        slot["walk_check_var"].set(1)
                    else:
                        slot["walk_check_var"].set(0)
                    
                    self.log(f"  > (PID: {pid}) 找到「行走」位址 @ 0x{patch_address:X} (原始: {hex(current_byte)})")
                    walk_enabled = True
            except Exception as e:
                 self.log(f"  > (PID: {pid}) 掃描「行走」時出錯: {e}")

            # --- 2. 處理「遊戲加速」 (AOB 2 & 3) ---
            try:
                found_address_speed_1 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_1)
                found_address_speed_2 = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_SPEED_2)
                
                if not found_address_speed_1 or not found_address_speed_2:
                    self.log(f"警告 (PID: {pid}): 找不到「遊戲加速」特徵碼！")
                else:
                    addr1 = found_address_speed_1 + SPEED_AOB_OFFSET
                    addr2 = found_address_speed_2 + SPEED_AOB_OFFSET
                    orig_bytes_1 = pm.read_bytes(addr1, len(NOP_PATCH))
                    orig_bytes_2 = pm.read_bytes(addr2, len(NOP_PATCH))
                    slot["speed_patch_address_1"] = addr1
                    slot["speed_patch_address_2"] = addr2
                    slot["speed_original_bytes_1"] = orig_bytes_1
                    slot["speed_original_bytes_2"] = orig_bytes_2
                    self.log(f"  > (PID: {pid}) 找到「加速1」位址 @ 0x{addr1:X} (原始: {orig_bytes_1.hex()})")
                    self.log(f"  > (PID: {pid}) 找到「加速2」位址 @ 0x{addr2:X} (原始: {orig_bytes_2.hex()})")

                    if orig_bytes_1 == NOP_PATCH:
                        slot["speed_check_var"].set(1)
                    else:
                        slot["speed_check_var"].set(0)
                    
                    speed_enabled = True
            except Exception as e:
                 self.log(f"  > (PID: {pid}) 掃描「加速」時出錯: {e}")

            # --- 3. 處理「穿牆行走」 (AOB 4) ---
            try:
                found_address_noclip = pymem.pattern.pattern_scan_module(pm.process_handle, module, AOB_PATTERN_NOCLIP)
                if not found_address_noclip:
                    self.log(f"警告 (PID: {pid}): 找不到「穿牆行走」特徵碼！")
                else:
                    patch_address = found_address_noclip + NOCLIP_PATCH_OFFSET
                    slot["noclip_patch_address"] = patch_address
                    current_bytes = pm.read_bytes(patch_address, len(NOCLIP_PATCHED_BYTES))
                    slot["noclip_original_bytes_cache"] = current_bytes 
                    
                    if current_bytes == NOCLIP_PATCHED_BYTES:
                        slot["noclip_check_var"].set(1)
                    else:
                        slot["noclip_check_var"].set(0)
                        
                    self.log(f"  > (PID: {pid}) 找到「穿牆」位址 @ 0x{patch_address:X} (原始: {current_bytes.hex()})")
                    noclip_enabled = True
            except Exception as e:
                 self.log(f"  > (PID: {pid}) 掃描「穿牆」時出錯: {e}")

            # --- 4. 啟用 GUI ---
            if walk_enabled: slot["walk_checkbox"].config(state="normal")
            if speed_enabled: slot["speed_checkbox"].config(state="normal")
            if noclip_enabled: slot["noclip_checkbox"].config(state="normal")
                
        except Exception as e:
            self.log(f"掃描時出錯 (PID: {pid}): {e}")
            # --- (★★★ 已修改 5/2 ★★★) ---
            slot["status_label"].config(text=f"窗口 {slot_index+1}: 掃描失敗", foreground="red")
            
    # (後續的 on_walk_toggle, on_speed_toggle, on_noclip_toggle 
    #  perform_write_byte, perform_write_bytes, on_closing 
    #  函式皆無需修改)

    def on_walk_toggle(self, slot_index):
        """(快速行走) 點擊開關時調用"""
        slot = self.slot_widgets[slot_index]
        pid = slot["pid"]
        patch_address = slot["walk_patch_address"]
        is_checked = slot["walk_check_var"].get()
        original_byte = slot["walk_original_byte_cache"]

        if pid is None or patch_address is None or original_byte is None:
            self.log(f"錯誤：窗口 {slot_index+1} 未綁定或未找到「行走」位址。")
            slot["walk_check_var"].set(not is_checked)
            return

        target_byte = WALK_PATCHED_BYTE if is_checked else original_byte
        action_text = "修補" if is_checked else "還原"
        
        self.log(f"--- 窗口 {slot_index+1} (PID: {pid}): 快速行走 {action_text} ---")
        self.log(f"  > 操作快取位址: 0x{patch_address:X}")
        
        success = self.perform_write_byte(pid, patch_address, target_byte)
        if not success:
            self.log(f"操作失敗！將開關恢復原狀。")
            slot["walk_check_var"].set(not is_checked)

    def on_speed_toggle(self, slot_index):
        """(遊戲加速) 點擊開關時調用 (NOP 補丁)"""
        slot = self.slot_widgets[slot_index]
        pid = slot["pid"]
        is_checked = slot["speed_check_var"].get()
        action_text = "啟用 (NOP)" if is_checked else "還原 (ADD)"
        
        addr1 = slot["speed_patch_address_1"]
        addr2 = slot["speed_patch_address_2"]
        orig1 = slot["speed_original_bytes_1"]
        orig2 = slot["speed_original_bytes_2"]
        
        if pid is None or addr1 is None or addr2 is None or orig1 is None or orig2 is None:
            self.log(f"錯誤：窗口 {slot_index+1} 未綁定或未找到「加速」位址。")
            slot["speed_check_var"].set(not is_checked)
            return
            
        self.log(f"--- 窗口 {slot_index+1} (PID: {pid}): 遊戲加速 {action_text} ---")

        if is_checked:
            target_bytes_1, target_bytes_2 = NOP_PATCH, NOP_PATCH
        else:
            target_bytes_1, target_bytes_2 = orig1, orig2

        self.log(f"  > G正在寫入 位址 1 (0x{addr1:X})...")
        s1 = self.perform_write_bytes(pid, addr1, target_bytes_1)
        self.log(f"  > 正在寫入 位址 2 (0x{addr2:X})...")
        s2 = self.perform_write_bytes(pid, addr2, target_bytes_2)
        
        if not s1 or not s2:
            self.log(f"操作失敗！將開關恢復原狀。")
            slot["speed_check_var"].set(not is_checked)

    def on_noclip_toggle(self, slot_index):
        """(穿牆行走) 點擊開關時調用"""
        slot = self.slot_widgets[slot_index]
        pid = slot["pid"]
        patch_address = slot["noclip_patch_address"]
        is_checked = slot["noclip_check_var"].get()
        original_bytes = slot["noclip_original_bytes_cache"]
        
        if pid is None or patch_address is None or original_bytes is None:
            self.log(f"錯誤：窗口 {slot_index+1} 未綁定或未找到「穿牆」位址。")
            slot["noclip_check_var"].set(not is_checked)
            return

        target_bytes = NOCLIP_PATCHED_BYTES if is_checked else original_bytes
        action_text = "修補 (mov 0)" if is_checked else "還原"
        
        self.log(f"--- 窗口 {slot_index+1} (PID: {pid}): 穿牆行走 {action_text} ---")
        self.log(f"  > 操作快取位址: 0x{patch_address:X}")
        
        success = self.perform_write_bytes(pid, patch_address, target_bytes)
        if not success:
            self.log(f"操作失敗！將開關恢復原狀。")
            slot["noclip_check_var"].set(not is_checked)

    def perform_write_byte(self, pid, patch_address, target_byte):
        """對指定的PID和位址執行「單次」寫入 (用於快速行走)"""
        try:
            pm = pymem.Pymem(pid)
            current_byte = pm.read_bytes(patch_address, 1)[0]
            if current_byte == target_byte:
                self.log(f"  > (PID: {pid}) 狀態已是 0x{target_byte:X}。")
                return True
            
            pm.write_uchar(patch_address, target_byte)
            written_byte = pm.read_bytes(patch_address, 1)[0]
            
            if written_byte == target_byte:
                self.log(f"  > 成功! (PID: {pid}) 修改為: 0x{target_byte:X}")
                return True
            else:
                self.log(f"  > 失敗! (PID: {pid}) 寫入後驗證失敗。")
                return False
                
        except Exception as e:
            self.log(f"寫入時出錯 (PID: {pid}): {e}")
            return False
            
    def perform_write_bytes(self, pid, patch_address, target_bytes):
        """對指定的PID和位址執行「多位元組」寫入"""
        try:
            pm = pymem.Pymem(pid)
            current_bytes = pm.read_bytes(patch_address, len(target_bytes))
            if current_bytes == target_bytes:
                self.log(f"  > (PID: {pid}) 狀態已是 {target_bytes.hex()}。")
                return True
            
            pm.write_bytes(patch_address, target_bytes, len(target_bytes))
            written_bytes = pm.read_bytes(patch_address, len(target_bytes))
            
            if written_bytes == target_bytes:
                self.log(f"  > S成功! (PID: {pid}) 修改為: {target_bytes.hex()}")
                return True
            else:
                self.log(f"  > 失敗! (PID: {pid}) 寫入後驗證失敗。")
                return False
                
        except Exception as e:
            self.log(f"寫入多位元組時出錯 (PID: {pid}): {e}")
            return False

    def on_closing(self):
        """當使用者關閉GUI視窗時"""
        self.log("正在關閉程式...")
        self.destroy()

# --- 程式主體 ---
if __name__ == "__main__":
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.user32.MessageBoxW(0, "此程式必須以「系統管理員」權限執行才能讀寫記憶體。", "權限錯誤", 0x10)
    else:
        app = GamePatcherApp()
        app.mainloop()