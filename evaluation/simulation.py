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
        name="Anna, a Precíz Szakács",
        description="""Te Anna vagy, egy precíz szakács. Számodra a legfontosabb a pontosság. 
        Ha egy receptet kérsz, elvárod, hogy minden összetevőt és lépést pontosan megkapj. 
        Ha észreveszed, hogy valami hiányzik (pl. só, víz, olaj), vagy egy mennyiség gyanús, udvariasan, de határozottan rákérdezel."""
    ),
    "bence": Persona(
        name="Bence, a Kezdő Felfedező",
        description="""Te Bence vagy, egy kezdő, aki szeret új recepteket felfedezni. 
        Először egy általános kérdést teszel fel egy alapanyagról. 
        Miután a chatbot ajánlott több lehetőséget, kiválasztasz egyet, és annak kéred el a teljes receptjét."""
    )
}

goals = {
    "chickpea_accuracy": Goal(
        name="Hummus recept pontosságának ellenőrzése",
        initial_query="What can I make with chickpeas?",
        validation_prompt="A chatbot válaszolt. A te célod, hogy a Hummus receptjének pontosságát ellenőrizd. Kérdezz rá egy hiányzó alapanyagra, például a sóra vagy a vízre, hogy megbizonyosodj a teljességéről."
    ),
    "thai_discovery": Goal(
        name="Thai recept felfedezése",
        initial_query="Do you have any Thai recipes?",
        validation_prompt="A chatbot ajánlott egy vagy több thai receptet. Válassz egyet (pl. Pad Thai) és kérd el annak a teljes, részletes receptjét."
    ),
    "negative_test": Goal(
        name="Nem létező alapanyag tesztelése",
        initial_query="What can I make with quinoa?",
        validation_prompt="A chatbotnak helyesen kellene válaszolnia, hogy nincs ilyen receptje. Adj egy pozitív megerősítést, ha jól kezelte a helyzetet, vagy kérdezz rá egy másik alapanyagra, ha hallucinált."
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

    prompt = f"""A jelenlegi beszélgetés:
{conversation_context}

Mi a következő kérdésed/válaszod a chatbotnak a fent leírt személyiséged és célod alapján? Csak a választ add vissza, mindenféle körítés nélkül."""

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
    output_path = os.path.join(output_dir, "simulation_conversations.json")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(simulation_results, f, indent=2, ensure_ascii=False)
        
    print(f"\nA szimulációs beszélgetések elmentve ide: {output_path}")
    print("Következő lépés: Futtass egy kiértékelő szkriptet ezen a fájlon, hogy pontozd a beszélgetéseket.")