import pytesseract
from PIL import Image
import sys

# 设置 Tesseract 路径（Windows 用户必须修改）
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

print("Tesseract版本:", pytesseract.get_tesseract_version())
print("可用语言包:", pytesseract.get_languages())

# 如果提供了图像路径，尝试识别
if len(sys.argv) > 1:
    image_path = sys.argv[1]
    try:
        print(f"正在识别图像: {image_path}")
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang='chi_sim')
        print("识别结果:")
        print(text)
    except Exception as e:
        print(f"处理图像时出错: {e}")
else:
    print("使用方法: python test_ocr.py 图像路径") 