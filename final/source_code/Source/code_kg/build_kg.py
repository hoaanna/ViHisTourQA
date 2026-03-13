# from dotenv import load_dotenv
import os
import json
from neo4j import GraphDatabase
import unicodedata
import re
import textwrap
from langchain_community.graphs import Neo4jGraph
# from langchain_openai import ChatOpenAI

# Warning control
import warnings
warnings.filterwarnings("ignore")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# === Khởi tạo LangChain Graph Interface ===
kg = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD
)




STATE_PATH = "/kaggle/working/progress_kg_v2.json"
SAVE_EVERY = 10

def normalize_to_snake_case(text):
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "d")
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')

# === Load tiến độ đã lưu nếu có ===
if os.path.exists(STATE_PATH):
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)
        processed_chunks = set(tuple(x) for x in state.get("processed_chunks", []))
        seen_entities = set(state.get("seen_entities", []))
        seen_relations = set(tuple(x) for x in state.get("seen_relations", []))
        seen_mentions = set(tuple(x) for x in state.get("seen_mentions", []))
else:
    processed_chunks = set()
    seen_entities = set()
    seen_relations = set()
    seen_mentions = set()

chunks_since_last_save = 0


# === Hàm xử lý và ghi vào Neo4j ===
def create_chunk_entity_relation(tx, chunk_id, chunk_index, chunk_text, triples):
    global processed_chunks, seen_entities, seen_relations, seen_mentions, chunks_since_last_save

    chunk_key = (chunk_id, chunk_index)

    if chunk_key in processed_chunks:
        print(f"Bỏ qua chunk đã xử lý: {chunk_key}")
        return

    node_id = f"{chunk_id}_{chunk_index}"
    tx.run("""
        MERGE (c:Chunk {id: $node_id})
        SET c.text = $chunk_text
    """, node_id=node_id, chunk_text=chunk_text)

    triple_count = 0

    for triple in triples:
        try:
            subj = triple.get("subject")
            obj = triple.get("object")
            rel_raw = triple.get("relation")
            subj_type_raw = triple.get("subject_type", "Entity")
            obj_type_raw = triple.get("object_type", "Entity")

            if not subj or not rel_raw or not obj:
                print(f"Bỏ qua triple thiếu thông tin: {triple}")
                continue
                
            subj_type = normalize_to_snake_case(subj_type_raw)
            obj_type = normalize_to_snake_case(obj_type_raw)
            rel = normalize_to_snake_case(rel_raw)
            
            # Tạo Entity với label theo type
            if subj not in seen_entities:
                tx.run(f"MERGE (s:{subj_type} {{name: $subj}})", subj=subj)
                seen_entities.add(subj)

            if obj not in seen_entities:
                tx.run(f"MERGE (o:{obj_type} {{name: $obj}})", obj=obj)
                seen_entities.add(obj)

            # Tạo quan hệ
            rel_key = (subj, rel, obj)
            if rel_key not in seen_relations:
                tx.run(f"""
                    MATCH (s:{subj_type} {{name: $subj}}), (o:{obj_type} {{name: $obj}})
                    MERGE (s)-[:{rel.replace(" ", "_")}]->(o)
                """, subj=subj, obj=obj)
                seen_relations.add(rel_key)

            # Mentions
            for entity, entity_type_raw in [(subj, subj_type_raw), (obj, obj_type_raw)]:
                entity_type = normalize_to_snake_case(entity_type_raw)
                mention_key = (entity, node_id)
                if mention_key not in seen_mentions:
                    tx.run(f"""
                        MATCH (c:Chunk {{id: $node_id}}), (e:`{entity_type}` {{name: $entity}})
                        MERGE (c)-[:MENTIONS]->(e)
                    """, node_id=node_id, entity=entity)
                    seen_mentions.add(mention_key)

            triple_count += 1

        except Exception as e:
            print(f"Lỗi xử lý triple: {triple} → {e}")
            continue

    processed_chunks.add(chunk_key)
    chunks_since_last_save += 1
    print(f"Đã xử lý chunk: {chunk_key} | {triple_count} triples")

    if chunks_since_last_save >= SAVE_EVERY:
        save_progress()
        chunks_since_last_save = 0


def save_progress():
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "processed_chunks": [list(x) for x in processed_chunks],
            "seen_entities": list(seen_entities),
            "seen_relations": [list(x) for x in seen_relations],
            "seen_mentions": [list(x) for x in seen_mentions]
        }, f, ensure_ascii=False, indent=2)
    print("Đã lưu tiến độ.")


def process_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Lỗi JSON ở dòng: {line[:50]}...\nChi tiết: {e}")
                continue

            chunk_id = item.get("formId") or item.get("id")
            chunk_text = item.get("text", "")
            chunk_index = item.get("chunk_index")
            triples = item.get("triples", [])

            if not chunk_id or not triples:
                continue

            with driver.session() as session:
                session.write_transaction(create_chunk_entity_relation, chunk_id, chunk_index, chunk_text, triples)
