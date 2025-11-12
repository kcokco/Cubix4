import os
import json
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm
from vectordb import VectorDB

load_dotenv()

DEFAULT_QUERY_GENERATOR_PROMPT = """
You are helping to evaluate a RAG (Retrieval-Augmented Generation) system. 
Given a document, generate a realistic user query that someone might ask when looking for information contained in this document.

Requirements:
- The query should be natural and realistic (how a real user would ask)
- The query should be answerable by the provided document
- Keep queries concise (1-2 sentences maximum)
- Focus on the main topics or key information in the document
- Return only the query, no additional text

Document:
{document}

Query:"""

def simulate_user_query_for_document(document: str, query_generator_prompt: str = DEFAULT_QUERY_GENERATOR_PROMPT, openai_client: OpenAI = None) -> str:
    """
    Simulate a user query for a given document.
    It calls OpenAI API to get the user query.
    """
    if openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key must be provided either as parameter or OPENAI_API_KEY environment variable")
        openai_client = OpenAI(api_key=api_key)
    
    prompt = query_generator_prompt.format(document=document)
    
    response = openai_client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content.strip()

def simulate_user_query_for_all_documents(documents: List[Dict[str, Any]], query_generator: Optional[Callable] = None, query_generator_prompt: str = DEFAULT_QUERY_GENERATOR_PROMPT, openai_client: OpenAI = None) -> List[Tuple[Dict[str, Any], str]]:
    """
    Simulate a user query for all documents
    Returns list of tuples (document_dict, generated_query)
    """
    if query_generator is None:
        query_generator = simulate_user_query_for_document
    
    results = []
    for document in tqdm(documents, desc="Generating queries"):
        try:
            query = query_generator(document["text"], query_generator_prompt, openai_client)
            results.append((document, query))
        except Exception as e:
            print(f"Error generating query for document: {e}")
            continue
    
    return results

def evaluate_rag_level(vector_db: VectorDB, documents: Optional[List[Dict[str, Any]]] = None, query_generator: Optional[Callable] = None, query_generator_prompt: str = DEFAULT_QUERY_GENERATOR_PROMPT, top_k: int = 5, limit: Optional[int] = None, log_file: Optional[str] = None) -> Dict[str, float]:
    """
    It estimates the precision and recall of the RAG system. It generates the user query for each document and then checks if the retrieved documents contain the 
    document, that was used to generate the user query. Uses chunk_index from metadata for tracking.
    
    Args:
        limit: Optional limit on number of documents to process for evaluation
        log_file: Optional path to log file for debugging information
    
    Returns:
        Dict with precision, recall, and f1_score metrics
    """
    if documents is None:
        # Get all documents from vector database
        documents = vector_db.get_all_documents()
    
    # Apply limit if specified
    if limit is not None and limit > 0:
        documents = documents[:limit]
    
    if not documents:
        return {"precision": 0.0, "recall": 0.0, "f1_score": 0.0, "total_queries": 0}
    
    # Initialize logging
    log_data = []
    if log_file:
        log_data.append({
            "timestamp": datetime.now().isoformat(),
            "evaluation_start": True,
            "total_documents": len(documents),
            "top_k": top_k,
            "limit": limit
        })
    
    # Generate queries for all documents
    document_queries = simulate_user_query_for_all_documents(documents, query_generator, query_generator_prompt, vector_db.openai_client)
    
    if not document_queries:
        return {"precision": 0.0, "recall": 0.0, "f1_score": 0.0, "total_queries": 0}
    
    total_queries = len(document_queries)
    relevant_retrieved = 0  # Number of times the original document was retrieved
    total_retrieved = 0     # Total number of retrieved documents
    
    for query_idx, (original_document, query) in enumerate(tqdm(document_queries, desc="Evaluating queries")):
        try:
            # Search for documents using the generated query
            search_results = vector_db.search(query, limit=top_k)
            total_retrieved += 1
            
            # Get the original document's chunk_index from metadata
            original_chunk_index = original_document.get("metadata", {}).get("chunk_index")
            
            # Check if the original document is in the retrieved results using chunk_index
            found_match = False
            for result in search_results:
                result_chunk_index = result.get("metadata", {}).get("chunk_index")
                if result_chunk_index is not None and result_chunk_index == original_chunk_index:
                    relevant_retrieved += 1
                    found_match = True
                    break
            
            # Log detailed information for debugging
            if log_file:
                log_entry = {
                    "query_index": query_idx,
                    "timestamp": datetime.now().isoformat(),
                    "query": query,
                    "ground_truth": {
                        "chunk_index": original_chunk_index,
                        "text": original_document.get("text", "")[:200] + "..." if len(original_document.get("text", "")) > 200 else original_document.get("text", ""),
                        "metadata": original_document.get("metadata", {})
                    },
                    "retrieved_results": [
                        {
                            "chunk_index": result.get("metadata", {}).get("chunk_index"),
                            "text": result.get("text", "")[:200] + "..." if len(result.get("text", "")) > 200 else result.get("text", ""),
                            "metadata": result.get("metadata", {}),
                            "score": result.get("score", 0.0) if "score" in result else None
                        }
                        for result in search_results
                    ],
                    "match_found": found_match,
                    "num_retrieved": len(search_results)
                }
                log_data.append(log_entry)
                    
        except Exception as e:
            print(f"Error during search: {e}")
            if log_file:
                log_data.append({
                    "query_index": query_idx,
                    "timestamp": datetime.now().isoformat(),
                    "query": query,
                    "error": str(e)
                })
            continue
    
    # Calculate metrics
    precision = relevant_retrieved / total_queries if total_queries > 0 else 0.0
    recall = relevant_retrieved / total_queries if total_queries > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    # Write log file if specified
    if log_file:
        log_data.append({
            "timestamp": datetime.now().isoformat(),
            "evaluation_end": True,
            "final_metrics": {
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "total_queries": total_queries,
                "relevant_retrieved": relevant_retrieved,
                "total_retrieved": total_retrieved
            }
        })
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        print(f"Debug log written to: {log_file}")
    
    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "total_queries": total_queries,
        "relevant_retrieved": relevant_retrieved,
        "total_retrieved": total_retrieved
    }

if __name__ == "__main__":
    # Example usage
    try:
        # Initialize vector database
        vector_db = VectorDB()
        
        # Evaluate RAG system
        print("Starting RAG evaluation...")
        results = evaluate_rag_level(vector_db, top_k=3, limit=None, log_file="rag_evaluation_debug_full.json")
        
        print("\nRAG Evaluation Results:")
        print(f"Precision: {results['precision']:.3f}")
        print(f"Recall: {results['recall']:.3f}")
        print(f"F1 Score: {results['f1_score']:.3f}")
        print(f"Total queries: {results['total_queries']}")
        print(f"Relevant retrieved: {results['relevant_retrieved']}")
        print(f"Total retrieved: {results['total_retrieved']}")
        
    except Exception as e:
        print(f"Error during evaluation: {e}")