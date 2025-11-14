# evaluation/multi_turn_evaluation.py

import json
import os
import re
from typing import Dict, List, Any
from openai import OpenAI
from dotenv import load_dotenv

# Környezeti változók és OpenAI kliens inicializálása
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Az OPENAI_API_KEY-t be kell állítani a .env fájlban")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# --- LLM-AS-A-JUDGE PROMPT A TELJES BESZÉLGETÉSHEZ ---

CONVERSATION_JUDGE_PROMPT = """
You are an expert evaluator assessing an AI cooking assistant based on a full conversation.
Your primary evaluation aspect is: **Accuracy and Completeness**.

**Evaluation Criteria:**
- **Accuracy:** Is the information provided by the assistant correct? (e.g., real recipe details).
- **Completeness:** Does the assistant provide all necessary information? When the user asks for missing details (like salt, water, oil quantity), does the assistant provide a correct and helpful answer, or does it evade the question/hallucinate?
- **Goal Achievement:** Did the user persona successfully achieve their goal by the end of the conversation?

**Scoring Scale (0-3):**
- **0 (Failure):** The assistant provided completely inaccurate information, failed to answer follow-up questions, or did not help the user achieve their goal at all.
- **1 (Poor):** The assistant provided partially correct information but had significant gaps. It struggled with follow-up questions about missing details, leading to an incomplete or frustrating experience.
- **2 (Good):** The assistant was mostly accurate and complete. It might have missed a minor detail initially but was able to provide it correctly when asked. The user's goal was achieved.
- **3 (Excellent):** The assistant was perfectly accurate and complete from the start, or it flawlessly handled all follow-up questions, providing precise details without any evasion. The user's goal was achieved efficiently and accurately.

---
**CONVERSATION TO EVALUATE:**

**Persona:** {persona_name}
**Goal:** {goal_name}

**Conversation History:**
{conversation_history}

---
**YOUR EVALUATION:**

Based on the criteria of **Accuracy and Completeness**, please provide your evaluation in the following format.

REASONING: [Provide a detailed step-by-step analysis of the conversation. Explain how the assistant performed on accuracy and completeness. Mention if the user's goal was achieved and how well the assistant handled follow-up questions for missing details.]
SCORE: [Assign a single score from 0-3]
"""

def load_conversations(file_path: str) -> List[Dict[str, Any]]:
    """Beolvassa a szimulált beszélgetéseket tartalmazó JSON fájlt."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Hiba: A(z) '{file_path}' fájl nem található.")
        return []
    except json.JSONDecodeError:
        print(f"Hiba: A(z) '{file_path}' fájl formátuma érvénytelen.")
        return []

def format_conversation_for_prompt(conversation_log: Dict[str, Any]) -> str:
    """A beszélgetési előzményeket egyetlen, olvasható stringgé formázza a prompt számára."""
    history_str = ""
    for turn in conversation_log["conversation_history"]:
        role = "User" if turn["role"] == "user" else "Assistant"
        text = turn["parts"][0]["text"]
        history_str += f"- **{role}:** {text}\n"
    return history_str

def evaluate_conversation(conversation_log: Dict[str, Any]) -> Dict[str, Any]:
    """Egy teljes beszélgetést értékel az LLM-as-a-Judge segítségével."""
    
    formatted_history = format_conversation_for_prompt(conversation_log)
    
    prompt = CONVERSATION_JUDGE_PROMPT.format(
        persona_name=conversation_log["persona"],
        goal_name=conversation_log["goal"],
        conversation_history=formatted_history
    )
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Robusztusabb feldolgozás a pontszám és az indoklás kinyerésére
        score = 0
        reasoning = "Could not parse evaluation."

        # Indoklás kinyerése
        reasoning_marker = "REASONING:"
        reasoning_start_index = result_text.find(reasoning_marker)
        if reasoning_start_index != -1:
            # Az indoklás a "REASONING:" után kezdődik
            reasoning_text_start = reasoning_start_index + len(reasoning_marker)
            # Az indoklás vége a "SCORE:" előtti rész
            score_marker_index = result_text.find("SCORE:")
            if score_marker_index > reasoning_start_index:
                reasoning = result_text[reasoning_text_start:score_marker_index].strip()
            else:
                reasoning = result_text[reasoning_text_start:].strip()
        else:
            # Fallback, ha a "REASONING:" marker nem található
            reasoning = result_text

        # Pontszám kinyerése reguláris kifejezéssel
        score_marker = "SCORE:"
        score_start_index = result_text.upper().find(score_marker)
        if score_start_index != -1:
            score_str = result_text[score_start_index + len(score_marker):]
            # Keressük az első, 0-3 közötti számot
            match = re.search(r'\b[0-3]\b', score_str)
            if match:
                try:
                    score = int(match.group(0))
                except (ValueError, IndexError):
                    score = 0 # Hiba esetén 0 pont
            else:
                score = 0 # Ha nem található 0-3 közötti szám
        else:
            score = 0 # Ha a "SCORE:" marker nem található
        
        return {"score": score, "reasoning": reasoning}

    except Exception as e:
        return {"score": 0, "reasoning": f"An error occurred during evaluation: {e}"}

if __name__ == "__main__":
    input_file = os.path.join("results", "simulation_conversations_prompt_v2_en.json")
    
    print(f"Kiértékelés indul a(z) '{input_file}' fájl alapján...")
    
    conversations = load_conversations(input_file)
    
    if not conversations:
        print("Nincsenek kiértékelhető beszélgetések. A program leáll.")
    else:
        all_results = []
        total_score = 0
        
        for conv_log in conversations:
            print(f"\n--- Értékelés alatt: '{conv_log['goal']}' ---")
            
            evaluation = evaluate_conversation(conv_log)
            
            print(f"Eredmény: {evaluation['score']}/3")
            print(f"Indoklás (részlet): {evaluation['reasoning'][:150]}...")
            
            result_entry = {
                "persona": conv_log["persona"],
                "goal": conv_log["goal"],
                "evaluation_score": evaluation["score"],
                "evaluation_reasoning": evaluation["reasoning"],
                "conversation_history": conv_log["conversation_history"]
            }
            all_results.append(result_entry)
            total_score += evaluation["score"]
            
        # Átlagpontszám kiszámítása
        average_score = total_score / len(conversations) if conversations else 0
        
        # Eredmények mentése
        output_file = os.path.join("results", "multi_turn_evaluation_results_prompt_v2_en.json")
        final_output = {
            "overall_average_score": average_score,
            "detailed_results": all_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
            
        print("\n" + "="*60)
        print("KIÉRTÉKELÉS ÖSSZEGZÉSE")
        print("="*60)
        print(f"Beszélgetések száma: {len(conversations)}")
        print(f"Átlagos pontszám: {average_score:.2f} / 3.0")
        print(f"\nA részletes kiértékelés elmentve ide: {output_file}")
