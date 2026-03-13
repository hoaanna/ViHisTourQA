import json


def apply_location_mapping(mapping_path, driver):
    with open(mapping_path, "r", encoding="utf-8") as f:
        mappings = json.load(f)

    with driver.session() as session:
        for entry in mappings:
            old = entry.get("old_name", "").strip()
            new = entry.get("new_name", "").strip()
            period = entry.get("period", "").strip()
            note = entry.get("note", "").strip()

            if not old or not period:
                continue

            # 1. MERGE Time node nếu đã có thì không tạo lại
            session.run("""
                MERGE (t:time {name: $period})
            """, period=period, note=note)

            # 2. MERGE Location cũ và gán Time
            session.run("""
                MERGE (loc:location {name: $old})
                SET loc.note = CASE WHEN $note <> "" THEN $note ELSE loc.note END
                WITH loc
                MATCH (t:time {name: $period})
                MERGE (loc)-[:belongs_to_time]->(t)
            """, old=old, period=period, note=note)

            # 3. Xử lý danh sách tỉnh mới (new_name có thể là "A + B + C")
            new_names = [n.strip() for n in new.split("+") if n.strip()]

            for new_n in new_names:
                session.run("""
                    MERGE (loc:location {name: $new_n})
                """, new_n=new_n)

            # 4. Tạo quan hệ
            if len(new_names) == 1 and old != new_names[0]:
                # SAME_AS nếu chỉ đổi tên 1-1
                session.run("""
                    MATCH (a:location {name: $old}), (b:location {name: $new})
                    MERGE (a)-[:same_as]->(b)
                """, old=old, new=new_names[0])
                print(f"[SAME_AS] {old}: {new_names[0]}")

            elif len(new_names) > 1:
                # SPLIT_INTO nếu bị tách ra
                for new_n in new_names:
                    session.run("""
                        MATCH (a:location {name: $old}), (b:location {name: $new})
                        MERGE (a)-[:split_into]->(b)
                    """, old=old, new=new_n)
                print(f"[SPLIT_INTO] {old}: {', '.join(new_names)}")

    print("Ánh xạ location KG hoàn tất.")
