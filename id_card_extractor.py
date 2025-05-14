#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import argparse
from pathlib import Path
import PyPDF2
import pytesseract
from PIL import Image
import fitz  # PyMuPDF，用于从PDF提取图像

# 中国大陆身份证号码正则表达式
ID_CARD_PATTERN = r'[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|10|11|12)(?:0[1-9]|[1-2]\d|30|31)\d{3}[\dXx]'

def extract_text_from_image(image_path):
    """从图像中提取文本"""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang='chi_sim')
        return text
    except Exception as e:
        print(f"处理图像时出错: {image_path}, 错误: {e}")
        return ""

def extract_text_from_pdf(pdf_path):
    """从PDF中提取文本"""
    try:
        # 尝试使用PyPDF2直接提取文本
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text() or ""
        
        # 如果文本为空或很少，说明PDF可能是扫描件，使用PyMuPDF提取图像
        if len(text.strip()) < 50:
            print(f"PDF {pdf_path} 可能是扫描件，尝试提取图像...")
            text = extract_text_from_pdf_images(pdf_path)
        
        return text
    except Exception as e:
        print(f"处理PDF时出错: {pdf_path}, 错误: {e}")
        return ""

def extract_text_from_pdf_images(pdf_path):
    """从PDF中提取图像并进行OCR识别"""
    try:
        text = ""
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text += pytesseract.image_to_string(img, lang='chi_sim')
        doc.close()
        return text
    except Exception as e:
        print(f"从PDF提取图像时出错: {pdf_path}, 错误: {e}")
        return ""

def find_id_card_number(text):
    """在文本中查找身份证号码"""
    match = re.search(ID_CARD_PATTERN, text)
    return match.group(0) if match else None

def process_file(file_path):
    """处理单个文件，识别身份证号码并重命名"""
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        return False
    
    print(f"正在处理: {file_path}")
    
    # 根据文件类型提取文本
    text = ""
    if file_path.suffix.lower() == '.pdf':
        text = extract_text_from_pdf(file_path)
    elif file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']:
        text = extract_text_from_image(file_path)
    else:
        print(f"不支持的文件类型: {file_path}")
        return False
    
    # 查找身份证号码
    id_number = find_id_card_number(text)
    if not id_number:
        print(f"未找到身份证号码: {file_path}")
        return False
    
    # 重命名文件
    new_path = file_path.parent / f"{id_number}{file_path.suffix}"
    
    # 检查是否有重名文件
    if new_path.exists() and file_path != new_path:
        print(f"目标文件已存在，无法重命名: {new_path}")
        return False
    
    if file_path == new_path:
        print(f"文件已经以身份证号码命名: {file_path}")
        return True
    
    try:
        file_path.rename(new_path)
        print(f"重命名成功: {file_path} -> {new_path}")
        return True
    except Exception as e:
        print(f"重命名失败: {file_path}, 错误: {e}")
        return False

def process_directory(directory_path, recursive=False):
    """处理目录中的所有PDF和图像文件"""
    directory_path = Path(directory_path)
    if not directory_path.exists() or not directory_path.is_dir():
        print(f"目录不存在: {directory_path}")
        return
    
    print(f"正在处理目录: {directory_path}")
    
    # 获取所有文件
    file_list = []
    if recursive:
        for file_path in directory_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']:
                file_list.append(file_path)
    else:
        for file_path in directory_path.glob('*'):
            if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']:
                file_list.append(file_path)
    
    success_count = 0
    fail_count = 0
    
    for file_path in file_list:
        if process_file(file_path):
            success_count += 1
        else:
            fail_count += 1
    
    print(f"处理完成，成功: {success_count}，失败: {fail_count}")

def main():
    parser = argparse.ArgumentParser(description='批量识别身份证号码并重命名文件')
    parser.add_argument('path', help='文件或目录路径')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    
    args = parser.parse_args()
    path = Path(args.path)
    
    # 设置 Tesseract 路径（Windows 用户必须修改）
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    if path.is_file():
        process_file(path)
    elif path.is_dir():
        process_directory(path, args.recursive)
    else:
        print(f"路径不存在: {path}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"程序异常: {e}") 