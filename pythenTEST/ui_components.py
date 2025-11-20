# ui_components.py
# 儲存可重複使用的 tkinter 元件

import tkinter as tk
from tkinter import ttk

class ScrollableFrame(ttk.Frame):
    """一個可滾動的 Frame (垂直或水平)"""
    def __init__(self, container, orient="vertical", *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        self.orient = orient 
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        
        if self.orient == "vertical":
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
            self.canvas.configure(yscrollcommand=self.scrollbar.set)
            self.scrollbar.pack(side="right", fill="y")
        else: # horizontal
            self.scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
            self.canvas.configure(xscrollcommand=self.scrollbar.set)
            self.scrollbar.pack(side="bottom", fill="x")
            
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.inner_frame = ttk.Frame(self.canvas)

        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.inner_frame.bind("<MouseWheel>", self.on_mouse_wheel)
            
    def on_mouse_wheel(self, event):
        if self.orient == "vertical":
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else: 
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")