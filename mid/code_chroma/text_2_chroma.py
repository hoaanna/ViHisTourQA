from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
import time
import uuid
from transformers import AutoTokenizer
import json

# ===== Khởi tạo embedding model =====
embedding_function = HuggingFaceEmbeddings(
    model_name="dangvantuan/vietnamese-document-embedding",
    model_kwargs={"device": "cuda", "trust_remote_code": True},  # thêm trust_remote_code
    encode_kwargs={"normalize_embeddings": True}
)

# ===== Load tokenizer để tính số token =====
tokenizer = AutoTokenizer.from_pretrained("dangvantuan/vietnamese-document-embedding")

def token_len(text):
    return len(tokenizer.encode(text))

# ===== TextSplitter =====
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,          # hợp lý cho tài liệu lịch sử/du lịch
    chunk_overlap=150,
    length_function=token_len,
    separators=["\n\n", "\n", ". ", " ", ""]
)


# ===== Hàm chia nhỏ text =====
def split_text_to_subchunks(text, chunk_id, extra_meta=None):
    sub_chunks = splitter.split_text(text)
    return [
        {
            "id": f"{chunk_id}_{i}_{uuid.uuid4().hex[:8]}",  # thêm UUID ngắn cho chắc
            "text": sub_text,
            "type": "sub_chunk",
            "parent_chunk_id": chunk_id,
            **(extra_meta or {})
        }
        for i, sub_text in enumerate(sub_chunks)
    ]

# ===== Xử lý file lịch sử =====
def fetch_history_chunks(file_input):
    print("Đang lấy dữ liệu lịch sử...")
    with open(file_input, "r", encoding="utf-8") as f:
        data = json.load(f)
    sub_chunks = []
    for form in data:
        form_id = form.get("formId", "unknown")
        content = form.get("content", "").strip()
        if not content:
            continue
        meta = {
            "title": form.get("title", ""),
            "volumeId": form.get("volumeId", ""),
            "source": form.get("source", "")
        }
        chunks = split_text_to_subchunks(content, form_id, meta)
        sub_chunks.extend(chunks)
    print(f"Đã tách thành {len(sub_chunks)} sub_chunks từ dữ liệu lịch sử")
    return sub_chunks

# ===== Xử lý file du lịch =====
def fetch_destination_chunks(file_input):
    print("Đang lấy dữ liệu du lịch...")
    with open(file_input, "r", encoding="utf-8") as f:
        data = json.load(f)
    sub_chunks = []
    for place in data:
        place_id = place.get("id", "unknown")
        desc = place.get("description", "").strip()
        if not desc:
            continue
        meta = {
            "title": place.get("title", ""),
            "metadata": place.get("metadata", {})
        }
        chunks = split_text_to_subchunks(desc, f"dest_{place_id}", meta)
        sub_chunks.extend(chunks)
    print(f"Đã tách thành {len(sub_chunks)} sub_chunks từ dữ liệu du lịch")
    return sub_chunks


# ===== Clean Metadata =====
def clean_metadata(meta: dict):
    """Chuyển mọi list/dict/... thành str để tránh lỗi khi upsert vào Chroma."""
    clean = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            clean[k] = v
        else:
            clean[k] = str(v)
    return clean

# ===== Insert vào Chroma =====
def insert_into_chroma(db, records, db_name, batch_size=500, persist_every=2000):
    total = len(records)
    if total == 0:
        print(f"{db_name}: không có record nào để lưu.")
        return

    print(f"Bắt đầu lưu {total} records vào {db_name} ...")
    t0 = time.time()
    saved = 0

    for start_idx in range(0, total, batch_size):
        batch = records[start_idx:start_idx + batch_size]

        docs = [
            Document(
                page_content=rec["text"],
                metadata=clean_metadata({k: v for k, v in rec.items() if k != "text"})
            )
            for rec in batch
        ]
        ids = [str(rec["id"]) for rec in batch]

        db.add_documents(documents=docs, ids=ids)
        saved += len(batch)

        pct = int(saved * 100 / total)
        elapsed = time.time() - t0
        print(f"Đã lưu {saved}/{total} ({pct}%) | {elapsed:.1f}s", flush=True)

        if saved % persist_every == 0:
            db.persist()
            print("Persist tạm thời xuống disk.", flush=True)

    db.persist()
    elapsed_total = time.time() - t0
    print(f"Hoàn tất lưu {db_name} | Tổng thời gian: {elapsed_total:.1f}s")

    try:
        count_now = db._collection.count()
        print(f"{db_name} hiện có {count_now} documents.")
    except Exception:
        pass


# ===== Khởi tạo Chroma =====
CHROMA_PATH = "/kaggle/working/vector_db_5_9_1"

chunk_db = Chroma(
    persist_directory=CHROMA_PATH,
    collection_name="chunks_his_dest",
    embedding_function=embedding_function
)

# ===== Main =====
if __name__ == "__main__":
    history_chunks = fetch_history_chunks("/kaggle/input/data-his-dest/history_form.json")
    destination_chunks = fetch_destination_chunks("/kaggle/input/data-his-dest/destination.json")

    # Lưu vào DB
    insert_into_chroma(chunk_db, history_chunks, "chunks_history", batch_size=50, persist_every=2000)
    insert_into_chroma(chunk_db, destination_chunks, "chunks_destination", batch_size=50, persist_every=2000)

    print("Hoàn tất: dữ liệu đã được split + embedding + lưu vào ChromaDB")
