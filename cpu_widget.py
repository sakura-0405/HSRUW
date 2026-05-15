import tkinter as tk
import psutil

class AdvancedCPUWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("P/E Core Monitor")
        
        # 視窗置頂與無邊框設定
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.configure(bg="#1e1e1e")
        
        # 自動偵測大小核分配（適用於 Intel 12代以上，如你的 i5-14400 擁有 6P+4E=20執行緒）
        self.detect_cores()
        
        self.labels = {}
        self.setup_ui()
        
        # 建立右鍵選單
        self.create_context_menu()
        
        # 滑鼠事件綁定
        self.root.bind("<Button-1>", self.start_drag)      # 左鍵點擊（準備拖曳）
        self.root.bind("<B1-Motion>", self.drag_window)    # 左鍵拖曳
        self.root.bind("<Button-3>", self.show_menu)       # 右鍵點擊（跳出選單）
        
        # 開始輪詢更新數據
        self.update_cpu_status()

    def detect_cores(self):
        """ 自動辨識 P-Core 與 E-Core 的邏輯執行緒數量 """
        self.total_logical = psutil.cpu_count(logical=True)
        self.total_physical = psutil.cpu_count(logical=False)
        
        # 以常見的 Intel 異質架構估算：
        # P-core 支援超執行緒（1核2執行緒），E-core 不支援（1核1執行緒）
        # 聯立方程式解出 P 核心物理數 = 總執行緒數 - 總實體核心數
        p_physical = self.total_logical - self.total_physical
        self.p_logical_count = p_physical * 2
        self.e_logical_count = self.total_logical - self.p_logical_count

    def setup_ui(self):
        # --- P-Core 區域 ---
        p_frame = tk.LabelFrame(self.root, text=" Performance Cores (P-Core) ", fg="#64B5F6", bg="#1e1e1e", font=("Arial", 9, "bold"))
        p_frame.pack(padx=10, pady=5, fill="x")
        
        for i in range(self.p_logical_count):
            row = i // 6
            col = i % 6
            lbl = tk.Label(p_frame, text=f"P{i}\n0%", font=("Arial", 8, "bold"), width=5, height=2, bg="#ffffff", fg="#000000", relief="groove")
            lbl.grid(row=row, column=col, padx=3, pady=3)
            
            # 讓每一個子標籤點擊右鍵時，也能觸發視窗的右鍵選單
            lbl.bind("<Button-3>", self.show_menu)
            lbl.bind("<Button-1>", self.start_drag)
            lbl.bind("<B1-Motion>", self.drag_window)
            self.labels[i] = lbl

        # --- E-Core 區域 ---
        if self.e_logical_count > 0:
            e_frame = tk.LabelFrame(self.root, text=" Efficiency Cores (E-Core) ", fg="#81C784", bg="#1e1e1e", font=("Arial", 9, "bold"))
            e_frame.pack(padx=10, pady=5, fill="x")
            
            for i in range(self.e_logical_count):
                idx = self.p_logical_count + i
                row = i // 6
                col = i % 6
                lbl = tk.Label(e_frame, text=f"E{i}\n0%", font=("Arial", 8, "bold"), width=5, height=2, bg="#ffffff", fg="#000000", relief="groove")
                lbl.grid(row=row, column=col, padx=3, pady=3)
                
                # 同步綁定事件
                lbl.bind("<Button-3>", self.show_menu)
                lbl.bind("<Button-1>", self.start_drag)
                lbl.bind("<B1-Motion>", self.drag_window)
                self.labels[idx] = lbl

    def create_context_menu(self):
        """ 建立右鍵彈出選單 """
        self.menu = tk.Menu(self.root, tearoff=0)
        # 加入「關閉程式」選項，點擊後執行 root.destroy
        self.menu.add_command(label="關閉核心監控器", command=self.root.destroy)
        self.menu.add_separator()
        self.menu.add_command(label="取消", command=lambda: None)

    def show_menu(self, event):
        """ 在滑鼠點擊的位置彈出選單 """
        self.menu.post(event.x_root, event.y_root)

    def get_color(self, percentage):
        if percentage < 50:
            ratio = percentage / 50.0
            r = int(255 - (255 * ratio))
            g = int(255 - (45 * ratio))
            b = int(255 - (255 * ratio))
        else:
            ratio = (percentage - 50) / 50.0
            r = int(255 * ratio)
            g = int(210 * (1 - ratio))
            b = 0
        return f"#{r:02x}{g:02x}{b:02x}"

    def update_cpu_status(self):
        cpu_percentages = psutil.cpu_percent(percpu=True)
        
        for idx, percent in enumerate(cpu_percentages):
            if idx in self.labels:
                color = self.get_color(percent)
                label_text = f"P{idx}\n{int(percent)}%" if idx < self.p_logical_count else f"E{idx - self.p_logical_count}\n{int(percent)}%"
                self.labels[idx].config(
                    text=label_text, 
                    bg=color,
                    fg="#ffffff" if percent > 30 else "#000000"
                )
                
        self.root.after(1000, self.update_cpu_status)

    # 滑鼠拖曳功能邏輯
    def start_drag(self, event):
        self.x = event.x
        self.y = event.y

    def drag_window(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedCPUWidget(root)
    root.mainloop()