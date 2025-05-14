#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext, simpledialog
from pathlib import Path
import PyPDF2
import pytesseract
from PIL import Image, ImageTk, ImageDraw
import fitz  # PyMuPDF

# 中国大陆身份证号码正则表达式
ID_CARD_PATTERN = r'[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|10|11|12)(?:0[1-9]|[1-2]\d|30|31)\d{3}[\dXx]'

class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""

    def write(self, string):
        self.buffer += string
        self.update_text_widget()
    
    def update_text_widget(self):
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, self.buffer)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')
        self.buffer = ""
    
    def flush(self):
        self.update_text_widget()

class IdCardExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("身份证号码识别与文件重命名")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        # 设置Tesseract路径
        self.tesseract_path = tk.StringVar(value=r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path.get()
        
        # 高级选项
        self.use_keywords = tk.BooleanVar(value=False)
        self.keywords = tk.StringVar(value="身份证,号码,姓名,性别,民族,出生")
        self.use_region = tk.BooleanVar(value=False)
        self.current_image = None
        self.current_image_path = None
        self.selected_region = None
        
        # 创建控件
        self.create_widgets()
        
        # 状态变量
        self.is_processing = False
        self.total_files = 0
        self.processed_files = 0
        self.success_count = 0
        self.fail_count = 0
    
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tesseract路径设置
        tesseract_frame = ttk.LabelFrame(main_frame, text="Tesseract设置", padding=5)
        tesseract_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(tesseract_frame, text="Tesseract路径:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(tesseract_frame, textvariable=self.tesseract_path, width=50).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        ttk.Button(tesseract_frame, text="浏览", command=self.browse_tesseract).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(tesseract_frame, text="测试", command=self.test_tesseract).grid(row=0, column=3, padx=5, pady=5)
        
        # 输入设置
        input_frame = ttk.LabelFrame(main_frame, text="输入设置", padding=5)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.path_var = tk.StringVar()
        ttk.Label(input_frame, text="路径:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(input_frame, textvariable=self.path_var, width=50).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        ttk.Button(input_frame, text="选择文件", command=self.browse_file).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(input_frame, text="选择文件夹", command=self.browse_directory).grid(row=0, column=3, padx=5, pady=5)
        
        self.recursive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(input_frame, text="递归处理子目录", variable=self.recursive_var).grid(row=1, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)
        
        # 高级设置
        advanced_frame = ttk.LabelFrame(main_frame, text="高级设置", padding=5)
        advanced_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 关键字
        keyword_frame = ttk.Frame(advanced_frame)
        keyword_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Checkbutton(keyword_frame, text="使用关键字搜索", variable=self.use_keywords).pack(side=tk.LEFT, padx=5)
        ttk.Label(keyword_frame, text="关键字(逗号分隔):").pack(side=tk.LEFT, padx=5)
        ttk.Entry(keyword_frame, textvariable=self.keywords, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 区域选择
        region_frame = ttk.Frame(advanced_frame)
        region_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Checkbutton(region_frame, text="使用区域选择", variable=self.use_region).pack(side=tk.LEFT, padx=5)
        ttk.Button(region_frame, text="选择示例图片", command=self.select_sample_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(region_frame, text="定义识别区域", command=self.define_region).pack(side=tk.LEFT, padx=5)
        self.region_label = ttk.Label(region_frame, text="未设置区域")
        self.region_label.pack(side=tk.LEFT, padx=5)
        
        # 操作按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="开始处理", command=self.start_processing).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(button_frame, text="停止", command=self.stop_processing).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(progress_frame, text="处理进度:").pack(side=tk.LEFT, padx=5, pady=5)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, length=600)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0/0")
        self.progress_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 日志输出
        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 重定向输出到日志窗口
        self.text_redirect = RedirectText(self.log_text)
        
        # 状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT, padx=5)
    
    def browse_tesseract(self):
        path = filedialog.askopenfilename(
            title="选择Tesseract可执行文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if path:
            self.tesseract_path.set(path)
    
    def test_tesseract(self):
        try:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path.get()
            version = pytesseract.get_tesseract_version()
            languages = pytesseract.get_languages()
            
            info = f"Tesseract版本: {version}\n可用语言包: {', '.join(languages)}"
            messagebox.showinfo("Tesseract测试", info)
            
            # 检查中文语言包
            if 'chi_sim' not in languages:
                messagebox.showwarning("警告", "未检测到中文简体语言包(chi_sim)，这可能会影响识别效果")
        except Exception as e:
            messagebox.showerror("错误", f"Tesseract测试失败: {e}")
    
    def browse_file(self):
        path = filedialog.askopenfilename(
            title="选择文件",
            filetypes=[
                ("所有支持的文件", "*.pdf;*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp"),
                ("PDF文件", "*.pdf"),
                ("图像文件", "*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp"),
                ("所有文件", "*.*")
            ]
        )
        if path:
            self.path_var.set(path)
    
    def browse_directory(self):
        path = filedialog.askdirectory(title="选择文件夹")
        if path:
            self.path_var.set(path)
    
    def start_processing(self):
        if self.is_processing:
            messagebox.showwarning("警告", "已有处理任务正在进行")
            return
        
        path = self.path_var.get()
        if not path:
            messagebox.showwarning("警告", "请选择文件或文件夹")
            return
        
        # 设置Tesseract路径
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path.get()
        
        # 清空日志
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        
        # 重置计数器
        self.total_files = 0
        self.processed_files = 0
        self.success_count = 0
        self.fail_count = 0
        
        # 更新UI
        self.status_label.config(text="正在处理...")
        self.is_processing = True
        
        # 在子线程中处理
        self.processing_thread = threading.Thread(target=self.process_path, args=(path,))
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # 启动更新UI的周期性任务
        self.root.after(100, self.update_ui)
    
    def stop_processing(self):
        if self.is_processing:
            self.is_processing = False
            self.status_label.config(text="已停止")
            print("处理已停止")
    
    def update_ui(self):
        if self.is_processing:
            # 更新进度条
            if self.total_files > 0:
                progress = self.processed_files / self.total_files * 100
                self.progress_var.set(progress)
                self.progress_label.config(text=f"{self.processed_files}/{self.total_files}")
            
            # 周期性更新UI
            self.root.after(100, self.update_ui)
        else:
            # 处理结束，更新最终UI状态
            if not self.processing_thread.is_alive():
                self.status_label.config(text=f"处理完成，成功: {self.success_count}，失败: {self.fail_count}")
                
                # 如果有处理结果，显示摘要
                if self.total_files > 0:
                    self.progress_var.set(100)
                    self.progress_label.config(text=f"{self.processed_files}/{self.total_files}")
                    messagebox.showinfo("处理完成", f"共处理{self.total_files}个文件\n成功: {self.success_count}\n失败: {self.fail_count}")
    
    def process_path(self, path):
        import sys
        # 重定向标准输出
        sys_stdout = sys.stdout
        sys.stdout = self.text_redirect
        
        try:
            path = Path(path)
            
            if path.is_file():
                self.total_files = 1
                success = self.process_file(path)
                self.processed_files = 1
                self.success_count += 1 if success else 0
                self.fail_count += 0 if success else 1
            elif path.is_dir():
                recursive = self.recursive_var.get()
                
                # 获取文件列表
                file_list = []
                if recursive:
                    for file_path in path.rglob('*'):
                        if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']:
                            file_list.append(file_path)
                else:
                    for file_path in path.glob('*'):
                        if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']:
                            file_list.append(file_path)
                
                self.total_files = len(file_list)
                print(f"找到{self.total_files}个文件需要处理")
                
                # 处理每个文件
                for file_path in file_list:
                    if not self.is_processing:
                        print("处理已取消")
                        break
                    
                    success = self.process_file(file_path)
                    self.success_count += 1 if success else 0
                    self.fail_count += 0 if success else 1
                    self.processed_files += 1
            
            print(f"处理完成，成功: {self.success_count}，失败: {self.fail_count}")
        except Exception as e:
            print(f"处理过程中发生错误: {e}")
            import traceback
            traceback.print_exc(file=sys.stdout)
        finally:
            # 恢复标准输出
            sys.stdout = sys_stdout
            self.is_processing = False
    
    def process_file(self, file_path):
        try:
            print(f"正在处理: {file_path}")
            
            # 根据文件类型提取文本
            text = ""
            if file_path.suffix.lower() == '.pdf':
                text = self.extract_text_from_pdf(file_path)
            elif file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']:
                text = self.extract_text_from_image(file_path)
            else:
                print(f"不支持的文件类型: {file_path}")
                return False
            
            # 查找身份证号码
            id_number = self.find_id_card_number(text)
            if not id_number:
                print(f"未找到身份证号码: {file_path}")
                return False
            
            print(f"找到身份证号码: {id_number}")
            
            # 重命名文件
            new_path = file_path.parent / f"{id_number}{file_path.suffix}"
            
            # 检查是否有重名文件
            if new_path.exists() and file_path != new_path:
                print(f"目标文件已存在，无法重命名: {new_path}")
                return False
            
            if file_path == new_path:
                print(f"文件已经以身份证号码命名: {file_path}")
                return True
            
            file_path.rename(new_path)
            print(f"重命名成功: {file_path} -> {new_path}")
            return True
        except Exception as e:
            print(f"处理文件时出错: {file_path}, 错误: {e}")
            return False
    
    def extract_text_from_image(self, image_path):
        try:
            image = Image.open(image_path)
            
            # 如果启用了区域选择
            if self.use_region.get() and self.selected_region is not None:
                # 裁剪图像到选定区域
                x1, y1, x2, y2 = self.selected_region
                image = image.crop((x1, y1, x2, y2))
            
            text = pytesseract.image_to_string(image, lang='chi_sim')
            
            # 显示提取的部分文本
            preview = text[:200] + "..." if len(text) > 200 else text
            print(f"提取的文本片段: {preview}")
            
            # 如果启用了关键字搜索
            if self.use_keywords.get():
                keyword_list = [k.strip() for k in self.keywords.get().split(',')]
                print(f"使用关键字进行搜索: {', '.join(keyword_list)}")
                
                # 检查文本中是否包含关键字
                found_keywords = []
                for keyword in keyword_list:
                    if keyword and keyword in text:
                        found_keywords.append(keyword)
                
                if found_keywords:
                    print(f"找到关键字: {', '.join(found_keywords)}")
                else:
                    print("未找到任何关键字")
                    if not self.find_id_card_number(text):
                        print("由于未找到关键字和身份证号码，跳过此文件")
                        return ""
            
            return text
        except Exception as e:
            print(f"处理图像时出错: {image_path}, 错误: {e}")
            return ""
    
    def extract_text_from_pdf(self, pdf_path):
        try:
            # 尝试使用PyPDF2直接提取文本
            text = ""
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page_num in range(len(reader.pages)):
                    text += reader.pages[page_num].extract_text() or ""
            
            # 如果启用了关键字搜索，先检查文本是否包含关键字
            if self.use_keywords.get() and text.strip():
                keyword_list = [k.strip() for k in self.keywords.get().split(',')]
                print(f"使用关键字进行搜索: {', '.join(keyword_list)}")
                
                # 检查文本中是否包含关键字
                found_keywords = []
                for keyword in keyword_list:
                    if keyword and keyword in text:
                        found_keywords.append(keyword)
                
                if found_keywords:
                    print(f"找到关键字: {', '.join(found_keywords)}")
                else:
                    print("未在PDF文本中找到任何关键字")
            
            # 如果文本为空或很少，说明PDF可能是扫描件，使用PyMuPDF提取图像
            if len(text.strip()) < 50:
                print(f"PDF {pdf_path} 可能是扫描件，尝试提取图像...")
                text = self.extract_text_from_pdf_images(pdf_path)
            
            # 显示提取的部分文本
            preview = text[:200] + "..." if len(text) > 200 else text
            print(f"提取的文本片段: {preview}")
            
            return text
        except Exception as e:
            print(f"处理PDF时出错: {pdf_path}, 错误: {e}")
            return ""
    
    def extract_text_from_pdf_images(self, pdf_path):
        try:
            text = ""
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # 如果启用了区域选择
                if self.use_region.get() and self.selected_region is not None:
                    # 裁剪图像到选定区域
                    x1, y1, x2, y2 = self.selected_region
                    img = img.crop((x1, y1, x2, y2))
                
                page_text = pytesseract.image_to_string(img, lang='chi_sim')
                text += page_text
                
                # 如果启用了关键字搜索，检查是否包含关键字
                if self.use_keywords.get() and page_num == 0:  # 只检查第一页
                    keyword_list = [k.strip() for k in self.keywords.get().split(',')]
                    
                    # 检查文本中是否包含关键字
                    found_keywords = []
                    for keyword in keyword_list:
                        if keyword and keyword in page_text:
                            found_keywords.append(keyword)
                    
                    if found_keywords:
                        print(f"在PDF图像中找到关键字: {', '.join(found_keywords)}")
                    else:
                        print("未在PDF图像中找到任何关键字")
                        if not self.find_id_card_number(text) and page_num == 0:
                            print("由于未找到关键字和身份证号码，可能识别难度较大")
            
            doc.close()
            return text
        except Exception as e:
            print(f"从PDF提取图像时出错: {pdf_path}, 错误: {e}")
            return ""
    
    def find_id_card_number(self, text):
        match = re.search(ID_CARD_PATTERN, text)
        return match.group(0) if match else None
    
    def select_sample_image(self):
        """选择一个示例图片来定义识别区域"""
        path = filedialog.askopenfilename(
            title="选择示例图片",
            filetypes=[
                ("图像文件", "*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp"),
                ("所有文件", "*.*")
            ]
        )
        if not path:
            return
        
        try:
            # 打开并显示图像
            self.current_image_path = path
            self.current_image = Image.open(path)
            
            # 显示图像，并让用户选择区域
            self.define_region()
        except Exception as e:
            messagebox.showerror("错误", f"无法打开图像: {e}")
    
    def define_region(self):
        """打开一个窗口让用户定义识别区域"""
        if self.current_image is None:
            messagebox.showwarning("警告", "请先选择一个示例图片")
            return
        
        # 创建图像预览窗口
        preview_window = tk.Toplevel(self.root)
        preview_window.title("选择识别区域")
        preview_window.geometry("800x600")
        
        # 限制图像尺寸
        img_width, img_height = self.current_image.size
        max_width, max_height = 700, 500
        scale = min(max_width/img_width, max_height/img_height)
        new_width, new_height = int(img_width * scale), int(img_height * scale)
        
        # 调整图像大小以适应窗口
        display_image = self.current_image.resize((new_width, new_height))
        photo = ImageTk.PhotoImage(display_image)
        
        # 创建一个画布来显示图像
        canvas = tk.Canvas(preview_window, width=new_width, height=new_height)
        canvas.pack(padx=10, pady=10)
        canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        
        # 存储画布上的矩形选择框
        rect_id = None
        start_x, start_y = 0, 0
        
        # 鼠标事件处理
        def on_mouse_down(event):
            nonlocal start_x, start_y, rect_id
            start_x, start_y = event.x, event.y
            if rect_id:
                canvas.delete(rect_id)
            rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)
        
        def on_mouse_move(event):
            nonlocal rect_id
            if rect_id:
                canvas.coords(rect_id, start_x, start_y, event.x, event.y)
        
        def on_mouse_up(event):
            nonlocal rect_id
            if rect_id:
                x1, y1, x2, y2 = canvas.coords(rect_id)
                # 确保坐标是按左上、右下排序的
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                
                # 转换回原始图像坐标
                orig_x1 = int(x1 / scale)
                orig_y1 = int(y1 / scale)
                orig_x2 = int(x2 / scale)
                orig_y2 = int(y2 / scale)
                
                # 存储选定的区域
                self.selected_region = (orig_x1, orig_y1, orig_x2, orig_y2)
                self.region_label.config(text=f"已设置区域: ({orig_x1}, {orig_y1}, {orig_x2}, {orig_y2})")
        
        # 绑定鼠标事件
        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_move)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        
        # 确认按钮
        ttk.Button(preview_window, text="确认选择", command=preview_window.destroy).pack(pady=10)
        
        # 保持对图像的引用，防止被垃圾回收
        preview_window.photo = photo
        
        # 等待窗口关闭
        self.root.wait_window(preview_window)

def main():
    root = tk.Tk()
    app = IdCardExtractorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 