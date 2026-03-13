from ast import parse
import requests
import json
import os
import re

API_KEY = ""
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

headers = {
    "Content-Type": "application/json"
}

output_path = "destination_triples_v2.json"
processed_keys = set()

# === BƯỚC 2: Nếu file kết quả đã có, đọc các đoạn đã xử lý ===
if os.path.exists(output_path):
    with open(output_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                key = (record["id"], record["chunk_index"])
                processed_keys.add(key)
            except:
                continue

# === BƯỚC 3: Đọc file JSON input ===
with open("/content/destination.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# === BƯỚC 4: Hàm chia nhỏ văn bản theo từ ===
def split_text(text, max_words=1000):
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

# === BƯỚC 5: Gửi request API từng đoạn và lưu từng dòng ===
import time

MAX_RETRIES = 5
BASE_DELAY =5  # giây
WAIT_AFTER_N_REQUESTS = 10
LONG_SLEEP_SECONDS = 60

request_count = 0  # Đếm số request thành công liên tiếp

with open(output_path, "a", encoding="utf-8") as out_f:
    for item in data:
        id = item.get("id", "unknown")
        description = item.get("description", "").strip()

        if not description:
            continue

        chunks = split_text(description)

        for i, chunk in enumerate(chunks):
            key = (id, i)
            if key in processed_keys:
                print(f"⏭️ Bỏ qua {id} đoạn {i} (đã xử lý)")
                continue

            prompt = f"""Bạn là một công cụ trích xuất thông tin để xây dựng đồ thị tri thức du lịch – lịch sử Việt Nam.
            Mục tiêu: Từ một đoạn văn bản đầu vào (tiếng Việt), hãy trích xuất các bộ ba (triple) theo định dạng JSON:[{{"subject": "...", "subject_type": "...", "relation": "...", "object": "...", "object_type": "..."}}]
            - Các loại thực thể có thể bao gồm:
               - Địa danh (Location)
               - Nhân vật lịch sử có thật, có vai trò cụ thể (HistoricalFigure)
               - Người hiện đại (du khách, hướng dẫn viên, người kể chuyện...) (Person)
               - Di tích / Công trình (Place)
               - Sự kiện (Event)
               - Mốc thời gian lịch sử, thời kỳ, thế kỷ (Time)
               - Triều đại (Dynasty)
               - Tác phẩm / Tài liệu (Work)
               - Dân tộc / Tôn giáo (Ethnic, Religion)
               - Tổ chức / Cơ quan liên quan tới lịch sử hoặc du lịch (Organization)
               - Lễ hội truyền thống gắn với văn hóa – lịch sử (Festival)
               - Di sản, cổ vật, công trình lịch sử (Heritage / Artifact / Historical Structure)
               - Món ăn truyền thống, đặc sản vùng miền (Cuisine)
               - Tuyến du lịch, hành trình di chuyển (Route)
            - Các loại quan hệ có thể bao gồm:
               - Thực thể nằm trong địa danh (located_in)
               - Sự kiện xảy ra ở địa điểm (happened_in)
               - Nhân vật sáng lập địa điểm, triều đại (founded)
               - được xây bởi (built_by)
               - nằm ở (is_located_in)
               - diễn ra tại (takes_place_in)
               - xảy ra vào (happened_on / occurred_on)
               - được phong kiến dưới (under_feudal_rule_of)
               - thuộc về (belongs_to)
               - có liên quan đến (related_to)
               - là thủ đô của (is_capital_of)
               - là nhân vật trong (character_in / mentioned_in)
               - được thành lập vào (founded_on / established_in)
               - thờ ai (worships / dedicated_to)
               - được công nhận là (recognized_as)
               - Gắn với thời kỳ lịch sử (belongs_to_period)
               - Gắn với lễ hội (has_festival)
               - Gắn với món ăn đặc sản vùng miền (features_cuisine)
               - Tham gia sự kiện (participated_in)
               - Cai trị thời kỳ (ruled)
               - Gần địa danh khác (next_to) 
               - Gợi ý tuyến du lịch (suggests_route_to)
               - Gợi ý sự kiện lịch sử tại điểm đến (related_to_event)
            - Nếu thực thể hoặc quan hệ không rõ, hãy suy luận hợp lý từ văn cảnh.
            Yêu cầu:
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
                - (Place, nổi tiếng với, Event)
                - (Place, liên quan đến, HistoricalFigure)
                - (Place, nằm ở, Tỉnh/Thành phố)
                - (Place, có, Festival)
                - (Place, nổi tiếng với, Cuisine)
                - (Place, thu hút, Person/du khách)
                - (Place, có hoạt động, Trải nghiệm du lịch)
                - (Place, có, Dịch vụ du lịch / khách sạn / resort)
                - (Route, đi qua, Place)
                - (Artifact, được UNESCO công nhận, Loại hình
            Ví dụ:
            title: Rừng tràm Trà Sư
            description: Rừng tràm Trà Sư nằm tại huyện Tịnh Biên, tỉnh An Giang. Đây là khu rừng đặc dụng có vai trò quan trọng trong thời kháng chiến.

            Kết quả:
            [
              {{
                "subject": "Rừng tràm Trà Sư",
                "subject_type": "Place",
                "relation": "located_in",
                "object": "Tịnh Biên",
                "object_type": "Place"
              }},
              {{
                "subject": "Rừng tràm Trà Sư",
                "subject_type": "Place",
                "relation": "located_in",
                "object": "An Giang",
                "object_type": "Place"
              }},
              {{
                "subject": "Rừng tràm Trà Sư",
                "subject_type": "Place",
                "relation": "associated_with",
                "object": "thời kháng chiến",
                "object_type": "TimePeriod"
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
                        "id": id,
                        "chunk_index": i,
                        "triples": triples,
                        "text": chunk
                    }

                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    out_f.flush()
                    print(f"✅ Đã xử lý: {id} - đoạn {i+1}/{len(chunks)}")

                    request_count += 1
                    if request_count % WAIT_AFTER_N_REQUESTS == 0:
                        print(f"⏳ Nghỉ {LONG_SLEEP_SECONDS} giây sau {WAIT_AFTER_N_REQUESTS} request...")
                        time.sleep(LONG_SLEEP_SECONDS)
                    else:
                        time.sleep(5)  # delay ngắn giữa các request

                    break  # thành công thì thoát retry loop

                except Exception as e:
                    print(f"❌ Lỗi (attempt {attempt}) với {id} - đoạn {i+1}: {e}")
                    if attempt == MAX_RETRIES:
                        print("⚠️ Bỏ qua sau khi retry quá nhiều lần.")
                        break
                    else:
                        sleep_time = BASE_DELAY * (2 ** (attempt - 1))
                        print(f"🔁 Đợi {sleep_time:.1f}s rồi thử lại...")
                        time.sleep(sleep_time)
