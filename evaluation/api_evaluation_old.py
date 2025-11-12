# Az összes szükséges könyvtár importálása.
import json                         # JSON fájlok kezeléséhez
import os                           
from typing import Dict, List, Any  # Standard könyvtárak

import requests                     # HTTP requestekhez (API hívásokhoz)
from openai import OpenAI           # OpenAI API kliens (LLM Judge)
from dotenv import load_dotenv # Harmadik fél könyvtárai. 

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client for LLM Judge
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be set in .env file")

# Az OpenAI API kliens létrehozása az LLM Judge-hoz. Ez később hívni fogja a GPT-4-et az értékeléshez.    
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# API endpoint
API_URL = "http://localhost:3000/api/chat"

# LLM Judge prompts
# Az AI válasz pontosságát értékeli (0-3 skála)
ACCURACY_JUDGE_PROMPT = """
You are an expert evaluator. Your task is to evaluate whether a generated response is accurate and complete compared to the expected response.

Expected Response: {expected_response}
Generated Response: {generated_response}

Evaluate the accuracy on a scale of 0-3:
0 = Completely incorrect or hallucinated information
1 = Partially correct but missing key information or has errors
2 = Mostly correct with minor omissions or inaccuracies
3 = Fully accurate and complete

Provide your evaluation in this format:
REASONING: [Detailed explanation]
SCORE: [0-3]
"""

# Az AI válasz relevancia-ját értékeli (0-3 skála)
RELEVANCE_JUDGE_PROMPT = """
You are an expert evaluator. Your task is to evaluate whether a generated response is relevant to the user's query.

User Query: {query}
Generated Response: {generated_response}

Evaluate relevance on a scale of 0-3:
0 = Completely irrelevant
1 = Partially relevant but missing key information
2 = Mostly relevant with good information
3 = Highly relevant and well-addressed

Provide your evaluation in this format:
REASONING: [Detailed explanation]
SCORE: [0-3]
"""


def send_api_request(query: str) -> str:
   """
    Ez a függvény kezeli az API hívást: HTTP POST requestet küld
    a RAG chatbot API-nak, a kérdést JSON formátumba csomagolja,
    megvárja, majd visszaadja az AI válaszát.
      
    Args:
        query (str): A felhasználó kérdése (pl. "What can I make with chickpeas?")
    
    Returns:
        The AI's response text (A chatbot válasza).
    
    Raises:
        Exception: If API request fails
    """
    try:
        payload = {
            "messages": [
                {"role": "user", "content": query}
            ]
        }
        
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        
        # Parse the streaming response
        # The API returns a stream, we need to collect the full response
        ai_response = ""
        
        # For now, return a simplified version
        # In production, you'd handle the streaming properly
        return response.text
        
    except Exception as e:
        return f"Error calling API: {str(e)}"


def evaluate_accuracy(generated_response: str, expected_response: str) -> Dict[str, Any]:
    """
    Use LLM Judge to evaluate if the generated response is accurate.
    Mit csinál:
        1. Előkészíti az LLM Judge promptot (az elvárt vs. generált választ).
        2. Hívja az OpenAI API-t a GPT-4 modellel a relevanciát és pontosságot mérő prompt használatával.
        3. Parszolja a válaszból a SCORE értéket (0-3).
        4. Kivonja a REASONING-et (indoklást).
        5. Visszaadja a pontszámot és az indoklást.
    
    Args:
        generated_response: The response from the AI
        expected_response: The expected/ideal response
    
    Returns:
        Dictionary with score and reasoning
    """
    prompt = ACCURACY_JUDGE_PROMPT.format(
        expected_response=expected_response,
        generated_response=generated_response
    )
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse the response
        score = None
        reasoning = None
        
        lines = result.split('\n')
        for line in lines:
            if line.startswith("SCORE:"):
                try:
                    score = int(line.replace("SCORE:", "").strip())
                except ValueError:
                    score = 0
            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()
        
        if reasoning is None:
            reasoning = result
        
        if score is None:
            score = 0
        
        return {
            "score": score,
            "reasoning": reasoning,
            "raw_response": result
        }
    
    except Exception as e:
        return {
            "score": 0,
            "reasoning": f"Error in evaluation: {str(e)}",
            "raw_response": None
        }
        
def evaluate_relevance(generated_response: str, query: str) -> Dict[str, Any]:
    """
    Use LLM Judge to evaluate if the generated response is relevant to the query.
    
    Args:
        generated_response: The response from the AI
        query: The user's original query
    
    Returns:
        Dictionary with score and reasoning
    """
    
    prompt = RELEVANCE_JUDGE_PROMPT.format(
        query=query,
        generated_response=generated_response
    )
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse the response
        score = None
        reasoning = None
        
        lines = result.split('\n')
        for line in lines:
            if line.startswith("SCORE:"):
                try:
                    score = int(line.replace("SCORE:", "").strip())
                except ValueError:
                    score = 0
            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()
        
        if reasoning is None:
            reasoning = result
        
        if score is None:
            score = 0
        
        return {
            "score": score,
            "reasoning": reasoning,
            "raw_response": result
        }
        
    except Exception as e:
        return {
            "score": 0,
            "reasoning": f"Error in evaluation: {str(e)}",
            "raw_response": None
        }
        
        
