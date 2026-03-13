from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from transformers import AutoTokenizer


embedding_function = HuggingFaceEmbeddings(
    model_name="dangvantuan/vietnamese-embedding",
    model_kwargs={"device": "cpu", "trust_remote_code": True},  # thêm trust_remote_code
    encode_kwargs={"normalize_embeddings": True}
)

CHROMA_PATH = "/kaggle/working/test_schema"

schema_label_db = Chroma(
    persist_directory=CHROMA_PATH,
    collection_name="schema_label",
    embedding_function=embedding_function
)

schema_rel_db = Chroma(
    persist_directory=CHROMA_PATH,
    collection_name="schema_rel",
    embedding_function=embedding_function
)

tokenizer = AutoTokenizer.from_pretrained("dangvantuan/vietnamese-embedding")




import json
with open("/kaggle/input/schema-kg/label_enriched_detailed.json", "r", encoding="utf-8") as f:
    labels = json.load(f)

with open("/kaggle/input/schema-kg/relationshipType_enriched_detailed.json", "r", encoding="utf-8") as f:
    relationships = json.load(f)
    
schema_label_entries = []
schema_rel_entries = []

for l in labels:
    schema_label_entries.append({"id": f"label_{l['label']}", "text": l["text"]})

for r in relationships:
    schema_rel_entries.append({
        "id": f"rel_{r['relationshipType']}",
        "text": r["text"]
    })
    
schema_label_db.add_texts(
    texts=[e["text"] for e in schema_label_entries],
    ids=[e["id"] for e in schema_label_entries]
)
print(f"Đã nạp {len(schema_label_entries)} schema label entries vào vectorDB.")

schema_rel_db.add_texts(
    texts=[e["text"] for e in schema_rel_entries],
    ids=[e["id"] for e in schema_rel_entries]
)

print(f"Đã nạp {len(schema_rel_entries)} schema relationship entries vào vectorDB.")
