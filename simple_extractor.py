#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
from pathlib import Path
import pytesseract
from PIL import Image

# 设置 Tesseract 路径（Windows 用户必须修改）
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 中国大陆身份证号码正则表达式
ID_CARD_PATTERN = r'[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|10|11|12)(?:0[1-9]|[1-2]\d|30|31)\d{3}[\dXx]'

def extract_text_from_image(image_path):
    """从图像中提取文本"""
    try:
        print(f"正在处理图像: {image_path}")
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang='chi_sim')
        print("提取的文本片段:")
        print(text[:200] + "..." if len(text) > 200 else text)
        return text
    except Exception as e:
        print(f"处理图像时出错: {image_path}, 错误: {e}")
        return ""

def find_id_card_number(text):
    """在文本中查找身份证号码"""
    match = re.search(ID_CARD_PATTERN, text)
    return match.group(0) if match else None

def main():
    if len(sys.argv) < 2:
        print("使用方法: python simple_extractor.py 图像文件路径")
        return
    
    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        return
    
    # 仅处理图像文件
    if file_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']:
        print(f"不支持的文件类型: {file_path}")
        return
    
    # 提取文本
    text = extract_text_from_image(file_path)
    
    # 查找身份证号码
    id_number = find_id_card_number(text)
    if not id_number:
        print(f"未找到身份证号码: {file_path}")
        return
    
    print(f"找到身份证号码: {id_number}")
    
    # 重命名文件
    new_path = file_path.parent / f"{id_number}{file_path.suffix}"
    
    print(f"准备将文件从 {file_path} 重命名为 {new_path}")
    
    # 检查是否有重名文件
    if new_path.exists() and file_path != new_path:
        print(f"目标文件已存在，无法重命名: {new_path}")
        return
    
    if file_path == new_path:
        print(f"文件已经以身份证号码命名: {file_path}")
        return
    
    try:
        file_path.rename(new_path)
        print(f"重命名成功: {file_path} -> {new_path}")
    except Exception as e:
        print(f"重命名失败: {file_path}, 错误: {e}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"程序异常: {e}")
        import traceback
        traceback.print_exc() 