def load_golden_dataset(file_path: str) -> Dict[str, Any]:
    """
    Load the golden dataset from JSON file.
    
    Args:
        file_path: Path to the golden dataset JSON file
    
    Returns:
        Loaded dataset dictionary
    """ 
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
        
        
def run_api_evaluation(golden_dataset_path: str = "golden_dataset.json") -> Dict[str, Any]:
    """
    Run the complete evaluation against the API.
    
    Args:
        golden_dataset_path: Path to the golden dataset JSON file
    
    Returns:
        Evaluation results with metrics
    """
    # Load golden dataset
    dataset = load_golden_dataset(golden_dataset_path)
    
    results = {
        "metadata": dataset["metadata"],
        "total_queries": 0,
        "accuracy_total": 0,
        "relevance_total": 0,
        "detailed_results": []
    }
    # Process each entry in the dataset
    for entry in dataset["entries"]:
        document_info = entry["document"]
        qa_pairs = entry["qa_pairs"]
        
        for qa_pair in qa_pairs:
            query = qa_pair["query"]
            expected_response = qa_pair["response"]
        
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print(f"{'='*60}")
            
            # Get response from API
            generated_response = send_api_request(query)
            print(f"\nGenerated Response:\n{generated_response[:500]}...\n")
            
            # Evaluate accuracy
            accuracy_eval = evaluate_accuracy(generated_response, expected_response)
            print(f"Accuracy Score: {accuracy_eval['score']}/3")
            print(f"Reasoning: {accuracy_eval['reasoning']}\n")
            
            # Evaluate relevance
            relevance_eval = evaluate_relevance(generated_response, query)
            print(f"Relevance Score: {relevance_eval['score']}/3")
            print(f"Reasoning: {relevance_eval['reasoning']}\n")
            
            # Store detailed results
            detailed_result = {
                "document_title": document_info["title"],
                "query": query,
                "expected_response": expected_response,
                "generated_response": generated_response[:500],  # Store shortened version
                "accuracy": accuracy_eval,
                "relevance": relevance_eval
            }
            
            results["detailed_results"].append(detailed_result)
            
            # Update totals
            results["total_queries"] += 1
            results["accuracy_total"] += accuracy_eval["score"]
            results["relevance_total"] += relevance_eval["score"]
    
    # Calculate final metrics
    if results["total_queries"] > 0:
        results["average_accuracy"] = results["accuracy_total"] / results["total_queries"]
        results["average_relevance"] = results["relevance_total"] / results["total_queries"]
    
    return results


def save_evaluation_results(results: Dict[str, Any], output_path: str = "baseline_results.json"):
    """
    Save evaluation results to a JSON file.
    
    Args:
        results: Evaluation results dictionary
        output_path: Path to save the results
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def print_evaluation_summary(results: Dict[str, Any]):
    """
    Print a summary of the evaluation results.

    Args:
        results: Evaluation results dictionary
    """
    print("\n" + "="*60)
    print("BASELINE EVALUATION RESULTS")
    print("="*60)
    print(f"Total Queries: {results['total_queries']}")
    print(f"Average Accuracy: {results.get('average_accuracy', 0):.2f}/3")
    print(f"Average Relevance: {results.get('average_relevance', 0):.2f}/3")
    print("="*60)
    
    # Print detailed results
    print("\nDetailed Results:")
    for i, result in enumerate(results["detailed_results"], 1):
        print(f"\n--- Query {i} ---")
        print(f"Title: {result['document_title']}")
        print(f"Query: {result['query']}")
        print(f"Accuracy: {result['accuracy']['score']}/3")
        print(f"Relevance: {result['relevance']['score']}/3")
        
if __name__ == "__main__":
    print("Starting API Evaluation...")
    print("Make sure:")
    print("1. Dev server is running (pnpm run dev)")
    print("2. PostgreSQL is running (docker-compose up -d)")
    print("3. .env file has correct API key\n")
    
    # Run evaluation
    results = run_api_evaluation("golden_dataset.json")
    
    # Create output directory if it doesn't exist
    os.makedirs("results", exist_ok=True)
    
    # Save results
    output_path = "results/baseline_evaluation_results.json"
    save_evaluation_results(results, output_path)
    
    # Print summary
    print_evaluation_summary(results)
    print(f"\nDetailed results saved to: {output_path}")