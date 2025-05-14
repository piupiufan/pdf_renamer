# 身份证号码识别与文件重命名工具

这是一个批量处理PDF或图片文件，识别其中的中国大陆身份证号码并将文件重命名为识别到的身份证号码的工具。

## 功能特点

- 支持PDF文件和常见图片格式(JPG, PNG, TIFF, BMP)
- 自动处理PDF文本和图像识别
- 支持单个文件或批量处理整个目录
- 可选择递归处理子目录
- 使用正则表达式准确匹配身份证号码格式

## 安装依赖

```bash
pip install -r requirements.txt
```

另外，本程序依赖Tesseract OCR引擎，需要单独安装：

### Windows安装Tesseract

1. 从[此处](https://github.com/UB-Mannheim/tesseract/wiki)下载并安装Tesseract
2. 确保安装中文语言包（chi_sim）
3. 将Tesseract的安装路径添加到系统环境变量，或在代码中取消注释并设置`pytesseract.pytesseract.tesseract_cmd`

### Linux安装Tesseract

```bash
sudo apt update
sudo apt install tesseract-ocr
sudo apt install tesseract-ocr-chi-sim
```

### macOS安装Tesseract

```bash
brew install tesseract
brew install tesseract-lang
```

## 使用方法

### 处理单个文件

```bash
python id_card_extractor.py 文件路径
```

### 处理目录中的所有文件

```bash
python id_card_extractor.py 目录路径
```

### 递归处理目录及其子目录

```bash
python id_card_extractor.py 目录路径 -r
```

## 示例

```bash
# 处理单个PDF文件
python id_card_extractor.py 扫描件.pdf

# 处理目录中的所有文件
python id_card_extractor.py ./身份证扫描文件/

# 递归处理目录及其子目录
python id_card_extractor.py ./档案文件夹/ -r
```

## 注意事项

1. 识别结果取决于OCR质量，请确保图像清晰度
2. 如果文件已经以正确的身份证号码命名，将保持不变
3. 如果目标文件名已存在，将不会进行重命名操作
4. 程序会自动忽略不支持的文件类型 

## 故障排除

如果程序无法运行，请按照以下步骤解决：

1. **确认Tesseract安装**
   
   Windows用户必须安装Tesseract OCR并设置正确的路径：
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```
   
   请根据您的实际安装路径修改上述代码。

2. **验证Tesseract安装**
   
   运行测试脚本确认Tesseract工作正常：
   ```
   python test_ocr.py 图片路径
   ```

3. **使用简化版本进行测试**
   
   如果完整程序有问题，可以尝试使用简化版本：
   ```
   python simple_extractor.py 图片路径
   ```

4. **常见错误**

   - `FileNotFoundError: [WinError 2]`: Tesseract路径设置错误
   - `TesseractNotFoundError`: 未安装Tesseract或路径错误  
   - `ImportError: DLL load failed`: 缺少必要的Windows DLL文件
   - `pytesseract.pytesseract.TesseractError: (1, 'Error opening data file')`: 缺少语言包，确保安装了中文语言包(chi_sim)

5. **语言包问题**
   
   确保安装了中文简体语言包。在Windows安装Tesseract时勾选"Chinese (Simplified)"选项。

6. **路径问题**
   
   Windows路径中如有空格，确保使用原始字符串(前缀r)：
   ```
   python id_card_extractor.py "C:\Users\用户名\Desktop\文件夹"
   ``` 