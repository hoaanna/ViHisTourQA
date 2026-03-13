import os
import zipfile
import pdfplumber

# 🔧 Cấu hình đường dẫn
ZIP_PATH = "lich_su_viet_nam.zip"        # 📦 File .zip chứa 15 file PDF
EXTRACT_DIR = "lich_su_pdfs"             # 📁 Thư mục sau khi giải nén
TXT_OUTPUT_DIR = "lich_su_txts"          # 📁 Thư mục chứa file .txt
COMBINED_TXT_PATH = "lich_su_combined.txt"  # 📄 File tổng hợp tất cả

# 📦 Bước 1: Giải nén
def extract_zip(zip_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)
    print(f"✅ Đã giải nén vào: {output_dir}")

# 📄 Bước 2: Chuyển từng file PDF → TXT
def convert_pdfs_to_txt(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for filename in os.listdir(input_dir):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(input_dir, filename)
            txt_path = os.path.join(output_dir, filename.replace(".pdf", ".txt"))

            with pdfplumber.open(pdf_path) as pdf:
                all_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        all_text += page_text + "\n"

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(all_text)
            print(f"📄 Đã chuyển: {filename} → {txt_path}")

# 📘 Bước 3: Gộp tất cả TXT thành một file lớn
def combine_all_txt(input_dir, output_file):
    combined_text = ""
    for filename in sorted(os.listdir(input_dir)):
        if filename.endswith(".txt"):
            path = os.path.join(input_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                combined_text += f"\n\n--- {filename} ---\n\n"
                combined_text += f.read()

    with open(output_file, "w", encoding="utf-8") as out_f:
        out_f.write(combined_text)
    print(f"📘 Đã gộp tất cả thành: {output_file}")

# 🚀 Thực thi toàn bộ
if __name__ == "__main__":
    extract_zip(ZIP_PATH, EXTRACT_DIR)
    convert_pdfs_to_txt(EXTRACT_DIR, TXT_OUTPUT_DIR)
    combine_all_txt(TXT_OUTPUT_DIR, COMBINED_TXT_PATH)
    print("🎉 Hoàn tất toàn bộ quá trình!")

