

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI
import uuid
import os
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables from .env file
load_dotenv()


class VectorDB:
    """
    Vector DB class, that implements the vector db interface by connecting to a qdrant server
    """
    def __init__(self, host: str = "localhost", port: int = 6333, collection_name: str = "documents",
                 openai_api_key: str = None):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name

        # Initialize OpenAI client
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key must be provided either as parameter or OPENAI_API_KEY environment variable")

        self.openai_client = OpenAI(api_key=api_key)
        self.embedding_model = "text-embedding-3-small"
        self.vector_size = 1536  # Default dimension for text-embedding-3-small

        self._create_collection_if_not_exists()

    def _create_collection_if_not_exists(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
                )
        except Exception as e:
            print(f"Error creating collection: {e}")

    def add_document(self, document: str, metadata: Dict[str, Any] = None):
        """Add a document to the vector database"""
        if metadata is None:
            metadata = {}

        # Get embedding from OpenAI
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=document
        )
        vector = response.data[0].embedding

        point_id = str(uuid.uuid4())

        point = PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "text": document,
                **metadata
            }
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )

        return point_id

    def search(self, query: str, limit: int = 5):
        """Search for similar documents"""
        # Get embedding from OpenAI
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=query
        )
        query_vector = response.data[0].embedding

        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit
        )

        results = []
        for hit in search_result:
            results.append({
                "id": hit.id,
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
            })

        return results

    def get_all_documents(self):
        """
        If the vector db is not too large, we can get all the documents from the vector db
        """
        try:
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000
            )

            documents = []
            for point in points:
                documents.append({
                    "id": point.id,
                    "text": point.payload.get("text", ""),
                    "metadata": {k: v for k, v in point.payload.items() if k != "text"}
                })

            return documents
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return []

if __name__ == "__main__":
    vector_db = VectorDB()
    documents = vector_db.get_all_documents()
    for document in documents[:10]:
        print(document["text"])
        print("METADATA:")
        print(document["metadata"])
        print("-"*100)