import os
import shutil
import json
import tkinter as tk
from pathlib import Path
from threading import Thread, Event
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
import datetime
from typing import List, Dict, Optional, Tuple, Union

class CircularProgressBar:
    def __init__(self, parent, diameter=200, line_width=15):
        self.canvas = tk.Canvas(
            parent,
            width=diameter,
            height=diameter,
            bg='#f8f9fa',  # 使用浅色主题的背景色
            highlightthickness=0
        )
        self.diameter = diameter
        self.line_width = line_width
        self.center = diameter // 2
        self.radius = (diameter - line_width) // 2 - 5
        self.progress = 0
        
        # 绑定配置变化事件，实现自动调整大小
        self.canvas.bind('<Configure>', self.on_configure)

        # 绘制背景环
        self.bg_arc = self.canvas.create_arc(
            self.line_width/2, self.line_width/2,
            diameter - self.line_width/2, diameter - self.line_width/2,
            start=0, extent=359.9,
            style="arc", outline="#e0e0e0", width=line_width
        )

        # 绘制进度环
        self.progress_arc = self.canvas.create_arc(
            self.line_width/2, self.line_width/2,
            diameter - self.line_width/2, diameter - self.line_width/2,
            start=90, extent=0,  # 从顶部开始
            style="arc", outline="#4CAF50", width=line_width,
            tags="progress"
        )

        # 进度文字
        self.text = self.canvas.create_text(
            self.center, self.center,
            text="0%",
            font=(("微软雅黑", 28, "bold")),
            fill="#2196F3"
        )
    
    def on_configure(self, event):
        """处理Canvas大小变化事件"""
        # 获取新的Canvas尺寸
        new_width = event.width
        new_height = event.height
        
        # 计算新的直径（取宽高中的较小值）
        new_diameter = min(new_width, new_height) - 20  # 留一些边距
        
        # 只在尺寸变化时更新
        if new_diameter != self.diameter:
            self.diameter = new_diameter
            self.center = new_diameter // 2
            self.radius = (new_diameter - self.line_width) // 2 - 5
            
            # 更新Canvas尺寸
            self.canvas.config(width=new_diameter, height=new_diameter)
            
            # 重新绘制背景环
            self.canvas.coords(self.bg_arc, 
                              self.line_width/2, self.line_width/2,
                              new_diameter - self.line_width/2, new_diameter - self.line_width/2)
            
            # 重新绘制进度环
            self.canvas.coords(self.progress_arc, 
                              self.line_width/2, self.line_width/2,
                              new_diameter - self.line_width/2, new_diameter - self.line_width/2)
            
            # 更新进度文字位置和大小
            font_size = max(12, min(28, new_diameter // 8))  # 根据直径调整字体大小
            self.canvas.coords(self.text, self.center, self.center)
            self.canvas.itemconfig(self.text, font=(("微软雅黑", font_size, "bold")))
            
            # 重新计算进度角度
            angle = -self.progress * 3.6
            self.canvas.itemconfig(self.progress_arc, extent=angle)

    def update_progress(self, value):
        """更新进度（0-100）"""
        self.progress = max(0, min(100, value))
        angle = -self.progress * 3.6  # 逆时针旋转
        self.canvas.itemconfig(self.progress_arc, extent=angle)
        self.canvas.itemconfig(self.text, text=f"{int(self.progress)}%")

class FileOrganizerApp:
    def __init__(self):
        # 配置文件路径
        self.config_file = Path(__file__).parent / "app_config.json"
        
        # 日志文件路径
        self.log_file = Path(__file__).parent / "sorting_logs.json"
        
        # 加载配置
        self.config = self.load_config()
        
        # 皮肤配置字典
        self.skin_configs = {
            "现代薄荷": {
                "theme": "minty",
                "description": "清新现代的薄荷绿色主题",
                "preview": "🌿"
            },
            "蓝色渐变": {
                "theme": "cosmo",
                "description": "蓝色渐变风格，现代简洁",
                "preview": "🔵"
            },
            "经典商务": {
                "theme": "flatly",
                "description": "经典商务蓝色风格，类似IE浏览器的界面",
                "preview": "🌐"
            }
        }
        
        # 获取皮肤设置
        self.current_skin = self.config.get("skin", "现代薄荷")
        self.skin_theme = self.skin_configs.get(self.current_skin, self.skin_configs["现代薄荷"])["theme"]
        
        # 设置窗口大小和位置
        window_size = self.config.get("window_size", (900, 700))
        window_pos = self.config.get("window_pos", (100, 100))
        
        self.window = ttk.Window(
            title="✨ 智能文件分拣工具3.0",
            themename=self.skin_theme,  # 使用配置的皮肤主题
            size=window_size,
            resizable=(True, True)  # 允许调整大小
        )
        
        # 保持默认皮肤样式
        
        # 设置窗口位置
        self.window.geometry(f"{window_size[0]}x{window_size[1]}+{window_pos[0]}+{window_pos[1]}")
        
        # 绑定窗口关闭事件，保存配置
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.stop_event = Event()
        
        # 显示启动动画
        self.show_splash_screen()
        
        # 延迟初始化UI，让启动动画有时间显示
        self.window.after(1500, self.setup_ui)
        
    def load_config(self) -> Dict:
        """加载配置文件
        
        Returns:
            Dict: 配置字典
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载配置失败: {e}")
        return {}
    
    def save_config(self):
        """保存配置文件"""
        try:
            # 获取窗口大小和位置
            window_size = self.window.winfo_width(), self.window.winfo_height()
            window_pos = self.window.winfo_x(), self.window.winfo_y()
            
            # 更新配置
            self.config["window_size"] = window_size
            self.config["window_pos"] = window_pos
            self.config["skin"] = self.current_skin  # 保存皮肤设置
            
            # 保存到文件
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def on_close(self):
        """窗口关闭事件处理"""
        self.save_config()
        self.window.destroy()
    
    def save_profile(self):
        """保存分拣配置"""
        # 获取当前配置
        profile = {
            "source_folder": self.src_entry.get(),
            "destination_folder": self.dest_entry.get(),
            "include_keywords": self.key_entry.get(),
            "exclude_keywords": self.exclude_entry.get(),
            "create_folder": self.create_folder_var.get(),
            "separate_folder": self.separate_folder_var.get(),
            "match_type": self.match_type_var.get(),
            "custom_folder_name": self.custom_folder_entry.get(),
            "combo_keywords": self.combo_key_entry.get()
        }
        
        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            title="保存配置"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(profile, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("成功", "配置已保存")
            except Exception as e:
                messagebox.showerror("错误", f"保存配置失败：{str(e)}")
    
    def load_profile(self):
        """加载分拣配置"""
        # 选择配置文件
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            title="加载配置"
        )
        
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    profile = json.load(f)
                
                # 加载配置
                self.src_entry.delete(0, tk.END)
                self.src_entry.insert(0, profile.get("source_folder", ""))
                
                self.dest_entry.delete(0, tk.END)
                self.dest_entry.insert(0, profile.get("destination_folder", ""))
                
                self.key_entry.delete(0, tk.END)
                self.key_entry.insert(0, profile.get("include_keywords", ""))
                
                self.exclude_entry.delete(0, tk.END)
                self.exclude_entry.insert(0, profile.get("exclude_keywords", ""))
                
                # 加载文件夹创建选项
                self.create_folder_var.set(profile.get("create_folder", True))
                self.separate_folder_var.set(profile.get("separate_folder", True))
                # 加载自定义文件夹名称
                self.custom_folder_entry.delete(0, tk.END)
                self.custom_folder_entry.insert(0, profile.get("custom_folder_name", ""))
                # 加载组合关键词
                self.combo_key_entry.delete(0, tk.END)
                self.combo_key_entry.insert(0, profile.get("combo_keywords", ""))
                # 加载关键词匹配方式选项
                self.match_type_var.set(profile.get("match_type", False))
                
                messagebox.showinfo("成功", "配置已加载")
            except Exception as e:
                messagebox.showerror("错误", f"加载配置失败：{str(e)}")
    
    def show_splash_screen(self):
        """显示启动动画"""
        # 创建启动窗口
        splash = ttk.Toplevel(self.window)
        splash.title("")
        splash.geometry("400x300")
        splash.resizable(False, False)
        splash.transient(self.window)
        splash.grab_set()
        
        # 计算居中位置
        splash.update_idletasks()
        screen_width = splash.winfo_screenwidth()
        screen_height = splash.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 300) // 2
        splash.geometry(f"400x300+{x}+{y}")
        
        # 设置背景
        splash_frame = ttk.Frame(splash, bootstyle="success")
        splash_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加图标和文字
        icon_label = ttk.Label(
            splash_frame,
            text="📁",
            font=("Arial", 60)
        )
        icon_label.pack(pady=(40, 20))
        
        # 标题样式
        title_label = ttk.Label(
            splash_frame,
            text="智能文件分拣工具",
            font=("微软雅黑", 24, "bold"),
            bootstyle="success-inverse"
        )
        title_label.pack(pady=10)
        
        version_label = ttk.Label(
            splash_frame,
            text="版本 3.0",
            font=("微软雅黑", 12),
            bootstyle="success-inverse"
        )
        version_label.pack(pady=5)
        
        # 添加加载动画
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            splash_frame,
            variable=progress_var,
            length=200,
            bootstyle="light-horizontal"
        )
        progress_bar.pack(pady=(30, 10))
        
        # 模拟加载过程
        def update_progress():
            current = progress_var.get()
            if current < 100:
                progress_var.set(current + 5)
                splash.after(50, update_progress)
            else:
                splash.destroy()
        
        update_progress()
    
    def on_drag_enter(self, event):
        """拖放进入事件"""
        event.widget.focus_set()
        return "break"
    
    def on_drag_over(self, event):
        """拖放经过事件"""
        return "break"
    
    def load_logs(self) -> List[Dict]:
        """加载日志文件
        
        Returns:
            List[Dict]: 日志条目列表
        """
        try:
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载日志失败: {e}")
        return []
    
    def save_log(self, log_entry: Dict) -> None:
        """保存日志条目
        
        Args:
            log_entry: 日志条目字典
        """
        try:
            logs = self.load_logs()
            logs.append(log_entry)
            # 只保留最近200条日志，增加日志容量
            if len(logs) > 200:
                logs = logs[-200:]
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存日志失败: {e}")
    
    def _log_error(self, error_type: str, message: str, details: Optional[str] = None) -> None:
        """记录错误信息到日志文件
        
        Args:
            error_type: 错误类型
            message: 错误消息
            details: 错误详情
        """
        try:
            error_log = {
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error_type": error_type,
                "message": message,
                "details": details
            }
            
            # 加载错误日志
            error_log_file = Path(__file__).parent / "error_logs.json"
            try:
                if error_log_file.exists():
                    with open(error_log_file, "r", encoding="utf-8") as f:
                        error_logs = json.load(f)
                else:
                    error_logs = []
            except Exception:
                error_logs = []
            
            # 添加新错误日志
            error_logs.append(error_log)
            # 只保留最近100条错误日志
            if len(error_logs) > 100:
                error_logs = error_logs[-100:]
            
            # 保存错误日志
            with open(error_log_file, "w", encoding="utf-8") as f:
                json.dump(error_logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"记录错误日志失败: {e}")
    
    def view_logs(self):
        """查看日志"""
        try:
            logs = self.load_logs()
            
            # 创建日志窗口
            log_window = ttk.Toplevel(self.window)
            log_window.title("分拣日志")
            log_window.geometry("900x600")
            log_window.resizable(True, True)
            
            # 创建滚动条
            scrollbar = ttk.Scrollbar(log_window)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 创建文本框
            text_widget = tk.Text(log_window, yscrollcommand=scrollbar.set, font=(("微软雅黑", 10)))
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 绑定滚动条
            scrollbar.config(command=text_widget.yview)
            
            # 显示日志
            if not logs:
                text_widget.insert(tk.END, "暂无日志记录")
            else:
                for i, log in enumerate(reversed(logs)):  # 倒序显示，最新的日志在前
                    text_widget.insert(tk.END, f"日志 {len(logs) - i}:\n")
                    text_widget.insert(tk.END, f"  时间: {log.get('time', '')}\n")
                    text_widget.insert(tk.END, f"  源文件夹: {log.get('source_folder', '')}\n")
                    text_widget.insert(tk.END, f"  目标文件夹: {log.get('destination_folder', '')}\n")
                    text_widget.insert(tk.END, f"  包含关键词: {', '.join(log.get('include_keywords', []))}\n")
                    text_widget.insert(tk.END, f"  排除关键词: {', '.join(log.get('exclude_keywords', []))}\n")
                    text_widget.insert(tk.END, f"  文件操作: {'复制' if log.get('operation', 'copy') == 'copy' else '移动'}\n")
                    text_widget.insert(tk.END, f"  总文件数: {log.get('total_files', 0)}\n")
                    text_widget.insert(tk.END, f"  匹配文件数: {log.get('matched_files', 0)}\n")
                    text_widget.insert(tk.END, f"  跳过文件数: {log.get('skipped_files', 0)}\n")
                    text_widget.insert(tk.END, "-" * 80 + "\n")
            
            # 关闭按钮
            ttk.Button(log_window, text="关闭", command=log_window.destroy, bootstyle="secondary").pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("错误", f"查看日志失败：{str(e)}")
    
    def on_drop(self, event):
        """拖放事件处理"""
        # 获取拖放的文件路径
        file_path = event.data
        if file_path:
            # 移除引号
            if file_path.startswith('"') and file_path.endswith('"'):
                file_path = file_path[1:-1]
            # 设置到当前聚焦的输入框
            event.widget.delete(0, tk.END)
            event.widget.insert(0, file_path)
    
    def preview_files(self):
        """预览匹配的文件"""
        if not self.validate_inputs():
            return
            
        try:
            src = Path(self.src_entry.get())
            keywords = [k.strip().lower() for k in self.key_entry.get().split() if k.strip()]
            exclude_keywords = [k.strip().lower() for k in self.exclude_entry.get().split() if k.strip()]
            selected_extensions = self.get_selected_extensions()
            
            # 预计算组合关键词
            combo_keywords = self._prepare_combo_keywords(keywords)
            
            # 查找匹配的文件
            matched_files = []
            skipped_files = []
            
            # 快速遍历文件
            for root, _, files in os.walk(src):
                for filename in files:
                    file_path = Path(root) / filename
                    lower_name = filename.lower()
                    
                    # 检查文件类型
                    if selected_extensions and not self._check_file_type(file_path, selected_extensions):
                        skipped_files.append(file_path)
                        continue
                    
                    # 检查排除关键词
                    if self._check_exclude_keywords(lower_name, exclude_keywords):
                        skipped_files.append(file_path)
                        continue
                    
                    # 匹配关键词
                    if self._match_keywords(lower_name, keywords, combo_keywords):
                        matched_files.append(file_path)
            
            # 创建预览窗口
            preview_window = ttk.Toplevel(self.window)
            preview_window.title("文件预览")
            preview_window.geometry("800x600")
            preview_window.resizable(True, True)
            
            # 统计信息
            stats_frame = ttk.Labelframe(preview_window, text=" 预览统计 ", bootstyle="info")
            stats_frame.pack(fill=tk.X, pady=10, padx=10)
            
            total_files = len(matched_files) + len(skipped_files)
            ttk.Label(stats_frame, text=f"总文件数：{total_files}").pack(side=tk.LEFT, padx=10, pady=5)
            ttk.Label(stats_frame, text=f"匹配文件数：{len(matched_files)}", bootstyle="success").pack(side=tk.LEFT, padx=10, pady=5)
            ttk.Label(stats_frame, text=f"跳过文件数：{len(skipped_files)}", bootstyle="warning").pack(side=tk.LEFT, padx=10, pady=5)
            
            # 文件列表
            list_frame = ttk.Labelframe(preview_window, text=" 匹配文件列表 ", bootstyle="success")
            list_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
            
            # 创建滚动条
            scrollbar = ttk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 创建列表框
            listbox = tk.Listbox(
                list_frame,
                yscrollcommand=scrollbar.set,
                font=(("微软雅黑", 10))
            )
            listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # 绑定滚动条
            scrollbar.config(command=listbox.yview)
            
            # 添加文件到列表
            for file_path in matched_files:
                listbox.insert(tk.END, str(file_path))
            
            # 关闭按钮
            ttk.Button(preview_window, text="关闭", command=preview_window.destroy, bootstyle="secondary").pack(pady=10)
            
        except FileNotFoundError:
            messagebox.showerror("错误", "源文件夹不存在")
        except Exception as e:
            messagebox.showerror("错误", f"预览失败：{str(e)}")

    def setup_ui(self):
        """构建界面布局"""
        # 创建Canvas作为滚动区域，恢复上下滑动功能
        canvas = tk.Canvas(self.window, bg="#f8f9fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, bootstyle="light")
        
        # 配置滚动区域，确保滚动区域能正确适应内容大小
        def on_frame_configure(event):
            # 更新滚动区域
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        
        # 创建窗口并保存窗口ID，以便后续更新
        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # 绑定Canvas配置变化事件，确保Canvas宽度与窗口宽度一致
        def on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)
        
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局Canvas和滚动条 - 减少边距
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # 标题 - 美化
        title_frame = ttk.Frame(scrollable_frame, bootstyle="success")
        title_frame.pack(fill=tk.X, pady=(15, 25), padx=20)
        
        title_label = ttk.Label(
            title_frame,
            text="✨ 智能文件分拣工具",
            font=("微软雅黑", 30, "bold"),
            bootstyle="success-inverse"
        )
        title_label.pack(pady=15)
        
        subtitle_label = ttk.Label(
            title_frame,
            text="高效、智能的文件管理解决方案",
            font=("微软雅黑", 16),
            bootstyle="success-inverse"
        )
        subtitle_label.pack(pady=8)
        
        # 路径选择部分 - 优化布局，减少边距
        path_frame = ttk.Labelframe(scrollable_frame, text=" 路径设置 ", bootstyle="info")
        path_frame.pack(fill=tk.X, pady=8, padx=5)
        
        # 源文件夹选择 - 减少内部边距
        source_row = ttk.Frame(path_frame)
        source_row.pack(fill=tk.X, pady=3, padx=5)
        ttk.Button(source_row, text="源文件夹", 
                 command=self.select_source,
                 bootstyle="primary",
                 width=12).pack(side=tk.LEFT, padx=5, pady=3)
        self.src_entry = ttk.Entry(source_row)
        self.src_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=3)
        
        # 添加拖放支持
        self.src_entry.bind("<<Drop>>", self.on_drop)
        self.src_entry.bind("<<DragOver>>", self.on_drag_over)
        self.src_entry.bind("<<DragEnter>>", self.on_drag_enter)
        self.src_entry.config(state="normal")
        
        # 目标文件夹选择 - 减少内部边距
        dest_row = ttk.Frame(path_frame)
        dest_row.pack(fill=tk.X, pady=3, padx=5)
        ttk.Button(dest_row, text="目标文件夹", 
                 command=self.select_destination,
                 bootstyle="warning",
                 width=12).pack(side=tk.LEFT, padx=5, pady=3)
        self.dest_entry = ttk.Entry(dest_row)
        self.dest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=3)
        
        # 添加拖放支持
        self.dest_entry.bind("<<Drop>>", self.on_drop)
        self.dest_entry.bind("<<DragOver>>", self.on_drag_over)
        self.dest_entry.bind("<<DragEnter>>", self.on_drag_enter)
        self.dest_entry.config(state="normal")
        
        # 关键词输入 - 优化布局，减少边距
        key_frame = ttk.Labelframe(scrollable_frame, text=" 分拣设置 ", bootstyle="success")
        key_frame.pack(fill=tk.X, pady=8, padx=5)
        
        # 包含关键词 - 减少内部边距
        include_row = ttk.Frame(key_frame)
        include_row.pack(fill=tk.X, pady=3, padx=5)
        ttk.Label(include_row, text="包含关键词：", width=15, anchor="w").pack(side=tk.LEFT, padx=5, pady=3)
        self.key_entry = ttk.Entry(include_row, bootstyle="primary")
        self.key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=3)
        ttk.Label(include_row, text="（多个关键词用空格分隔）", font=("微软雅黑", 9), bootstyle="secondary").pack(side=tk.LEFT, padx=5, pady=3)
        
        # 排除关键词 - 减少内部边距
        exclude_row = ttk.Frame(key_frame)
        exclude_row.pack(fill=tk.X, pady=3, padx=5)
        ttk.Label(exclude_row, text="排除关键词：", width=15, anchor="w").pack(side=tk.LEFT, padx=5, pady=3)
        self.exclude_entry = ttk.Entry(exclude_row, bootstyle="danger")
        self.exclude_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=3)
        
        # 文件夹创建选项
        folder_options_frame = ttk.Frame(key_frame)
        folder_options_frame.pack(fill=tk.X, pady=3, padx=5)
        
        self.create_folder_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(folder_options_frame, text="是否新建文件夹", variable=self.create_folder_var, bootstyle="info").pack(side=tk.LEFT, padx=12, pady=3)
        
        self.separate_folder_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(folder_options_frame, text="为每个关键词独立创建文件夹", variable=self.separate_folder_var, bootstyle="info").pack(side=tk.LEFT, padx=12, pady=3)
        
        # 自定义文件夹名称输入框
        custom_folder_frame = ttk.Frame(key_frame)
        custom_folder_frame.pack(fill=tk.X, pady=3, padx=5)
        ttk.Label(custom_folder_frame, text="自定义文件夹名称：", width=15, anchor="w").pack(side=tk.LEFT, padx=5, pady=3)
        self.custom_folder_entry = ttk.Entry(custom_folder_frame, bootstyle="primary")
        self.custom_folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=3)
        ttk.Label(custom_folder_frame, text="（留空则使用默认名称）", font=("微软雅黑", 9), bootstyle="secondary").pack(side=tk.LEFT, padx=5, pady=3)
        
        # 组合关键词匹配选项
        match_options_frame = ttk.Frame(key_frame)
        match_options_frame.pack(fill=tk.X, pady=3, padx=5)
        
        self.match_type_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(match_options_frame, text="使用组合关键词匹配", variable=self.match_type_var, bootstyle="info").pack(side=tk.LEFT, padx=12, pady=3)
        
        # 文件操作选项
        operation_frame = ttk.Frame(key_frame)
        operation_frame.pack(fill=tk.X, pady=3, padx=5)
        
        ttk.Label(operation_frame, text="文件操作：", width=15, anchor="w").pack(side=tk.LEFT, padx=5, pady=3)
        self.operation_var = tk.StringVar(value="copy")
        ttk.Radiobutton(operation_frame, text="复制文件", variable=self.operation_var, value="copy", bootstyle="primary").pack(side=tk.LEFT, padx=12, pady=3)
        ttk.Radiobutton(operation_frame, text="移动文件", variable=self.operation_var, value="move", bootstyle="primary").pack(side=tk.LEFT, padx=12, pady=3)
        
        # 组合关键词输入框
        combo_key_frame = ttk.Frame(key_frame)
        combo_key_frame.pack(fill=tk.X, pady=3, padx=5)
        ttk.Label(combo_key_frame, text="组合关键词：", width=15, anchor="w").pack(side=tk.LEFT, padx=5, pady=3)
        self.combo_key_entry = ttk.Entry(combo_key_frame, bootstyle="primary")
        self.combo_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=3)
        ttk.Label(combo_key_frame, text="示例：身份证（自动与包含关键词组合），多个属性词用空格分隔", font=(("微软雅黑", 9)), bootstyle="secondary").pack(side=tk.LEFT, padx=5, pady=3)
        
        # 配置管理 - 减少内部边距
        config_row = ttk.Frame(key_frame)
        config_row.pack(fill=tk.X, pady=3, padx=5)
        ttk.Button(config_row, text="保存配置", command=self.save_profile, bootstyle="info").pack(side=tk.LEFT, padx=5, pady=3)
        ttk.Button(config_row, text="加载配置", command=self.load_profile, bootstyle="info").pack(side=tk.LEFT, padx=5, pady=3)
        
        # 文件类型过滤 - 优化布局，减少边距
        file_type_frame = ttk.Labelframe(scrollable_frame, text=" 文件类型过滤 ", bootstyle="info")
        file_type_frame.pack(fill=tk.X, pady=8, padx=5)
        
        # 常见文件类型选项 - 优化布局，减少边距
        common_types_frame = ttk.Frame(file_type_frame)
        common_types_frame.pack(fill=tk.X, pady=3, padx=5)
        
        self.file_type_vars = {
            "文档": tk.BooleanVar(value=True),
            "图片": tk.BooleanVar(value=True),
            "视频": tk.BooleanVar(value=True),
            "音频": tk.BooleanVar(value=True),
            "压缩包": tk.BooleanVar(value=True),
            "其他": tk.BooleanVar(value=True)
        }
        
        # 详细文件格式选项
        self.file_format_vars = {
            "文档": {
                ".doc": tk.BooleanVar(value=True),
                ".docx": tk.BooleanVar(value=True),
                ".txt": tk.BooleanVar(value=True),
                ".pdf": tk.BooleanVar(value=True),
                ".xls": tk.BooleanVar(value=True),
                ".xlsx": tk.BooleanVar(value=True),
                ".ppt": tk.BooleanVar(value=True),
                ".pptx": tk.BooleanVar(value=True),
                ".md": tk.BooleanVar(value=True),
                ".rtf": tk.BooleanVar(value=True)
            },
            "图片": {
                ".jpg": tk.BooleanVar(value=True),
                ".jpeg": tk.BooleanVar(value=True),
                ".png": tk.BooleanVar(value=True),
                ".gif": tk.BooleanVar(value=True),
                ".bmp": tk.BooleanVar(value=True),
                ".tiff": tk.BooleanVar(value=True),
                ".svg": tk.BooleanVar(value=True)
            },
            "视频": {
                ".mp4": tk.BooleanVar(value=True),
                ".avi": tk.BooleanVar(value=True),
                ".mov": tk.BooleanVar(value=True),
                ".wmv": tk.BooleanVar(value=True),
                ".flv": tk.BooleanVar(value=True),
                ".mkv": tk.BooleanVar(value=True)
            },
            "音频": {
                ".mp3": tk.BooleanVar(value=True),
                ".wav": tk.BooleanVar(value=True),
                ".flac": tk.BooleanVar(value=True),
                ".aac": tk.BooleanVar(value=True),
                ".ogg": tk.BooleanVar(value=True)
            },
            "压缩包": {
                ".zip": tk.BooleanVar(value=True),
                ".rar": tk.BooleanVar(value=True),
                ".7z": tk.BooleanVar(value=True),
                ".tar": tk.BooleanVar(value=True),
                ".gz": tk.BooleanVar(value=True)
            }
        }
        
        # 文件类型映射
        self.file_type_map = {
            "文档": [".doc", ".docx", ".txt", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx", ".md", ".rtf"],
            "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg"],
            "视频": [".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv"],
            "音频": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
            "压缩包": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "其他": []
        }
        
        # 创建复选框 - 优化布局，分两行排列，减少间距
        checkbox_frame = ttk.Frame(common_types_frame)
        checkbox_frame.pack(fill=tk.X, pady=3)
        
        # 第一行复选框 - 减少间距
        checkbox_row1 = ttk.Frame(checkbox_frame)
        checkbox_row1.pack(fill=tk.X, pady=1)
        ttk.Checkbutton(checkbox_row1, text="文档", variable=self.file_type_vars["文档"], bootstyle="info").pack(side=tk.LEFT, padx=12, pady=3)
        ttk.Checkbutton(checkbox_row1, text="图片", variable=self.file_type_vars["图片"], bootstyle="info").pack(side=tk.LEFT, padx=12, pady=3)
        ttk.Checkbutton(checkbox_row1, text="视频", variable=self.file_type_vars["视频"], bootstyle="info").pack(side=tk.LEFT, padx=12, pady=3)
        
        # 第二行复选框 - 减少间距
        checkbox_row2 = ttk.Frame(checkbox_frame)
        checkbox_row2.pack(fill=tk.X, pady=1)
        ttk.Checkbutton(checkbox_row2, text="音频", variable=self.file_type_vars["音频"], bootstyle="info").pack(side=tk.LEFT, padx=12, pady=3)
        ttk.Checkbutton(checkbox_row2, text="压缩包", variable=self.file_type_vars["压缩包"], bootstyle="info").pack(side=tk.LEFT, padx=12, pady=3)
        ttk.Checkbutton(checkbox_row2, text="其他", variable=self.file_type_vars["其他"], bootstyle="info").pack(side=tk.LEFT, padx=12, pady=3)
        
        # 文件格式设置按钮 - 优化样式
        format_settings_frame = ttk.Frame(file_type_frame)
        format_settings_frame.pack(fill=tk.X, pady=10, padx=5)
        ttk.Button(format_settings_frame, text="📋 文件格式设置", command=self.open_format_settings, bootstyle="success-outline").pack(side=tk.LEFT, padx=15, pady=5)
        ttk.Label(format_settings_frame, text="（点击设置详细文件格式选项）", font=("微软雅黑", 9), bootstyle="secondary").pack(side=tk.LEFT, padx=8)
        
        # 自定义文件扩展名 - 优化布局，减少边距
        custom_ext_frame = ttk.Frame(file_type_frame)
        custom_ext_frame.pack(fill=tk.X, pady=3, padx=5)
        ttk.Label(custom_ext_frame, text="自定义扩展名：", width=15, anchor="w").pack(side=tk.LEFT, padx=5, pady=3)
        ttk.Label(custom_ext_frame, text="（逗号分隔）", font=(("微软雅黑", 9)), bootstyle="secondary").pack(side=tk.LEFT, padx=5, pady=3)
        self.custom_ext_entry = ttk.Entry(custom_ext_frame)
        self.custom_ext_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=3)
        
        # 进度和统计信息 - 优化布局，减少边距
        progress_stats_frame = ttk.Frame(scrollable_frame)
        progress_stats_frame.pack(fill=tk.X, pady=12, padx=5)
        
        # 进度显示区域 - 居中显示，减少边距
        progress_container = ttk.Frame(progress_stats_frame)
        progress_container.pack(fill=tk.X, pady=6)
        
        self.progress_bar = CircularProgressBar(progress_container, diameter=180, line_width=12)  # 减小进度条尺寸
        self.progress_bar.canvas.pack(expand=True)
        
        # 统计信息 - 优化布局，更紧凑
        if self.skin_theme == "darkly":
            # 科技感皮肤的模块样式
            stats_frame = ttk.Labelframe(progress_stats_frame, text="统计信息", bootstyle="dark")
            stats_frame.pack(fill=tk.X, pady=6, padx=5)
        else:
            # 其他皮肤的模块样式
            stats_frame = ttk.Labelframe(progress_stats_frame, text="统计信息", bootstyle="secondary")
            stats_frame.pack(fill=tk.X, pady=6, padx=5)
        
        # 统计信息行 - 减少内部边距，使用更紧凑的布局
        stats_row1 = ttk.Frame(stats_frame)
        stats_row1.pack(fill=tk.X, pady=3, padx=5)
        self.total_files_var = tk.StringVar(value="总文件数：0")
        ttk.Label(stats_row1, textvariable=self.total_files_var, font=(("微软雅黑", 10))).pack(side=tk.LEFT, padx=12, pady=3)
        
        stats_row2 = ttk.Frame(stats_frame)
        stats_row2.pack(fill=tk.X, pady=3, padx=5)
        self.matched_files_var = tk.StringVar(value="匹配文件：0")
        ttk.Label(stats_row2, textvariable=self.matched_files_var, font=(("微软雅黑", 10)), bootstyle="success").pack(side=tk.LEFT, padx=12, pady=3)
        
        stats_row3 = ttk.Frame(stats_frame)
        stats_row3.pack(fill=tk.X, pady=3, padx=5)
        self.skipped_files_var = tk.StringVar(value="跳过文件：0")
        ttk.Label(stats_row3, textvariable=self.skipped_files_var, font=(("微软雅黑", 10)), bootstyle="warning").pack(side=tk.LEFT, padx=12, pady=3)
        
        # 添加处理速度和时间统计
        stats_row4 = ttk.Frame(stats_frame)
        stats_row4.pack(fill=tk.X, pady=3, padx=5)
        self.processing_speed_var = tk.StringVar(value="处理速度：0 文件/秒")
        ttk.Label(stats_row4, textvariable=self.processing_speed_var, font=(("微软雅黑", 10)), bootstyle="info").pack(side=tk.LEFT, padx=12, pady=3)
        
        stats_row5 = ttk.Frame(stats_frame)
        stats_row5.pack(fill=tk.X, pady=3, padx=5)
        self.elapsed_time_var = tk.StringVar(value="已用时间：00:00")
        ttk.Label(stats_row5, textvariable=self.elapsed_time_var, font=(("微软雅黑", 10)), bootstyle="info").pack(side=tk.LEFT, padx=12, pady=3)
        
        # 状态信息 - 优化显示，减少边距
        self.status_var = tk.StringVar(value="等待开始...")
        status_label = ttk.Label(
            scrollable_frame, 
            textvariable=self.status_var,
            bootstyle="secondary",
            font=(("微软雅黑", 11)),
            wraplength=800,
            anchor="center"
        )
        status_label.pack(pady=(10, 12), padx=5)
        
        # 操作按钮 - 优化布局，居中显示，添加视觉效果
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(pady=15)
        
        # 按钮容器，实现居中对齐
        btn_container = ttk.Frame(btn_frame)
        btn_container.pack()

        # 按钮之间适当间距
        # 按钮样式
        ttk.Button(
            btn_container, 
            text="预览", 
            bootstyle="info-outline",
            command=self.preview_files,
            width=14
        ).pack(side=tk.LEFT, padx=15)

        ttk.Button(
            btn_container, 
            text="开始分拣", 
            bootstyle="success-outline",
            command=self.start_organize,
            width=14
        ).pack(side=tk.LEFT, padx=15)

        ttk.Button(
            btn_container, 
            text="停止", 
            bootstyle="danger-outline",
            command=self.stop_organize,
            width=14
        ).pack(side=tk.LEFT, padx=15)
        
        ttk.Button(
            btn_container, 
            text="查看日志", 
            bootstyle="secondary-outline",
            command=self.view_logs,
            width=14
        ).pack(side=tk.LEFT, padx=15)
        
        ttk.Button(
            btn_container, 
            text="使用介绍", 
            bootstyle="info-outline",
            command=self.show_usage_guide,
            width=14
        ).pack(side=tk.LEFT, padx=15)
        
        ttk.Button(
            btn_container, 
            text="皮肤选择", 
            bootstyle="primary-outline",
            command=self.show_skin_selection,
            width=14
        ).pack(side=tk.LEFT, padx=15)
        
        
        
        # 绑定鼠标滚轮事件，实现上下滑动
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def select_source(self):
        """选择源文件夹"""
        if path := filedialog.askdirectory():
            self.src_entry.delete(0, tk.END)
            self.src_entry.insert(0, path)

    def select_destination(self):
        """选择目标文件夹"""
        if path := filedialog.askdirectory():
            self.dest_entry.delete(0, tk.END)
            self.dest_entry.insert(0, path)

    def validate_inputs(self):
        """验证输入有效性"""
        required = {
            "源文件夹": self.src_entry.get(),
            "目标文件夹": self.dest_entry.get(),
            "关键词": self.key_entry.get()
        }
        if missing := [k for k, v in required.items() if not v]:
            messagebox.showerror("输入错误", f"缺少必要参数：\n{', '.join(missing)}")
            return False
        return True

    def start_organize(self):
        """启动分拣线程"""
        if self.validate_inputs():
            self.stop_event.clear()
            Thread(target=self.organize_files, daemon=True).start()

    def stop_organize(self):
        """停止分拣操作"""
        self.stop_event.set()
        self.status_var.set("操作已停止")
    
    def switch_skin(self, skin_name):
        """切换皮肤并重启应用"""
        try:
            # 更新皮肤设置
            self.current_skin = skin_name
            self.config["skin"] = skin_name
            self.save_config()
            
            # 显示皮肤切换成功的消息
            messagebox.showinfo("皮肤切换", f"成功切换到 '{skin_name}' 皮肤！\n应用将重启以应用新皮肤。")
            
            # 销毁当前窗口
            old_window = self.window
            old_window.destroy()
            
            # 重启应用
            import sys
            import os
            python = sys.executable
            os.execl(python, python, *sys.argv)
            
        except Exception as e:
            print(f"皮肤切换失败: {e}")
            messagebox.showerror("错误", f"皮肤切换失败：{str(e)}")
    
    def _restore_settings(self, settings):
        """恢复设置到新界面"""
        try:
            # 恢复路径设置
            if hasattr(self, 'src_entry'):
                self.src_entry.delete(0, tk.END)
                self.src_entry.insert(0, settings.get("source_folder", ""))
            
            if hasattr(self, 'dest_entry'):
                self.dest_entry.delete(0, tk.END)
                self.dest_entry.insert(0, settings.get("destination_folder", ""))
            
            # 恢复关键词设置
            if hasattr(self, 'key_entry'):
                self.key_entry.delete(0, tk.END)
                self.key_entry.insert(0, settings.get("include_keywords", ""))
            
            if hasattr(self, 'exclude_entry'):
                self.exclude_entry.delete(0, tk.END)
                self.exclude_entry.insert(0, settings.get("exclude_keywords", ""))
            
            # 恢复文件夹选项
            if hasattr(self, 'create_folder_var'):
                self.create_folder_var.set(settings.get("create_folder", True))
            
            if hasattr(self, 'separate_folder_var'):
                self.separate_folder_var.set(settings.get("separate_folder", True))
            
            # 恢复匹配类型
            if hasattr(self, 'match_type_var'):
                self.match_type_var.set(settings.get("match_type", False))
            
            # 恢复自定义文件夹名称
            if hasattr(self, 'custom_folder_entry'):
                self.custom_folder_entry.delete(0, tk.END)
                self.custom_folder_entry.insert(0, settings.get("custom_folder_name", ""))
            
            # 恢复组合关键词
            if hasattr(self, 'combo_key_entry'):
                self.combo_key_entry.delete(0, tk.END)
                self.combo_key_entry.insert(0, settings.get("combo_keywords", ""))
            
            # 恢复文件操作
            if hasattr(self, 'operation_var'):
                self.operation_var.set(settings.get("operation", "copy"))
            
            # 恢复自定义扩展名
            if hasattr(self, 'custom_ext_entry'):
                self.custom_ext_entry.delete(0, tk.END)
                self.custom_ext_entry.insert(0, settings.get("custom_extensions", ""))
            
            # 恢复文件类型设置
            if hasattr(self, 'file_type_vars'):
                for file_type, value in settings.get("file_types", {}).items():
                    if file_type in self.file_type_vars:
                        self.file_type_vars[file_type].set(value)
            
            # 恢复文件格式设置
            if hasattr(self, 'file_format_vars'):
                for file_type, formats in settings.get("file_formats", {}).items():
                    if file_type in self.file_format_vars:
                        for ext, value in formats.items():
                            if ext in self.file_format_vars[file_type]:
                                self.file_format_vars[file_type][ext].set(value)
        except Exception as e:
            print(f"恢复设置失败: {e}")
    
    def show_skin_selection(self):
        """显示皮肤选择模态对话框"""
        # 创建模态对话框
        dialog = tk.Toplevel(self.window)
        dialog.title("🎨 皮肤选择")
        dialog.geometry("700x600")
        dialog.resizable(True, True)
        dialog.transient(self.window)
        dialog.grab_set()
        
        # 设置对话框图标和样式
        dialog.configure(bg="#f8f9fa")
        
        # 创建滚动区域
        canvas = tk.Canvas(dialog, bg="#f8f9fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview, bootstyle="info-round")
        scrollable_frame = ttk.Frame(canvas, bootstyle="light")
        
        # 配置滚动区域
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)
        
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局Canvas和滚动条
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=15)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=15)
        
        # 标题
        title_label = ttk.Label(
            scrollable_frame,
            text="🎨 选择皮肤",
            font=("微软雅黑", 24, "bold"),
            bootstyle="success"
        )
        title_label.pack(pady=(20, 30))
        
        # 皮肤选项
        selected_skin = tk.StringVar(value=self.current_skin)
        
        for skin_name, skin_info in self.skin_configs.items():
            skin_frame = ttk.Labelframe(scrollable_frame, text=f" {skin_info['preview']} {skin_name} ", bootstyle="primary")
            skin_frame.pack(fill=tk.X, pady=12, padx=10)
            
            # 皮肤描述
            desc_label = ttk.Label(skin_frame, text=skin_info['description'], font=("微软雅黑", 12), bootstyle="info")
            desc_label.pack(padx=20, pady=15, anchor="w")
            
            # 选择按钮
            select_btn = ttk.Radiobutton(
                skin_frame,
                text="选择此皮肤",
                variable=selected_skin,
                value=skin_name,
                bootstyle="info",
                width=20
            )
            select_btn.pack(padx=20, pady=10, anchor="w")
        
        # 按钮区域
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(pady=20)
        
        def apply_skin():
            new_skin = selected_skin.get()
            if new_skin != self.current_skin:
                # 先销毁对话框，再切换皮肤
                dialog.destroy()
                self.switch_skin(new_skin)
            else:
                dialog.destroy()
        
        ttk.Button(btn_frame, text="✅ 应用", command=apply_skin, bootstyle="success", width=12).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ 取消", command=dialog.destroy, bootstyle="secondary", width=12).pack(side=tk.LEFT, padx=10)
        
        # 绑定鼠标滚轮事件
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
    
    def show_usage_guide(self):
        """显示使用介绍模态对话框"""
        # 创建模态对话框
        dialog = tk.Toplevel(self.window)
        dialog.title("📖 使用介绍")
        dialog.geometry("900x700")
        dialog.resizable(True, True)
        dialog.transient(self.window)
        dialog.grab_set()
        
        # 设置对话框图标和样式
        dialog.configure(bg="#f8f9fa")
        
        # 创建滚动区域
        canvas = tk.Canvas(dialog, bg="#f8f9fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview, bootstyle="info-round")
        scrollable_frame = ttk.Frame(canvas, bootstyle="light")
        
        # 配置滚动区域
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)
        
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局Canvas和滚动条
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=15)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=15)
        
        # 标题
        title_label = ttk.Label(
            scrollable_frame,
            text="📖 智能文件分拣工具使用指南",
            font=("微软雅黑", 24, "bold"),
            bootstyle="success"
        )
        title_label.pack(pady=(20, 30))
        
        # 功能介绍
        intro_frame = ttk.Labelframe(scrollable_frame, text=" 功能简介 ", bootstyle="info")
        intro_frame.pack(fill=tk.X, pady=12, padx=10)
        
        intro_text = """智能文件分拣工具是一款高效、智能的文件管理工具，能够帮助您快速整理和分类大量文件。

主要功能：
1. 根据关键词自动分拣文件
2. 支持文件类型过滤
3. 自定义文件夹结构
4. 预览匹配文件
5. 详细的分拣日志
6. 配置保存和加载

适用场景：
- 整理下载文件夹中的各种文件
- 分类工作文档和资料
- 管理照片和视频文件
- 批量处理文件整理任务"""
        
        ttk.Label(intro_frame, text=intro_text, font=("微软雅黑", 12), wraplength=850, justify=tk.LEFT, bootstyle="info").pack(padx=20, pady=15, anchor="w")
        
        # 基本操作步骤
        steps_frame = ttk.Labelframe(scrollable_frame, text=" 操作步骤 ", bootstyle="primary")
        steps_frame.pack(fill=tk.X, pady=12, padx=10)
        
        steps_text = """使用步骤：

1. **设置路径**
   - 点击"源文件夹"按钮选择要分拣的文件夹
   - 点击"目标文件夹"按钮选择文件保存位置

2. **配置分拣规则**
   - 在"包含关键词"输入框中输入要匹配的关键词（多个关键词用空格分隔）
   - 在"排除关键词"输入框中输入要排除的关键词
   - 选择是否新建文件夹以及文件夹创建方式
   - 选择文件操作方式（复制或移动）

3. **设置文件类型**
   - 在"文件类型过滤"部分勾选要处理的文件类型
   - 点击"文件格式设置"按钮可以详细配置每种文件类型包含的具体格式
   - 可以在"自定义扩展名"中添加不在列表中的文件扩展名

4. **预览和执行**
   - 点击"预览"按钮查看匹配的文件
   - 确认无误后点击"开始分拣"按钮执行分拣操作
   - 如有需要，可以点击"停止"按钮终止操作

5. **查看结果**
   - 分拣完成后可以在目标文件夹查看整理结果
   - 点击"查看日志"按钮查看详细的分拣记录"""
        
        ttk.Label(steps_frame, text=steps_text, font=("微软雅黑", 12), wraplength=850, justify=tk.LEFT, bootstyle="primary").pack(padx=20, pady=15, anchor="w")
        
        # 高级功能
        advanced_frame = ttk.Labelframe(scrollable_frame, text=" 高级功能 ", bootstyle="success")
        advanced_frame.pack(fill=tk.X, pady=12, padx=10)
        
        advanced_text = '''高级功能说明：

1. **组合关键词匹配**
   - 勾选"使用组合关键词匹配"选项
   - 在"组合关键词"输入框中输入属性词（如：身份证、学历等）
   - 系统会自动将包含关键词与属性词组合进行匹配
   - 示例：包含关键词输入"张三 李四"，组合关键词输入"身份证"，系统会匹配包含"张三身份证"或"李四身份证"的文件

2. **配置管理**
   - 点击"保存配置"按钮可以将当前配置保存为JSON文件
   - 点击"加载配置"按钮可以加载之前保存的配置
   - 方便在不同场景下快速切换配置

3. **自定义文件夹名称**
   - 在"自定义文件夹名称"输入框中输入名称
   - 分拣时会使用该名称创建主文件夹
   - 留空则使用默认名称"匹配文件夹"'''

        ttk.Label(advanced_frame, text=advanced_text, font=("微软雅黑", 12), wraplength=850, justify=tk.LEFT, bootstyle="success").pack(padx=20, pady=15, anchor="w")
        
        # 常见问题
        faq_frame = ttk.Labelframe(scrollable_frame, text=" 常见问题 ", bootstyle="warning")
        faq_frame.pack(fill=tk.X, pady=12, padx=10)
        
        faq_text = '''常见问题解答：

Q: 为什么有些文件没有被分拣？
A: 请检查以下几点：
   - 文件是否符合选择的文件类型
   - 文件名是否包含设置的关键词
   - 文件名是否包含排除的关键词
   - 文件路径是否有特殊字符或权限问题

Q: 分拣速度很慢怎么办？
A: 可以尝试以下方法：
   - 减少同时处理的文件类型
   - 只勾选必要的文件格式
   - 缩小源文件夹的范围
   - 关闭其他占用系统资源的程序

Q: 如何批量处理多个文件夹？
A: 可以使用配置管理功能：
   - 为每个文件夹创建一个配置文件
   - 依次加载配置并执行分拣

Q: 分拣后文件丢失了怎么办？
A: 请检查：
   - 目标文件夹路径是否正确
   - 是否有足够的磁盘空间
   - 查看分拣日志了解详细情况
   - 如果使用移动操作，文件会从源文件夹移除'''

        ttk.Label(faq_frame, text=faq_text, font=("微软雅黑", 12), wraplength=850, justify=tk.LEFT, bootstyle="warning").pack(padx=20, pady=15, anchor="w")
        
        # 按钮区域
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(pady=30)
        ttk.Button(btn_frame, text="✅ 我知道了", command=dialog.destroy, bootstyle="success", width=16).pack()
        
        # 绑定鼠标滚轮事件
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
    
    def open_format_settings(self):
        """打开文件格式设置模态对话框"""
        # 创建模态对话框
        dialog = tk.Toplevel(self.window)
        dialog.title("📋 文件格式设置")
        dialog.geometry("850x650")
        dialog.resizable(True, True)
        dialog.transient(self.window)
        dialog.grab_set()
        
        # 设置对话框图标和样式
        dialog.configure(bg="#f8f9fa")
        
        # 创建滚动区域
        canvas = tk.Canvas(dialog, bg="#f8f9fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview, bootstyle="info-round")
        scrollable_frame = ttk.Frame(canvas, bootstyle="light")
        
        # 配置滚动区域
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)
        
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局Canvas和滚动条
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=15)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=15)
        
        # 功能介绍 - 美化
        intro_frame = ttk.Labelframe(scrollable_frame, text=" 📚 功能介绍 ", bootstyle="info")
        intro_frame.pack(fill=tk.X, pady=12, padx=8)
        
        intro_text = """文件格式设置说明：

1. 选择文件类型：在主界面勾选需要处理的文件类型
2. 详细格式设置：在本对话框中设置每种文件类型包含的具体格式
3. 自定义扩展名：在主界面添加不在列表中的文件扩展名
4. 过滤规则：分拣时会只处理选中的文件类型和格式

💡 提示：取消勾选不需要的格式可以提高分拣效率，避免处理无关文件。"""
        
        ttk.Label(intro_frame, text=intro_text, font=("微软雅黑", 10), wraplength=800, justify=tk.LEFT, bootstyle="info").pack(padx=15, pady=12, anchor="w")
        
        # 文件格式选项 - 美化
        format_icons = {
            "文档": "📄",
            "图片": "🖼️",
            "视频": "🎬",
            "音频": "🎵",
            "压缩包": "📦"
        }
        
        for file_type, formats in self.file_format_vars.items():
            # 检查是否在主界面勾选了该文件类型
            if file_type in self.file_type_vars and not self.file_type_vars[file_type].get():
                continue  # 如果主界面未勾选，跳过显示该类型的格式
            
            icon = format_icons.get(file_type, "📁")
            format_frame = ttk.Labelframe(scrollable_frame, text=f" {icon} {file_type}格式 ", bootstyle="primary")
            format_frame.pack(fill=tk.X, pady=10, padx=8)
            
            # 添加格式选项
            row = 0
            col = 0
            max_cols = 5
            
            for ext, var in formats.items():
                ttk.Checkbutton(format_frame, text=ext, variable=var, bootstyle="primary").grid(row=row, column=col, padx=15, pady=5, sticky="w")
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
        
        # 按钮区域 - 美化
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="✅ 确定", command=dialog.destroy, bootstyle="success", width=14).pack(side=tk.LEFT, padx=15)
        ttk.Button(btn_frame, text="❌ 取消", command=dialog.destroy, bootstyle="danger", width=14).pack(side=tk.LEFT, padx=15)
        
        # 绑定鼠标滚轮事件
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
    
    def get_selected_extensions(self) -> List[str]:
        """获取用户选择的文件扩展名
        
        Returns:
            List[str]: 选中的文件扩展名列表
        """
        selected_extensions = []
        
        # 获取选中的常见文件类型及其详细格式
        for file_type, var in self.file_type_vars.items():
            if var.get():
                if file_type in self.file_format_vars:
                    # 检查详细文件格式选项
                    for ext, ext_var in self.file_format_vars[file_type].items():
                        if ext_var.get():
                            selected_extensions.append(ext)
                else:
                    # 其他类型，添加所有映射的扩展名
                    selected_extensions.extend(self.file_type_map[file_type])
        
        # 添加自定义扩展名
        custom_exts = self.custom_ext_entry.get().strip()
        if custom_exts:
            for ext in custom_exts.split(","):
                ext = ext.strip()
                if ext and not ext.startswith("."):
                    ext = f".{ext}"
                if ext:
                    selected_extensions.append(ext)
        
        return selected_extensions
    
    def _prepare_combo_keywords(self, keywords: List[str]) -> List[Tuple[str, str]]:
        """预计算组合关键词，避免每次循环都重新解析
        
        Args:
            keywords: 关键词列表
        
        Returns:
            List[Tuple[str, str]]: 组合关键词列表，每个元素是(name, attribute)元组
        """
        if not self.match_type_var.get():
            return []
        
        combo_keywords = []
        combo_keywords_str = self.combo_key_entry.get().strip()
        
        if not combo_keywords_str:
            return []
        
        # 检查是否包含连字符
        if '-' in combo_keywords_str:
            # 格式1：包含连字符，如 张三-身份证, 李四-学历
            for combo in combo_keywords_str.split(','):
                combo = combo.strip()
                if '-' in combo:
                    name, attribute = combo.split('-', 1)
                    name = name.strip().lower()
                    attribute = attribute.strip().lower()
                    combo_keywords.append((name, attribute))
        else:
            # 格式2：仅包含属性词，如 身份证
            # 自动与包含关键词中的每个关键词组合
            attributes = [attr.strip().lower() for attr in combo_keywords_str.split() if attr.strip()]
            for attribute in attributes:
                for name in keywords:
                    combo_keywords.append((name, attribute))
        
        return combo_keywords
    
    def _check_file_type(self, file_path: Path, selected_extensions: List[str]) -> bool:
        """检查文件类型是否符合要求
        
        Args:
            file_path: 文件路径
            selected_extensions: 选中的文件扩展名列表
        
        Returns:
            bool: 文件类型是否符合要求
        """
        if not selected_extensions:
            return True
        file_ext = file_path.suffix.lower()
        return file_ext in selected_extensions
    
    def _check_exclude_keywords(self, lower_name: str, exclude_keywords: List[str]) -> bool:
        """检查是否包含排除关键词
        
        Args:
            lower_name: 小写的文件名
            exclude_keywords: 排除关键词列表
        
        Returns:
            bool: 是否包含排除关键词
        """
        return any(exclude_kw in lower_name for exclude_kw in exclude_keywords)
    
    def _match_keywords(self, lower_name: str, keywords: List[str], combo_keywords: List[Tuple[str, str]]) -> Optional[str]:
        """匹配关键词，返回匹配到的名称
        
        Args:
            lower_name: 小写的文件名
            keywords: 关键词列表
            combo_keywords: 组合关键词列表
        
        Returns:
            Optional[str]: 匹配到的名称，若未匹配则返回None
        """
        if self.match_type_var.get():
            # 使用组合关键词匹配
            for name, attribute in combo_keywords:
                if name in lower_name and attribute in lower_name:
                    return name
        else:
            # 包含任意关键词
            for kw in keywords:
                if kw in lower_name:
                    return kw
        return None
    
    def _determine_destination_folder(self, base_dest: Path, main_folder_name: str, matched_name: str) -> Path:
        """确定目标文件夹结构
        
        Args:
            base_dest: 基础目标文件夹路径
            main_folder_name: 主文件夹名称
            matched_name: 匹配到的名称
        
        Returns:
            Path: 目标文件夹路径
        """
        if self.create_folder_var.get():
            # 情况1：新建文件夹
            if self.separate_folder_var.get():
                # 1.1：新建主文件夹，并为每个关键词创建独立子文件夹
                main_dest_dir = base_dest / main_folder_name
                return main_dest_dir / matched_name
            else:
                # 1.2：仅新建一个主文件夹，所有文件放入其中
                return base_dest / main_folder_name
        else:
            # 情况2：不新建主文件夹
            if self.separate_folder_var.get():
                # 2.1：直接在目标文件夹下为每个关键词创建独立文件夹
                return base_dest / matched_name
            else:
                # 2.2：所有文件直接放入目标文件夹，不创建额外文件夹
                return base_dest
    
    def _handle_duplicate_files(self, dest_dir: Path, filename: str) -> Path:
        """处理重名文件
        
        Args:
            dest_dir: 目标文件夹路径
            filename: 文件名
        
        Returns:
            Path: 处理后的目标文件路径
        """
        dest_path = dest_dir / filename
        counter = 1
        while dest_path.exists():
            new_name = f"{dest_path.stem}_副本{counter}{dest_path.suffix}"
            dest_path = dest_path.with_name(new_name)
            counter += 1
        return dest_path
    
    def _process_matched_file(self, file_path: Path, filename: str, base_dest: Path, matched_name: str) -> bool:
        """处理匹配到的文件
        
        Args:
            file_path: 文件路径
            filename: 文件名
            base_dest: 基础目标文件夹路径
            matched_name: 匹配到的名称
        
        Returns:
            bool: 处理是否成功
        """
        try:
            # 获取自定义文件夹名称，若为空则使用默认名称
            custom_folder_name = self.custom_folder_entry.get().strip()
            main_folder_name = custom_folder_name if custom_folder_name else "匹配文件夹"
            
            # 确定目标文件夹
            dest_dir = self._determine_destination_folder(base_dest, main_folder_name, matched_name)
            
            # 创建目标文件夹（如果不存在）
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # 构建目标文件路径并处理重名
            dest_path = self._handle_duplicate_files(dest_dir, filename)
            
            # 根据用户选择执行复制或移动操作
            operation = self.operation_var.get()
            if operation == "copy":
                # 复制文件
                shutil.copy2(file_path, dest_path)
            else:
                # 移动文件
                shutil.move(file_path, dest_path)
            return True
        except PermissionError:
            error_msg = f"权限错误：无法访问或创建文件夹 {dest_dir}"
            self._log_error("权限错误", error_msg)
            self.status_var.set(error_msg)
            messagebox.showerror("错误", error_msg)
            return False
        except Exception as e:
            error_msg = f"处理文件 {filename} 时发生异常：{str(e)}"
            self._log_error("文件处理错误", error_msg)
            self.status_var.set(f"错误：处理文件 {filename} 时发生异常")
            messagebox.showerror("错误", error_msg)
            return False
    
    def _finalize_processing(self, src: Path, base_dest: Path, keywords: List[str], exclude_keywords: List[str], total_files: int, matched: int, skipped: int) -> None:
        """完成处理并记录日志
        
        Args:
            src: 源文件夹路径
            base_dest: 基础目标文件夹路径
            keywords: 包含关键词列表
            exclude_keywords: 排除关键词列表
            total_files: 总文件数
            matched: 匹配文件数
            skipped: 跳过文件数
        """
        # 更新最终统计信息
        def final_update():
            self.progress_bar.update_progress(100)
            self.total_files_var.set(f"总文件数：{total_files}")
            self.matched_files_var.set(f"匹配文件：{matched}")
            self.skipped_files_var.set(f"跳过文件：{skipped}")
            self.processing_speed_var.set("处理速度：0 文件/秒")
            self.elapsed_time_var.set("已用时间：00:00")
        self.window.after_idle(final_update)
        
        # 记录日志
        import datetime
        log_entry = {
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_folder": str(src),
            "destination_folder": str(base_dest),
            "include_keywords": keywords,
            "exclude_keywords": exclude_keywords,
            "operation": self.operation_var.get(),
            "total_files": total_files,
            "matched_files": matched,
            "skipped_files": skipped
        }
        self.save_log(log_entry)
        
        # 显示完成信息
        self.status_var.set(f"完成！共处理 {total_files} 个文件，匹配 {matched} 个，跳过 {skipped} 个")
        messagebox.showinfo("完成", f"文件已分拣到：\n{base_dest}\n\n处理统计：\n总文件数：{total_files}\n匹配文件数：{matched}\n跳过文件数：{skipped}")
    
    def organize_files(self):
        """执行文件分拣的核心逻辑"""
        try:
            # 准备阶段
            src = Path(self.src_entry.get())
            base_dest = Path(self.dest_entry.get())
            keywords = [k.strip().lower() for k in self.key_entry.get().split() if k.strip()]
            exclude_keywords = [k.strip().lower() for k in self.exclude_entry.get().split() if k.strip()]
            selected_extensions = self.get_selected_extensions()
            
            # 验证路径存在性
            if not src.exists() or not src.is_dir():
                error_msg = f"源文件夹不存在或不是有效的目录：{src}"
                self._log_error("路径错误", error_msg)
                messagebox.showerror("错误", error_msg)
                return
            
            if not base_dest.exists() or not base_dest.is_dir():
                error_msg = f"目标文件夹不存在或不是有效的目录：{base_dest}"
                self._log_error("路径错误", error_msg)
                messagebox.showerror("错误", error_msg)
                return
            
            # 预计算组合关键词
            combo_keywords = self._prepare_combo_keywords(keywords)
            
            # 获取总文件数（使用生成器表达式，避免一次性加载所有文件）
            total_files = sum(1 for _, _, files in os.walk(src) for _ in files)
            if total_files == 0:
                messagebox.showinfo("提示", "源文件夹中没有文件")
                return
                
            # 初始化统计变量
            processed = 0
            matched = 0
            skipped = 0
            last_progress = -1
            update_interval = 20  # 增加更新间隔，减少UI更新次数
            start_time = datetime.datetime.now()
            
            # 初始化统计信息
            def init_stats():
                self.total_files_var.set(f"总文件数：{total_files}")
                self.matched_files_var.set(f"匹配文件：0")
                self.skipped_files_var.set(f"跳过文件：0")
                self.processing_speed_var.set("处理速度：0 文件/秒")
                self.elapsed_time_var.set("已用时间：00:00")
            self.window.after_idle(init_stats)
            
            # 批量处理文件
            for root, _, files in os.walk(src):
                for filename in files:
                    if self.stop_event.is_set():
                        self.status_var.set("操作已停止")
                        return
                        
                    file_path = Path(root) / filename
                    lower_name = filename.lower()
                    processed += 1
                    
                    try:
                        # 检查文件类型
                        if selected_extensions and not self._check_file_type(file_path, selected_extensions):
                            skipped += 1
                            continue
                        
                        # 检查排除关键词
                        if self._check_exclude_keywords(lower_name, exclude_keywords):
                            skipped += 1
                            continue
                        
                        # 计算并更新进度
                        current_progress = int((processed / total_files) * 100)
                        if current_progress != last_progress and processed % update_interval == 0:
                            # 计算处理速度和已用时间
                            elapsed_time = datetime.datetime.now() - start_time
                            seconds_elapsed = elapsed_time.total_seconds()
                            if seconds_elapsed > 0:
                                speed = processed / seconds_elapsed
                                time_str = str(elapsed_time).split('.')[0]
                            else:
                                speed = 0
                                time_str = "00:00:00"
                            
                            def safe_update():
                                self.progress_bar.update_progress(current_progress)
                                self.total_files_var.set(f"总文件数：{total_files}")
                                self.matched_files_var.set(f"匹配文件：{matched}")
                                self.skipped_files_var.set(f"跳过文件：{skipped}")
                                self.processing_speed_var.set(f"处理速度：{speed:.1f} 文件/秒")
                                self.elapsed_time_var.set(f"已用时间：{time_str}")
                            self.window.after_idle(safe_update)
                            last_progress = current_progress
                            
                        # 每处理一定数量的文件更新一次状态
                        if processed % update_interval == 0:
                            self.status_var.set(f"正在处理：{filename[:25]}...")
                        
                        # 匹配关键词
                        matched_name = self._match_keywords(lower_name, keywords, combo_keywords)
                        if matched_name:
                            # 处理匹配的文件
                            if self._process_matched_file(file_path, filename, base_dest, matched_name):
                                matched += 1
                    except Exception as e:
                        error_msg = f"处理文件 {filename} 时发生错误"
                        self._log_error("文件处理错误", error_msg, str(e))
                        skipped += 1
                        # 继续处理下一个文件，不中断整个过程
                        continue
            
            # 完成处理
            self._finalize_processing(src, base_dest, keywords, exclude_keywords, total_files, matched, skipped)
            
        except FileNotFoundError as e:
            error_msg = f"源文件夹或目标文件夹不存在：{str(e)}"
            self._log_error("路径错误", error_msg)
            messagebox.showerror("错误", error_msg)
        except PermissionError as e:
            error_msg = f"没有权限访问文件夹或文件：{str(e)}"
            self._log_error("权限错误", error_msg)
            messagebox.showerror("错误", error_msg)
        except Exception as e:
            error_msg = f"操作失败：{str(e)}"
            self._log_error("未知错误", error_msg)
            messagebox.showerror("错误", error_msg)
        finally:
            def reset_progress():
                self.progress_bar.update_progress(0)
                # 重置统计信息
                self.processing_speed_var.set("处理速度：0 文件/秒")
                self.elapsed_time_var.set("已用时间：00:00")
            self.window.after_idle(reset_progress)

if __name__ == "__main__":
    app = FileOrganizerApp()
    app.window.mainloop()