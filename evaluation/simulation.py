# simulation.py

import json
import os
from typing import Dict, List, Any
from openai import OpenAI
import requests
from dotenv import load_dotenv

# Környezeti változók betöltése a .env fájlból
load_dotenv()

# OpenAI kliens inicializálása a perszóna szimulációjához
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Az OPENAI_API_KEY-t be kell állítani a .env fájlban")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# A te chatbotod API végpontja
API_URL = "http://localhost:3000/api/chat"

# --- PERSONA ÉS GOAL DEFINÍCIÓK ---

class Persona:
    """Egy szimulált felhasználói perszónát reprezentál."""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

class Goal:
    """Egy célt reprezentál, amit a perszóna el akar érni."""
    def __init__(self, name: str, initial_query: str, validation_prompt: str):
        self.name = name
        self.initial_query = initial_query
        self.validation_prompt = validation_prompt

# A README alapján definiált perszónák és célok
personas = {
    "anna": Persona(
        name="Anna, the Precise Chef",
        description="""You are Anna, a precise chef. For you, accuracy is paramount.
        If you ask for a recipe, you expect to receive all ingredients and steps exactly as they are.
        If you notice something is missing (e.g., salt, water, oil), or a quantity seems suspicious, you will ask politely but firmly."""
    ),
    "bence": Persona(
        name="Bence, the Novice Explorer",
        description="""You are Bence, a beginner who loves to discover new recipes.
        You first ask a general question about an ingredient.
        After the chatbot suggests several options, you choose one and ask for the full recipe."""
    )
}

goals = {
    "chickpea_accuracy": Goal(
        name="Checking Hummus Recipe Accuracy",
        initial_query="What can I make with chickpeas?",
        validation_prompt="The chatbot has responded. Your goal is to check the accuracy of the Hummus recipe. Ask about a missing ingredient, for example, salt or water, to ensure its completeness."
    ),
    "thai_discovery": Goal(
        name="Discovering a Thai Recipe",
        initial_query="Do you have any Thai recipes?",
        validation_prompt="The chatbot has recommended one or more Thai recipes. Choose one (e.g., Pad Thai) and ask for its full, detailed recipe."
    ),
    "negative_test": Goal(
        name="Testing a Non-existent Ingredient",
        initial_query="What can I make with quinoa?",
        validation_prompt="The chatbot should correctly state that it does not have such a recipe. Give positive confirmation if it handled the situation well, or ask about another ingredient if it hallucinated."
    )
}

# --- API ÉS SZIMULÁCIÓS FÜGGVÉNYEK ---

def send_api_request(messages: List[Dict[str, Any]]) -> str:
    """Elküldi a beszélgetési előzményeket a chatbot API-nak és visszaadja a választ."""
    try:
        payload = {"messages": messages}
        response = requests.post(API_URL, json=payload, timeout=45, stream=True)
        response.raise_for_status()

        ai_response = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data:'):
                    try:
                        json_str = line[len('data:'):].strip()
                        chunk = json.loads(json_str)
                        if chunk.get('type') == 'text-delta' and 'delta' in chunk:
                            ai_response += chunk['delta']
                    except json.JSONDecodeError:
                        continue
        return ai_response if ai_response else "API did not return a valid response."
    except requests.exceptions.RequestException as e:
        return f"API request failed: {e}"

def get_next_user_turn(persona: Persona, goal: Goal, history: List[Dict[str, Any]]) -> str:
    """Az LLM segítségével generálja a következő felhasználói kérdést a perszóna és a cél alapján."""
    
    system_prompt = f"{persona.description}\n\nA célod: {goal.validation_prompt}"
    
    # Csak az utolsó pár üzenetet küldjük el, hogy ne lépjük túl a kontextus ablakot
    conversation_context = "\n".join([f"{msg['role']}: {msg['parts'][0]['text']}" for msg in history[-4:]])

    prompt = f"""The current conversation is:
{conversation_context}

What is your next question/response to the chatbot based on your persona and goal described above? **Respond ONLY in English.** Return only the response, without any extra text."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Persona generation failed: {e}"

def run_simulation(persona: Persona, goal: Goal, max_turns: int = 3) -> Dict[str, Any]:
    """Lefuttat egy teljes beszélgetési szimulációt."""
    print(f"\n--- Kezdődik a szimuláció: '{goal.name}' | Perszóna: {persona.name} ---")
    
    history = []
    
    # 1. kör: Kezdő kérdés
    user_message = goal.initial_query
    print(f"User (Turn 1): {user_message}")
    history.append({"role": "user", "parts": [{"type": "text", "text": user_message}]})
    
    ai_response = send_api_request(history)
    print(f"AI (Turn 1): {ai_response[:300]}...")
    history.append({"role": "assistant", "parts": [{"type": "text", "text": ai_response}]})

    # További körök
    for turn in range(2, max_turns + 1):
        # Persona LLM generálja a következő user üzenetet
        user_message = get_next_user_turn(persona, goal, history)
        if not user_message or "failed" in user_message:
            print("A perszóna generálása nem sikerült, a szimuláció leáll.")
            break
            
        print(f"User (Turn {turn}): {user_message}")
        history.append({"role": "user", "parts": [{"type": "text", "text": user_message}]})
        
        # API hívás a chatbottal
        ai_response = send_api_request(history)
        print(f"AI (Turn {turn}): {ai_response[:300]}...")
        history.append({"role": "assistant", "parts": [{"type": "text", "text": ai_response}]})

    print("--- Szimuláció vége ---")
    
    return {
        "persona": persona.name,
        "goal": goal.name,
        "conversation_history": history
    }

# --- FŐ FUTTATÁSI BLOKK ---

if __name__ == "__main__":
    print("Többkörös beszélgetések szimulációja indul...")
    print("Győződj meg róla, hogy a Next.js fejlesztői szerver fut (`pnpm run dev`)!")

    # Szimulációk futtatása a definiált esetekre
    simulation_results = []
    simulation_results.append(run_simulation(personas["anna"], goals["chickpea_accuracy"]))
    simulation_results.append(run_simulation(personas["bence"], goals["thai_discovery"]))
    simulation_results.append(run_simulation(personas["anna"], goals["negative_test"]))
    
    # Eredmények mentése
    output_dir = "results"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "simulation_conversations_prompt_v2_en.json")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(simulation_results, f, indent=2, ensure_ascii=False)
        
    print(f"\nA szimulációs beszélgetések elmentve ide: {output_path}")
    print("Következő lépés: Futtass egy kiértékelő szkriptet ezen a fájlon, hogy pontozd a beszélgetéseket.")