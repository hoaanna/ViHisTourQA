import os
import time
from google.cloud import vision_v1
from google.cloud import storage

# ================== CẤU HÌNH ==================
bucket_name = "my-ocr-history-tourism-bucket"
local_folder = "output_parts"  # thư mục chứa các file PDF
output_prefix_base = "ocr-results/"
batch_size = 20  # mỗi lần xử lý 20 trang
# =============================================

def async_ocr_pdf(pdf_file_name):
    gcs_input_uri = f"gs://{bucket_name}/{pdf_file_name}"
    gcs_output_prefix = f"{output_prefix_base}{pdf_file_name}/"
    gcs_output_uri = f"gs://{bucket_name}/{gcs_output_prefix}"

    print(f"[🔁] Gửi OCR cho {pdf_file_name}...")
    client = vision_v1.ImageAnnotatorClient()
    mime_type = "application/pdf"

    feature = vision_v1.Feature(type_=vision_v1.Feature.Type.DOCUMENT_TEXT_DETECTION)
    gcs_source = vision_v1.GcsSource(uri=gcs_input_uri)
    input_config = vision_v1.InputConfig(gcs_source=gcs_source, mime_type=mime_type)

    gcs_destination = vision_v1.GcsDestination(uri=gcs_output_uri)
    output_config = vision_v1.OutputConfig(gcs_destination=gcs_destination, batch_size=batch_size)

    request = vision_v1.AsyncAnnotateFileRequest(
        features=[feature],
        input_config=input_config,
        output_config=output_config,
    )

    operation = client.async_batch_annotate_files(requests=[request])
    print(" ⏳ Đang xử lý...")
    operation.result(timeout=600)
    print(" ✅ Xong!")

    return gcs_output_prefix

def download_and_extract_text(bucket_name, gcs_output_prefix, output_file):
    print(f"[📥] Tải kết quả về: {output_file}")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=gcs_output_prefix))

    all_text = ""
    for blob in blobs:
        if blob.name.endswith(".json"):
            json_data = blob.download_as_text()
            response = vision_v1.AnnotateFileResponse.from_json(json_data)
            for r in response.responses:
                if r.full_text_annotation.text:
                    all_text += r.full_text_annotation.text + "\n"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(all_text)
    print(f"[💾] Đã lưu: {output_file}")

def main():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    pdf_files = [f for f in os.listdir(local_folder) if f.lower().endswith(".pdf")]

    for file_name in pdf_files:
        local_path = os.path.join(local_folder, file_name)

        # 1. Upload file
        blob = bucket.blob(file_name)
        if not blob.exists():
            print(f"[⏫] Upload {file_name}...")
            blob.upload_from_filename(local_path)
            print(f" ✅ Uploaded {file_name}")
        else:
            print(f" ⚠️  Đã có trên bucket: {file_name}")

        # 2. Gửi OCR
        output_prefix = async_ocr_pdf(file_name)
        time.sleep(30)  # chờ GCS sync file JSON

        # 3. Tải kết quả & lưu text
        output_txt = f"{os.path.splitext(file_name)[0]}.txt"
        download_and_extract_text(bucket_name, output_prefix, output_txt)

if __name__ == "__main__":
    main()
