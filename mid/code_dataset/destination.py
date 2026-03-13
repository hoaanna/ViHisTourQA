import requests
from bs4 import BeautifulSoup
import time
import json
from tqdm import tqdm
import os

OUTPUT_FILE = "destination.jsonl"

def scrape_destination(item_id):
    url = f"https://csdl.vietnamtourism.gov.vn/dest/?item={item_id}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        title_tag = soup.find("h4")
        if not title_tag:
            return None
        title = title_tag.get_text(strip=True)
        
        desc_p = title_tag.find_next_sibling("p")
        desc_tags = soup.find_all("div", class_="col-12 py-2 content-detail")
        description_parts = [tag.get_text(separator="\n", strip=True) for tag in desc_tags]
        description = "\n\n".join(description_parts)
        
        info = {}
        labels = soup.find_all(["strong", "b"])
        for lb in labels:
            key = lb.get_text(strip=True).rstrip(":")
            value = lb.next_sibling.strip() if lb.next_sibling else ""
            if key and value:
                info[key] = value

        return {
            "id": item_id,
            "title": title,
            "description": description,
            "metadata": info
        }

    except Exception as e:
        print(f"Lỗi tại item {item_id}: {e}")
        return None

# ==== Đọc các item_id đã lưu (nếu có) ====
saved_ids = set()
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                saved_ids.add(obj["id"])
            except:
                continue

print(f"Đã có {len(saved_ids)} item được lưu từ trước.")

# ==== Cào và lưu từng dòng ====
with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
    for item_id in tqdm(range(1, 1201), desc="Crawl Destination"):
        if item_id in saved_ids:
            continue
        data = scrape_destination(item_id)
        if data:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
            f.flush()  # đảm bảo ghi ngay ra đĩa
            print(f"Ghi item {item_id}: {data['title']}")
        else:
            print(f"Bỏ qua item {item_id}")
        time.sleep(1)  # tránh bị chặn


import json

with open("destination.jsonl", "r", encoding="utf-8") as f:
    data = [json.loads(line) for line in f]

with open("destination.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
