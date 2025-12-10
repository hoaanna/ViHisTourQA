import requests
import json

# === BƯỚC 1: Thiết lập API Key & Endpoint ===
API_KEY = "AIzaSyDMyUNDxmUNEAa39a3vWSCMG8FpScgIeco"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

# === BƯỚC 2: Đọc file .txt ===
with open("lich_su_2.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()

# === BƯỚC 3: Chia đoạn văn bản (ví dụ mỗi đoạn 1000 từ) ===
def split_text(text, max_words=1000):
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

chunks = split_text(raw_text)

# === BƯỚC 4: Gửi request API từng đoạn ===
headers = {
    "Content-Type": "application/json"
}

results = []

for i, chunk in enumerate(chunks):
    prompt = f"""
    Dựa trên nội dung sau, hãy tạo 10 cặp câu hỏi và câu trả lời theo định dạng JSON:

    ---
    {chunk}
    """

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt.strip()
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()  # báo lỗi nếu không phải 2xx

        data = response.json()
        generated_text = data["candidates"][0]["content"]["parts"][0]["text"]
        print(f"✅ Đã xử lý đoạn {i+1}/{len(chunks)}")
        results.append(generated_text)
    except Exception as e:
        print(f"❌ Lỗi đoạn {i+1}: {e}")

# === BƯỚC 5: Ghi kết quả ra file ===
with open("output_qa_2.jsonl", "w", encoding="utf-8") as f:
    for item in results:
        f.write(item.strip() + "\n")
