import pytesseract
import fitz  # PyMuPDF
from PIL import Image
import io
import os
import time

# Đường dẫn tới tesseract
pytesseract.pytesseract.tesseract_cmd = r"./Tesseract-OCR/tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"./Tesseract-OCR/tessdata"

def pdf_scan_to_text(pdf_path, lang="vie"):
    text_output = ""
    try:
        pdf_file = fitz.open(pdf_path)
    except Exception as e:
        print(f"❌ Không thể mở file PDF: {pdf_path}. Lỗi: {e}")
        return ""

    total_pages = len(pdf_file)
    print(f"🔍 Đang xử lý {pdf_path} ({total_pages} trang)...")

    for page_num in range(total_pages):
        try:
            page = pdf_file.load_page(page_num)
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, lang=lang)
            text_output += f"\n--- Trang {page_num + 1} ---\n{text.strip()}\n"

            # Hiển thị tiến độ
            print(f"✅ Đã xử lý trang {page_num + 1}/{total_pages}")
        except Exception as e:
            print(f"⚠️  Lỗi khi xử lý trang {page_num + 1}: {e}")

    return text_output

# Danh sách file PDF cần xử lý
pdf_files = [
    ("lich_su_pdfs/LS03.pdf", "output_03.txt"),
    ("lich_su_pdfs/LS07.pdf", "output_04.txt"),
]

start_time = time.time()

# Xử lý từng file
for pdf_path, output_txt in pdf_files:
    print(f"\n🚀 Bắt đầu xử lý file: {pdf_path}")
    text = pdf_scan_to_text(pdf_path)
    
    if text:
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"📁 Ghi xong vào {output_txt}")
    else:
        print(f"❌ Không có dữ liệu để ghi từ file {pdf_path}")

end_time = time.time()
print(f"\n⏱️ Hoàn tất toàn bộ! Tổng thời gian: {end_time - start_time:.2f} giây")
