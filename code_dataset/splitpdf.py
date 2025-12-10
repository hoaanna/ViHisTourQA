import os
from PyPDF2 import PdfReader, PdfWriter

def split_pdf_to_parts(input_pdf, output_dir, prefix="LS3", parts=6):
    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    pages_per_part = total_pages // parts
    extra_pages = total_pages % parts  # số trang dư

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    start = 0
    for i in range(parts):
        writer = PdfWriter()
        # Nếu còn trang dư thì chia đều vào các phần đầu
        end = start + pages_per_part + (1 if i < extra_pages else 0)

        for j in range(start, end):
            writer.add_page(reader.pages[j])

        output_path = os.path.join(output_dir, f"{prefix}_{i+1}.pdf")
        with open(output_path, 'wb') as f:
            writer.write(f)

        print(f"Created: {output_path} (pages {start+1} to {end})")
        start = end

# Ví dụ sử dụng
split_pdf_to_parts("./lich_su_pdfs/LS03.pdf", "output_parts", prefix="LS3", parts=10)
split_pdf_to_parts("./lich_su_pdfs/LS07.pdf", "output_parts", prefix="LS7", parts=10)
