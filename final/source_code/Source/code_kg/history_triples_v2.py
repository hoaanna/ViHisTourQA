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

output_path = "history_triples_v2.json"
processed_keys = set()

# === BƯỚC 2: Nếu file kết quả đã có, đọc các đoạn đã xử lý ===
if os.path.exists(output_path):
    with open(output_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                key = (record["formId"], record["chunk_index"])
                processed_keys.add(key)
            except:
                continue

# === BƯỚC 3: Đọc file JSON input ===
with open("/content/history_form.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# === BƯỚC 4: Hàm chia nhỏ văn bản theo từ ===
def split_text(text, max_words=1000):
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

# === BƯỚC 5: Gửi request API từng đoạn và lưu từng dòng ===
MAX_RETRIES = 5
BASE_DELAY = 2  # giây
WAIT_AFTER_N_REQUESTS = 10
LONG_SLEEP_SECONDS = 60

request_count = 0  # Đếm số request thành công liên tiếp

with open(output_path, "a", encoding="utf-8") as out_f:
    for form in data:
        form_id = form.get("formId", "unknown")
        content = form.get("content", "").strip()

        if not content:
            continue

        chunks = split_text(content)

        for i, chunk in enumerate(chunks):
            key = (form_id, i)
            if key in processed_keys:
                print(f"Bỏ qua {form_id} đoạn {i} (đã xử lý)")
                continue

            prompt = f"""Bạn là một công cụ trích xuất thông tin để xây dựng đồ thị tri thức du lịch – lịch sử Việt Nam.
            Mục tiêu: Từ một đoạn văn bản đầu vào (tiếng Việt), hãy trích xuất các bộ ba (triple) theo định dạng JSON:[{{"subject": "...", "subject_type": "...", "relation": "...", "object": "...", "object_type": "..."}}]
            Các loại thực thể có thể bao gồm:
                - Địa danh (Location)
                - Nhân vật lịch sử có thật, có vai trò cụ thể (HistoricalFigure)
                - Di tích / Công trình (Place)
                - Sự kiện (Event)
                - Mốc thời gian lịch sử, thời kỳ, thế kỷ (Time)
                - Triều đại (Dynasty)
                - Tác phẩm / Tài liệu (Work)
                - Dân tộc / Tôn giáo (Ethnic, Religion)
                - Tổ chức / Cơ quan liên quan tới lịch sử hoặc du lịch (Organization)
                - Di sản, cổ vật, công trình lịch sử (Heritage / Artifact / Historical Structure)
            Các loại quan hệ có thể bao gồm:
                - Thực thể nằm trong địa danh (located_in)
                - Sự kiện xảy ra ở địa điểm (happened_in)
                - Nhân vật sáng lập địa điểm, triều đại (founded)
                - được xây bởi (built_by)
                - nằm ở (is_located_in)
                - diễn ra tại (takes_place_in)
                - xảy ra vào (happened_on)
                - được phong kiến dưới (under_feudal_rule_of)
                - thuộc về (belongs_to)
                - có liên quan đến (related_to)
                - là thủ đô của (is_capital_of)
                - là nhân vật trong (character_in / mentioned_in)
                - được thành lập vào (established_on)
                - thờ ai (worships / dedicated_to)
                - được công nhận là (recognized_as)
                - Gắn với thời kỳ lịch sử (belongs_to_period)
                - Cai trị thời kỳ (ruled)
            - Nếu thực thể hoặc quan hệ không rõ, hãy suy luận hợp lý từ văn cảnh.
            Yêu cầu:
            - Mỗi dòng đại diện cho một quan hệ
            - Tập trung vào các mối quan hệ sau:
                - (Place, nổi tiếng với, Event)
                - (Place, liên quan đến, HistoricalFigure)
                - (Place, nằm ở, Tỉnh/Thành phố)
                - (Event, diễn ra tại, Place)
                - (Sự kiện lịch sử, diễn ra tại, Địa điểm)
                - (Địa điểm, nổi tiếng với, Sự kiện lịch sử)
                - (Địa điểm, liên quan đến, Nhân vật lịch sử)
                - (Nhân vật lịch sử, tham gia, Sự kiện lịch sử)
                - (Địa điểm, nằm ở, Tỉnh/Thành phố)

            Ví dụ:
            Đoạn văn: "Chiến thắng Điện Biên Phủ năm 1954 là một dấu mốc quan trọng trong lịch sử Việt Nam. Trận đánh diễn ra tại thung lũng Điện Biên, tỉnh Điện Biên."
            Kết quả:
            [
              {{
                "subject": "Chiến thắng Điện Biên Phủ",
                "subject_type": "Event",
                "relation": "takes_place_in",
                "object": "thung lũng Điện Biên",
                "object_type": "Place"
              }},
              {{
                "subject": "thung lũng Điện Biên",
                "subject_type": "Place",
                "relation": "located_in",
                "object": "An Giang",
                "object_type": "Place"
              }}
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

                    # Bỏ markdown wrapper nếu có
                    if generated_text.startswith("```json"):
                        generated_text = re.sub(r"^```json\s*", "", generated_text)
                    if generated_text.endswith("```"):
                        generated_text = re.sub(r"\s*```$", "", generated_text)

                    print(f"✅ Đã xử lý: {form_id} - đoạn {i+1}/{len(chunks)}")
                   
                    # match = re.search(r"```json\s*(.*?)\s*```", generated_text, re.DOTALL)
                    # if match:
                    #     json_text = match.group(1).strip()
                    # else:
                    #     json_text = generated_text.strip()  # fallback nếu không có markdown wrapper

                    try:
                        parsed = json.loads(generated_text.strip())
                        # parsed = json.loads(json_text)
                        if isinstance(parsed, list):  # Nếu trả về list
                            triples = parsed
                        elif isinstance(parsed, dict) and "triples" in parsed:
                            triples = parsed["triples"]
                        else:
                            raise ValueError("Không nhận được format list hoặc dict hợp lệ.")
                    except Exception as parse_err:
                        print(f"❌ Không parse được JSON: {parse_err}")
                        print("Nội dung trả về:\n", response.text)
                        triples = []

                    record = {
                        "formId": form_id,
                        "chunk_index": i,
                        "triples": triples,
                        "text": chunk
                    }

                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    out_f.flush()

                    request_count += 1
                    if request_count % WAIT_AFTER_N_REQUESTS == 0:
                        print(f"⏳ Nghỉ {LONG_SLEEP_SECONDS} giây sau {WAIT_AFTER_N_REQUESTS} request...")
                        time.sleep(LONG_SLEEP_SECONDS)
                    else:
                        time.sleep(2)  # delay ngắn giữa các request

                    break  # thành công thì thoát retry loop

                except Exception as e:
                    print(f"❌ Lỗi (attempt {attempt}) với {form_id} - đoạn {i+1}: {e}")
                    if attempt == MAX_RETRIES:
                        print("⚠️ Bỏ qua sau khi retry quá nhiều lần.")
                        break
                    else:
                        sleep_time = BASE_DELAY * (2 ** (attempt - 1))
                        print(f"🔁 Đợi {sleep_time:.1f}s rồi thử lại...")
                        time.sleep(sleep_time)
