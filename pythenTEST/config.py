# config.py
# 配置管理模組

import json
import os
from datetime import datetime

CONFIG_FILE = "dsa_helper_config.json"

DEFAULT_CONFIG = {
    "ui": {
        "default_refresh_rate": "3s",
        "default_zoom": "100%",
        "auto_height_enabled": True,
        "remember_window_size": True,
        "last_window_width": 1050,
        "last_window_height": 280
    },
    "advanced": {
        "enable_logging": True,
        "log_level": "INFO",  # DEBUG, INFO, WARNING, ERROR
        "enable_memory_cache": True,
        "memory_cache_ttl_sec": 2.0
    },
    "memory": {
        "aob_scan_timeout": 10.0,  # 秒
        "max_retry_count": 3,
        "retry_delay_sec": 0.5
    }
}

class Config:
    def __init__(self):
        self.data = self.load()
    
    def load(self):
        """從檔案加載配置，不存在則使用預設"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load config: {e}, using default")
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()
    
    def save(self):
        """保存配置到檔案"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            print(f"Config saved: {CONFIG_FILE}")
        except Exception as e:
            print(f"Failed to save config: {e}")
    
    def get(self, key, default=None):
        """遞迴取得配置值，支援 dot notation"""
        keys = key.split(".")
        val = self.data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        return val if val is not None else default
    
    def set(self, key, value):
        """遞迴設定配置值，支援 dot notation"""
        keys = key.split(".")
        target = self.data
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

# 全域配置實例
config = Config()
