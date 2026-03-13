from code_kg import prompt_kg

import requests
import re
from neo4j import GraphDatabase

API_KEY = ""
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


SCHEMA_DESCRIPTION = prompt_kg.SCHEMA_DESCRIPTION

def build_prompt(question):
    return f"""{SCHEMA_DESCRIPTION}

Câu hỏi: "{question}"
→ Hãy viết truy vấn Cypher phù hợp để tìm thông tin trong KG. Chỉ trả về truy vấn Cypher duy nhất.
"""

def parse_queries_to_list(queries_str: str):
    return [{"query": q.strip()} for q in queries_str.strip().splitlines() if q.strip()]

def generate_with_gemini(prompt):
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return parse_queries_to_list(text)


def fix_cypher_query(query: str) -> str:
    quote_count = query.count('"')
    if quote_count % 2 != 0:
        query += '"'

    if re.search(r"\bWITH\s+\w+\s*$", query) or re.search(r"\bMATCH\s+\(.*\)\s*WHERE\s+.*$", query):
        query += " RETURN *"

    parts = query.split("RETURN")
    if len(parts) > 2:
        query = "RETURN".join(parts[:2])

    return query

def run_cypher(queries, driver):
    results = []

    with driver.session() as session:
        for query in queries:
            text = fix_cypher_query(query["query"])
            print("\n\nText:", text, "\n",type(text))
            print(f"Đang chạy truy vấn:\n{text}\n")
            try:
                result = session.run(text)
                for record in result:
                    results.append(dict(record))
            except Exception as e:
                print("[LỖI] Truy vấn lỗi:")
                print(query["query"])
                print(e)

    return results



question = "Bạn biết gì về Lê Lợi"
prompt = build_prompt(question)
queries = generate_with_gemini(prompt)
# print(queries)
# print("-------------------------")

# print(parse_queries_to_list(queries))
raw_queries = parse_queries_to_list(queries)
print("-------------------------")
# print(raw_queries)
run_cypher(raw_queries, driver)