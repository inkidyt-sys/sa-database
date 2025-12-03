# logger.py
# 日誌系統，用於記錄程式運行狀態與錯誤

import os
import time
from datetime import datetime

class SimpleLogger:
    """簡單的檔案+控制台日誌系統"""
    
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 每天一個新日誌檔案
        today = datetime.now().strftime("%Y%m%d")
        self.log_file = os.path.join(log_dir, f"dsa_helper_{today}.log")
    
    def _write(self, level, msg):
        """寫入日誌"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] [{level}] {msg}"
        
        # 控制台輸出
        print(full_msg)
        
        # 檔案輸出
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(full_msg + "\n")
        except Exception as e:
            print(f"[WARNING] 無法寫入日誌檔案: {e}")
    
    def info(self, msg):
        self._write("INFO", msg)
    
    def warning(self, msg):
        self._write("WARNING", msg)
    
    def error(self, msg):
        self._write("ERROR", msg)
    
    def debug(self, msg):
        self._write("DEBUG", msg)

# 全域日誌實例
logger = SimpleLogger()
