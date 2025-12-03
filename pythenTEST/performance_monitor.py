# performance_monitor.py
# 效能監控系統

import time
import threading
import psutil
import os

class PerformanceMonitor:
    """監控應用程式效能指標"""
    
    def __init__(self):
        self.start_time = time.time()
        self.process = psutil.Process(os.getpid())
        
        # 統計數據
        self.read_count = 0
        self.read_errors = 0
        self.read_time_total = 0.0
        self.memory_peak = 0
        self.cpu_percent_current = 0.0
        
        # 鎖
        self._lock = threading.Lock()
    
    def record_read(self, elapsed_time, success=True):
        """記錄一次記憶體讀取操作"""
        with self._lock:
            if success:
                self.read_count += 1
                self.read_time_total += elapsed_time
            else:
                self.read_errors += 1
    
    def update_metrics(self):
        """更新系統指標"""
        try:
            with self._lock:
                # CPU 使用率（百分比）
                self.cpu_percent_current = self.process.cpu_percent(interval=0.1)
                
                # 記憶體使用量（MB）
                mem_info = self.process.memory_info()
                current_mem = mem_info.rss / (1024 * 1024)
                if current_mem > self.memory_peak:
                    self.memory_peak = current_mem
        except Exception as e:
            from logger import logger
            logger.warning(f"Performance monitor error: {e}")
    
    def get_stats(self):
        """取得統計數據"""
        with self._lock:
            elapsed = time.time() - self.start_time
            avg_read_time = (self.read_time_total / self.read_count * 1000) if self.read_count > 0 else 0
            read_rate = self.read_count / elapsed if elapsed > 0 else 0
            error_rate = (self.read_errors / (self.read_count + self.read_errors) * 100) if (self.read_count + self.read_errors) > 0 else 0
            
            mem_info = self.process.memory_info()
            current_mem = mem_info.rss / (1024 * 1024)
            
            return {
                "uptime": elapsed,
                "reads_total": self.read_count,
                "read_errors": self.read_errors,
                "avg_read_time": avg_read_time,
                "read_rate": read_rate,
                "error_rate": error_rate,
                "cpu_percent": self.cpu_percent_current,
                "memory_current": current_mem,
                "memory_peak": self.memory_peak
            }
    
    def format_stats(self):
        """格式化統計數據為字串"""
        stats = self.get_stats()
        uptime_h = int(stats["uptime"] // 3600)
        uptime_m = int((stats["uptime"] % 3600) // 60)
        uptime_s = int(stats["uptime"] % 60)
        
        return (
            f"運行時間: {uptime_h}h {uptime_m}m {uptime_s}s | "
            f"讀取: {stats['reads_total']} (失敗: {stats['read_errors']}) | "
            f"平均延遲: {stats['avg_read_time']:.2f}ms | "
            f"CPU: {stats['cpu_percent']:.1f}% | "
            f"記憶體: {stats['memory_current']:.1f}MB (峰值: {stats['memory_peak']:.1f}MB)"
        )

# 全域監控器
monitor = PerformanceMonitor()
