import json

input_path = "output_triples.json"
output_path = "history_triples.json"

with open(input_path, "r", encoding="utf-8") as infile, \
     open(output_path, "w", encoding="utf-8") as outfile:

    for line in infile:
        entry = json.loads(line)
        raw_triples = entry.get("triples", "").strip()

        # Bỏ markdown wrapper nếu có
        if raw_triples.startswith("```json"):
            raw_triples = raw_triples[7:]
        if raw_triples.endswith("```"):
            raw_triples = raw_triples[:-3]

        # Cố gắng parse thành list
        try:
            triples = json.loads(raw_triples)
        except Exception:
            continue  # skip nếu không parse được

        # Kiểm tra triple có hợp lệ: là list các dict và mỗi dict có đầy đủ 3 trường
        valid_triples = []
        for triple in triples:
            if isinstance(triple, dict):
                # Trường hợp bị viết sai key: {"subject": ..., "quan hệ": ...}
                keys = list(triple.keys())
                if "subject" in triple and "relation" in triple and "object" in triple:
                    valid_triples.append(triple)
                elif "subject" in triple and len(keys) == 2:
                    rel_key = [k for k in keys if k != "subject"][0]
                    valid_triples.append({
                        "subject": triple["subject"],
                        "relation": rel_key,
                        "object": triple[rel_key]
                    })

        # Bỏ dòng nếu không có triple hợp lệ
        if not valid_triples:
            continue

        # Ghi lại
        entry["triples"] = valid_triples
        json.dump(entry, outfile, ensure_ascii=False)
        outfile.write("\n")
