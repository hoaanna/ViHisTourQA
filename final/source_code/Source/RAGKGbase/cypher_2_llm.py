from neo4j.graph import Node, Relationship

def kg_to_json(results):
    """
    Chuyển kết quả session.run() từ Neo4j thành JSON list (triples).
    - Tự động duyệt các field trong record.
    - Node -> {label, properties}
    - Relationship -> {type, properties}
    """
    json_results = []

    for record in results:
        triple = {}
        for key, value in record.items():
            if isinstance(value, Node):
                triple[key] = {
                    "labels": list(value.labels),
                    "properties": dict(value)
                }
            elif isinstance(value, Relationship):
                triple[key] = {
                    "type": value.type,
                    "properties": dict(value)
                }
            else:
                triple[key] = value  # nếu chỉ là giá trị primitive (str, int, ...)

        json_results.append(triple)

    return json_results

json_results = kg_to_json(results)


def kg_to_natural(json_results):
    """
    Chuyển JSON từ Neo4j (node + relationship) thành danh sách câu tự nhiên tiếng Việt.
    - Nếu có triple chuẩn (source, relationship, target) -> sinh câu trực tiếp.
    - Nếu là kết quả tổng quát (node/rel bất kỳ) -> cố gắng ghép lại.
    """
    sentences = set()

    for triple in json_results:
        # Trường hợp chuẩn source-relationship-target
        if "source" in triple and "relationship" in triple and "target" in triple:
            src = triple["source"]
            rel = triple["relationship"]
            tgt = triple["target"]

            rel_text = rel.replace("_", " ")
            sentence = f"\"{src['name']}\" {rel_text} \"{tgt['name']}\"."
            sentences.add(sentence)
            continue

        # Trường hợp tổng quát hơn (từ kg_to_json)
        nodes = {k: v for k, v in triple.items() if "labels" in v}
        rels = {k: v for k, v in triple.items() if "type" in v}

        for r_key, r_val in rels.items():
            rel_text = r_val["type"].replace("_", " ")
            rel_props = r_val.get("properties", {})

            # Ghép 2 node đầu tiên với quan hệ
            node_keys = list(nodes.keys())
            if len(node_keys) >= 2:
                src = nodes[node_keys[0]]
                tgt = nodes[node_keys[1]]
                src_name = src["properties"].get("name", "Unknown")
                tgt_name = tgt["properties"].get("name", "Unknown")

                props_text = ""
                if rel_props:
                    props_text = " (" + ", ".join(f"{k}={v}" for k, v in rel_props.items()) + ")"

                sentence = f"\"{src_name}\" {rel_text} \"{tgt_name}\"{props_text}."
                sentences.add(sentence)

    return sentences


print(kg_to_natural(json_results))