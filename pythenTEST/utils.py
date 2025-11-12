# utils.py
# 儲存通用輔助函式

import os
import ctypes
try:
    import ctypes.wintypes
except ImportError:
    pass # 稍後在 is_admin 中處理
    
import pymem

def is_admin():
    """檢查程式是否以系統管理員權限執行"""
    try: 
        return os.getuid() == 0
    except AttributeError: 
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False # 如果 ctypes 也失敗，假定不是管理員

def num_to_chinese(num):
    """將數字 1-5 轉換為中文"""
    return ["一", "二", "三", "四", "五"][num - 1]

def format_elements(earth, water, fire, wind):
    """輔助函式：格式化屬性字串"""
    parts = []
    if earth > 0: parts.append(f"地{earth // 10}")
    if water > 0: parts.append(f"水{water // 10}")
    if fire > 0:  parts.append(f"火{fire // 10}")
    if wind > 0:  parts.append(f"風{wind // 10}")
    return " ".join(parts) if parts else "無"

def read_big5_string(pm: pymem.Pymem, address: int, byte_length: int) -> str:
    """輔助函式：從 pymem 物件讀取 Big5 字串"""
    try:
        bytes_read = pm.read_bytes(address, byte_length)
        bytes_read = bytes_read.split(b'\x00')[0]
        return bytes_read.decode('big5', errors='ignore')
    except Exception as e:
        print(f"  > (PID: {pm.process_id}) 讀取字串失敗 @ 0x{address:X}: {e}")
        return ""