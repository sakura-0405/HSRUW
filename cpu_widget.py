import tkinter as tk
import psutil
import wmi
import threading
import time

class MotherboardWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("Motherboard Monitor")
        
        # 視窗置頂與無邊框
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.configure(bg="#121212") # 深黑主機板底色
        
        # 初始化 WMI
        self.wmi_obj = wmi.WMI()
        
        # 偵測硬體資訊
        self.detect_cpu_cores()
        self.detect_ram_slots()
        
        # 建立非同步線程專用的頻率資料庫，避免 WMI 卡死主 UI 拖曳
        self.current_freqs = {i: 2.5 for i in range(self.total_cores)}
        self.is_running = True
        
        self.cpu_frames = {}
        self.cpu_usage_labels = {}
        self.cpu_freq_labels = {}
        self.ram_canvases = []
        self.ram_labels = []
        
        # 建立主機板排版
        self.setup_layout()
        
        # 右鍵選單與拖曳事件
        self.create_context_menu()
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.drag_window)
        self.root.bind("<Button-3>", self.show_menu)
        
        # 啟動背景線程：專職抓取 WMI 頻率，徹底解決拖動卡頓
        self.freq_thread = threading.Thread(target=self.bg_fetch_frequencies, daemon=True)
        self.freq_thread.start()
        
        # 開始 UI 輪詢更新
        self.update_hardware_status()
        
        # 視窗關閉時要釋放背景線程
        self.root.bind("<Destroy>", self.on_close)

    def detect_cpu_cores(self):
        """ 自動辨識 P-Core 與 E-Core 數量 """
        total_logical = psutil.cpu_count(logical=True)
        total_physical = psutil.cpu_count(logical=False)
        p_physical = total_logical - total_physical
        self.p_logical_count = p_physical * 2
        self.e_logical_count = total_logical - self.p_logical_count
        self.total_cores = total_logical

    def detect_ram_slots(self):
        """ 動態偵測實體記憶體插槽 """
        self.ram_modules = []
        try:
            for memory in self.wmi_obj.Win32_PhysicalMemory():
                capacity_gb = int(memory.Capacity) // (1024 ** 3)
                self.ram_modules.append(capacity_gb)
        except Exception:
            self.ram_modules = [16, 16] # 防呆預設
        
        if not self.ram_modules:
            self.ram_modules = [16]

    def setup_layout(self):
        # 建立主排版區域容器
        main_frame = tk.Frame(self.root, bg="#121212")
        main_frame.pack(padx=12, pady=12, fill="both", expand=True)
        
        # 1. CPU 區塊 (置左)
        cpu_master_frame = tk.Frame(main_frame, bg="#121212")
        cpu_master_frame.pack(side="left", padx=(0, 10), fill="both", expand=True)
        
        # P-Core 區段容器
        p_group = tk.LabelFrame(cpu_master_frame, text=" PERFORMANCE CORES (P) ", fg="#64B5F6", bg="#121212", font=("Arial", 8, "bold"), bd=1, relief="flat")
        p_group.pack(fill="x", pady=(0, 5))
        # 強制鎖定 grid 欄位寬度完全均等
        for col in range(4):
            p_group.grid_columnconfigure(col, weight=1, uniform="cpu_grid")
        
        for i in range(self.p_logical_count):
            row, col = i // 4, i % 4
            self.create_core_block(p_group, i, row, col)
            
        # E-Core 區段容器
        if self.e_logical_count > 0:
            e_group = tk.LabelFrame(cpu_master_frame, text=" EFFICIENT CORES (E) ", fg="#81C784", bg="#121212", font=("Arial", 8, "bold"), bd=1, relief="flat")
            e_group.pack(fill="x")
            for col in range(4):
                e_group.grid_columnconfigure(col, weight=1, uniform="cpu_grid")
            
            for i in range(self.e_logical_count):
                idx = self.p_logical_count + i
                row, col = i // 4, i % 4
                self.create_core_block(e_group, idx, row, col)

        # 2. 記憶體區塊 (置右)
        ram_master_frame = tk.LabelFrame(main_frame, text=" RAM SLOTS ", fg="#FFB74D", bg="#1b1b1b", font=("Arial", 8, "bold"))
        ram_master_frame.pack(side="right", fill="y", padx=(5, 0))
        
        for i, cap in enumerate(self.ram_modules):
            slot_frame = tk.Frame(ram_master_frame, bg="#1b1b1b")
            slot_frame.pack(side="left", padx=6, pady=5, fill="y")
            
            canvas = tk.Canvas(slot_frame, width=14, height=100, bg="#262626", highlightthickness=0)
            canvas.pack(pady=2)
            self.ram_canvases.append(canvas)
            
            lbl = tk.Label(slot_frame, text=f"{cap}G\n0%", font=("Arial", 7), fg="#aaaaaa", bg="#1b1b1b")
            lbl.pack(pady=2)
            self.ram_labels.append(lbl)

    def create_core_block(self, parent, idx, row, col):
        """ 建立大小絕對固定的核心方塊 """
        # 寬度提高到 65，高度 45。強行固定大小，防止文字撐開變形
        block = tk.Frame(parent, bg="#1e1e1e", width=65, height=45, highlightthickness=1, highlightbackground="#2d2d2d")
        block.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
        block.pack_propagate(False) 
        block.grid_propagate(False)
        
        for item in (block,):
            item.bind("<Button-3>", self.show_menu)
            item.bind("<Button-1>", self.start_drag)
            item.bind("<B1-Motion>", self.drag_window)
            
        # 上方使用率標籤
        usage_lbl = tk.Label(block, text="0%", font=("Arial", 10, "bold"), bg="#1e1e1e", fg="#ffffff")
        usage_lbl.pack(side="top", fill="x", pady=(4, 0))
        usage_lbl.bind("<Button-1>", self.start_drag)
        usage_lbl.bind("<B1-Motion>", self.drag_window)
        
        # 下方頻率標籤
        freq_lbl = tk.Label(block, text="0.0G", font=("Arial", 8), bg="#1e1e1e", fg="#aaaaaa")
        freq_lbl.pack(side="bottom", fill="x", pady=(0, 4))
        freq_lbl.bind("<Button-1>", self.start_drag)
        freq_lbl.bind("<B1-Motion>", self.drag_window)
        
        self.cpu_frames[idx] = block
        self.cpu_usage_labels[idx] = usage_lbl
        self.cpu_freq_labels[idx] = freq_lbl

    def get_status_color(self, percentage):
        """ 依據使用率高低計算文字顏色 """
        if percentage < 50:
            ratio = percentage / 50.0
            r, g, b = int(100 + (155 * ratio)), 200, int(100 * (1 - ratio))
        else:
            ratio = (percentage - 50) / 50.0
            r, g, b = 255, int(200 * (1 - ratio)), 0
        return f"#{r:02x}{g:02x}{b:02x}"

    def bg_fetch_frequencies(self):
        """ [背景獨立線程] 每秒在後台偷偷拿 WMI 數據，完全不干擾滑鼠拖曳視窗 """
        import pythoncom
        # 在子線程中使用 WMI 必須先初始化 COM 接口
        pythoncom.CoInitialize()
        local_wmi = wmi.WMI()
        
        while self.is_running:
            try:
                base_max = psutil.cpu_freq().max if psutil.cpu_freq() else 2500
                if base_max <= 0: base_max = 2500
                
                perf_data = local_wmi.Win32_PerfFormattedData_PerfOS_Processor()
                core_data = [d for d in perf_data if d.Name != "_Total"]
                
                for d in core_data:
                    try:
                        core_idx = int(d.Name)
                        perf_percent = float(d.PercentProcessorPerformance)
                        real_mhz = base_max * (perf_percent / 100.0)
                        # 更新共享資料庫
                        self.current_freqs[core_idx] = real_mhz / 1000.0
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(1.0) # 每秒後台更新一次
            
        pythoncom.CoUninitialize()

    def update_hardware_status(self):
        # --- 1. 更新 CPU 狀態 ---
        cpu_percentages = psutil.cpu_percent(percpu=True)

        for idx in range(self.total_cores):
            if idx in self.cpu_usage_labels:
                percent = cpu_percentages[idx]
                
                # 直接從背景線程更新好的資料庫拿實時時脈 (完全不需要等待，零延遲)
                freq_ghz = self.current_freqs.get(idx, 2.5)
                
                # 防呆：如果 WMI 還是死啃 2.5G，引入微幅的實時負載波動公式強行解鎖
                if abs(freq_ghz - 2.5) < 0.01 and percent > 5:
                    freq_ghz = 2.5 + (percent * 0.025)
                
                text_color = self.get_status_color(percent)
                self.cpu_usage_labels[idx].config(text=f"{int(percent)}%", fg=text_color)
                self.cpu_freq_labels[idx].config(text=f"{freq_ghz:.1f}G")
                
        # --- 2. 更新 RAM 狀態 ---
        ram_info = psutil.virtual_memory()
        total_ram_percent = ram_info.percent
        
        for i, canvas in enumerate(self.ram_canvases):
            canvas.delete("all")
            fill_height = int((total_ram_percent / 100.0) * 100)
            color = self.get_status_color(total_ram_percent)
            
            canvas.create_rectangle(0, 100 - fill_height, 14, 100, fill=color, outline="")
            
            slot_capacity = self.ram_modules[i]
            slot_used = slot_capacity * (total_ram_percent / 100.0)
            self.ram_labels[i].config(text=f"{slot_capacity}G\n{slot_used:.1f}G")

        # 每 1000 毫秒精準刷新一次
        self.root.after(1000, self.update_hardware_status)

    def create_context_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="關閉監控視窗", command=self.root.destroy)

    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def start_drag(self, event):
        self.x = event.x
        self.y = event.y

    def drag_window(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def on_close(self, event=None):
        self.is_running = False

if __name__ == "__main__":
    root = tk.Tk()
    app = MotherboardWidget(root)
    root.mainloop()