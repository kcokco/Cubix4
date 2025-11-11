
from openai import OpenAI
import os
from dotenv import load_dotenv
from vectordb import VectorDB

# Load environment variables
load_dotenv()

SYSTEM_PROMPT="""
You are a helpful assistant that generates responses to user queries. Write your response based 
on the provided documents.
"""

USER_PROMPT="""
User query: {query}
Documents: {documents}
"""

def generate_response(query: str, documents: list[str]) -> str:
    """
    Generate a response using OpenAI API based on query and retrieved documents.
    
    Args:
        query: User's query string
        documents: List of relevant document texts
    
    Returns:
        Generated response string
    """
    # Initialize OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key must be provided as OPENAI_API_KEY environment variable")
    
    client = OpenAI(api_key=api_key)
    
    # Format documents for the prompt
    formatted_documents = "\n\n".join([f"Document {i+1}: {doc}" for i, doc in enumerate(documents)])
    
    # Create the user message
    user_message = USER_PROMPT.format(query=query, documents=formatted_documents)
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        return f"Error generating response: {str(e)}"

def full_response_pipeline(query: str, vector_db: VectorDB) -> str:
    """
    Complete RAG pipeline: retrieve relevant documents and generate response.
    
    Args:
        query: User's query string
        vector_db: VectorDB instance for document retrieval
    
    Returns:
        Generated response string
    """
    try:
        # Retrieve relevant documents
        search_results = vector_db.search(query, limit=3)
        
        # Extract document texts from search results
        documents = [result["text"] for result in search_results]
        
        # If no documents found, return appropriate message
        if not documents:
            return "I couldn't find any relevant documents to answer your query."
        
        # Generate response using retrieved documents
        response = generate_response(query, documents)
        
        return response
    
    except Exception as e:
        return f"Error in response pipeline: {str(e)}"

if __name__ == "__main__":
    vector_db = VectorDB()
    response = full_response_pipeline("Where is the default configuration file for qdrant?", vector_db)
    print(response)