import os
import json
import re
import time
import requests

API_KEY = ""
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

headers = {
    "Content-Type": "application/json"
}

output_path = "destination_triples.json"
processed_keys = set()

# === BƯỚC 1: Đọc các dòng đã xử lý (nếu có) ===
if os.path.exists(output_path):
    with open(output_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                key = (record["id"], record["chunk_index"])
                processed_keys.add(key)
            except:
                continue

# === BƯỚC 2: Đọc dữ liệu đầu vào ===
with open("/content/destination.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# === BƯỚC 3: Chia văn bản thành các đoạn nhỏ (chunk) ===
def split_text(text, max_words=1000):
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

# === BƯỚC 4: Gửi từng đoạn vào API và ghi kết quả ===
MAX_RETRIES = 5
BASE_DELAY = 2  # seconds
WAIT_AFTER_N_REQUESTS = 10
LONG_SLEEP_SECONDS = 60

request_count = 0

with open(output_path, "a", encoding="utf-8") as out_f:
    for item in data:
        _id = item.get("id", "unknown")
        description = item.get("description", "").strip()

        if not description:
            continue

        chunks = split_text(description)

        for i, chunk in enumerate(chunks):
            key = (_id, i)
            if key in processed_keys:
                print(f"⏭️ Bỏ qua {_id} đoạn {i} (đã xử lý)")
                continue

            prompt = f"""Bạn là một công cụ trích xuất thông tin để xây dựng đồ thị tri thức du lịch – lịch sử Việt Nam.

            Yêu cầu:
            - Từ một đoạn văn bản đầu vào (tiếng Việt), hãy trích xuất các bộ ba (triple) theo định dạng JSON: {{"subject": "...", "relation": "...", "object": "..."}}
            - Mỗi dòng đại diện cho một quan hệ.
            - Tập trung vào các mối quan hệ sau:
                - (Địa điểm, nổi tiếng với, Sự kiện lịch sử)
                - (Địa điểm, liên quan đến, Nhân vật lịch sử)
                - (Địa điểm, nằm ở, Tỉnh/Thành phố)
                - (Địa điểm, có, Lễ hội truyền thống)
                - (Địa điểm, nổi tiếng với, Món ăn đặc sản)
                - (Địa điểm, thu hút, Khách du lịch)
                - (Địa điểm, có hoạt động, Trải nghiệm du lịch cụ thể)
                - (Địa điểm, có, Dịch vụ du lịch)
                - (Tuyến du lịch, đi qua, Địa điểm)
                - (Di sản văn hóa, được UNESCO công nhận, Loại hình)
                - (Địa điểm, có, Khách sạn / resort / dịch vụ)

            Ví dụ:
            title: Rừng tràm Trà Sư
            description: Rừng tràm Trà Sư nằm tại huyện Tịnh Biên, tỉnh An Giang. Đây là khu rừng đặc dụng có vai trò quan trọng trong thời kháng chiến.

            Kết quả:
            [
              {{"subject": "Rừng tràm Trà Sư", "relation": "nằm tại", "object": "huyện Tịnh Biên"}},
              {{"subject": "Rừng tràm Trà Sư", "relation": "nằm ở", "object": "An Giang"}},
              {{"subject": "Rừng tràm Trà Sư", "relation": "thuộc tỉnh", "object": "An Giang"}},
              {{"subject": "Rừng tràm Trà Sư", "relation": "có vai trò", "object": "trong thời kháng chiến"}},
              {{"subject": "Rừng tràm Trà Sư", "relation": "nổi tiếng với", "object": "thời kháng chiến"}},
              {{"subject": "Rừng tràm Trà Sư", "relation": "là", "object": "khu rừng đặc dụng"}}
            ]

            Đoạn văn đầu vào:
            {chunk}
            → Triple:
            Hãy trả về chỉ các triple dưới dạng JSON như trên, không thêm lời giải thích."""

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt.strip()}
                        ]
                    }
                ]
            }

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = requests.post(API_URL, headers=headers, json=payload)
                    if response.status_code == 429:
                        raise Exception("429 Too Many Requests")

                    response.raise_for_status()
                    res_data = response.json()
                    generated_text = res_data["candidates"][0]["content"]["parts"][0]["text"]

                    if generated_text.startswith("```json"):
                        generated_text = re.sub(r"^```json\s*", "", generated_text)
                    if generated_text.endswith("```"):
                        generated_text = re.sub(r"\s*```$", "", generated_text)

                    # match = re.search(r"```json\s*(.*?)\s*```", generated_text, re.DOTALL)
                    # if match:
                    #     json_text = match.group(1).strip()
                    # else:
                    #     json_text = generated_text.strip()  # fallback nếu không có markdown wrapper

                    try:
                        parsed = json.loads(generated_text.strip())
                        # parsed = json.loads(json_text)                        
                        if isinstance(parsed, list):
                            triples = parsed
                        elif isinstance(parsed, dict) and "triples" in parsed:
                            triples = parsed["triples"]
                        else:
                            raise ValueError("Không nhận được định dạng list hoặc dict hợp lệ.")
                    except Exception as parse_err:
                        print(f"❌ Không parse được JSON: {parse_err}")
                        print("Nội dung trả về:\n", response.text)
                        triples = []

                    record = {
                        "id": _id,
                        "chunk_index": i,
                        "triples": triples,
                        "text": chunk
                    }

                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    out_f.flush()
                    print(f"✅ Đã xử lý: {_id} - đoạn {i+1}/{len(chunks)}")

                    request_count += 1
                    if request_count % WAIT_AFTER_N_REQUESTS == 0:
                        print(f"⏳ Nghỉ {LONG_SLEEP_SECONDS} giây sau {WAIT_AFTER_N_REQUESTS} request...")
                        time.sleep(LONG_SLEEP_SECONDS)
                    else:
                        time.sleep(5)

                    break  # thành công thì dừng retry

                except Exception as e:
                    print(f"❌ Lỗi (attempt {attempt}) với {_id} - đoạn {i+1}: {e}")
                    if attempt == MAX_RETRIES:
                        print("⚠️ Bỏ qua sau khi retry quá nhiều lần.")
                        break
                    else:
                        sleep_time = BASE_DELAY * (2 ** (attempt - 1))
                        print(f"🔁 Đợi {sleep_time:.1f}s rồi thử lại...")
                        time.sleep(sleep_time)
