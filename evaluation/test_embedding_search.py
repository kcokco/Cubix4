import psycopg2
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment from parent directory
load_dotenv("../ai-sdk-rag-starter/.env")

# Get OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get database connection
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# Test query
query = "What can I make with chickpeas?"

print(f"Query: {query}")
print("=" * 60)

# Generate embedding for the query
response = client.embeddings.create(
    model="text-embedding-ada-002",
    input=query
)
query_embedding = response.data[0].embedding

# Search in database with different thresholds
thresholds = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70]

for threshold in thresholds:
    print(f"\nThreshold: {threshold}")
    print("-" * 60)

    # Use pgvector's cosine distance operator
    cur.execute("""
        SELECT
            content,
            1 - (embedding <=> %s::vector) as similarity
        FROM embeddings
        WHERE 1 - (embedding <=> %s::vector) > %s
        ORDER BY similarity DESC
        LIMIT 3
    """, (query_embedding, query_embedding, threshold))

    results = cur.fetchall()

    if results:
        print(f"Found {len(results)} results:")
        for i, (content, similarity) in enumerate(results, 1):
            print(f"\n  {i}. Similarity: {similarity:.4f}")
            print(f"     Content: {content[:100]}...")
    else:
        print("  No results found")

cur.close()
conn.close()
