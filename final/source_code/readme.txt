cần phải có 2 API_KEY, os.environ["GOOGLE_API_KEY"] = API_KEY và f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
Xây dựng Neo4j trên Neo4jCloud lấy thông tin NEO4J_URI, NEO4J_USER, NEO4J_PASS để thiết lập kết nối:
graph = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USER,
    password=NEO4J_PASS
)
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))