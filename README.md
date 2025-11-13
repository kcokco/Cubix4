# Module 04 - Multi-Turn Evaluáció és Iteratív Fejlesztés

## Feladat Áttekintése

Ez a projekt a **RAG-alapú AI asszisztens** fejlesztésének és iteratív javításának bemutatásáról szól.A cél **egy konkrét aspektust azonosítani, mérni és javítani**.

**Tech Stack:**
- [Next.js](https://nextjs.org) 14 (App Router)
- [Vercel AI SDK](https://sdk.vercel.ai/docs)
- [OpenAI](https://openai.com)
- [Drizzle ORM](https://orm.drizzle.team)
- [Postgres](https://www.postgresql.org/) with [pgvector](https://github.com/pgvector/pgvector)
- Python evaluációs scriptek (02_code)

---

## 1. Kiindulási Pont

Ez a projekt az **előző házi (Cubix3) megoldásán alapul**, amely egy működőképes RAG chatbot volt **85 feltöltött recepttel**.

### Alapvető Funkcionalitás:
- **Dokumentum feltöltés**: Receptek vektorizálása és tárolása
- **Semantic keresés**: Vector similarity alapon (pgvector)
- **RAG Chat**: Az AI csak az adatbázisban lévő információt használja
- **Evaluáció**: LLM Judge alapú metrikák (02_code)

---

## 2. Tesztelési Fázis - Kezdeti Analízis

### Teszt Körülmények:
- **Receptek száma**: 85 feltöltött receptfájl
- **Kérdések nyelve**: Angol (az AI prompt angolul van)
- **Kiértékelés módszere**: Manual testing + Tool call output vizsgálata

### Teszt 1: Egyszerű Keresés 
**Kérdés:** "What can I make with chickpeas?"
**Válasz:** Homemade Hummus - Teljes recept
**Tool Output Scores:** 0.8959, 0.8958, 0.8522 (mind 0.85 felett)
**Megállapítás:** Valódi recept az adatbázisból
**AZONBAN - PROBLÉMA AZONOSÍTVA:**
- Az adatbázisban: "1 tsp baking soda", "1 tbsp salt", "6 cups water"
- Az AI válaszban: **HIÁNYZANAK** ezek az összetevők.
- **Az AI módosította a receptet** - hallucináció típusú hiba történt.

### Teszt 2: Komplex Szűrés
**Kérdés:** "Show me recipes that take less than 30 minutes to prepare"
**Válasz:** "No relevant information found"
**Tool Output:** Empty result (nincs szűrési lehetőség az időtartam alapján).
**Megállapítás:** A rendszer nem támogatja a szűrést metadata alapján.

### Teszt 3: Negatív Teszt 
**Kérdés:** "What can I make with quinoa?"
**Válasz:** Helyesen visszautasította - "No relevant information found"
**Megállapítás:** Helyesen működik, nem hallucinálja a quinoa recepteket

### Single-Turn Baseline Evaluation Results (Korábbi mérés)

Ez a mérés a rendszer kiinduló állapotát mutatja egykörös (single-turn) kérdések alapján, mielőtt áttértünk a többkörös szimulációra.

**Baseline Teljesítmény:**
- **Average Accuracy: 1.5/3** ❌ (Hiányos receptek - csak részleges információ)
- **Average Relevance: 1.75/3** ⚠️ (Általában releváns, de inkonzisztenciákkal)

**Azonosított Probléma:** Az AI csak részleges recepteket ad vissza, több ételt kihagyva.

**Részletes Bontás:**

| Kérdés 	| Accuracy  | Relevance | Probléma 												|
|-----------|-----------|-----------|-------------------------------------------------------|
| Chickpeas | 1/3 		| 3/3 		| Csak 1 recept helyett 3-ból 							|
| Potatoes  | 1/3 		| 0/3 		| Rossz tartalom és hiányzó összetevők 					|
| Thai      | 1/3 		| 3/3 		| Pad Thai csak, Thai Fried Rice hiányzik 				|
| Quinoa    | 3/3 		| 1/3 		| Helyes (nincs az adatbázisban), de kevés alternatíva 	|

---

## 3. Azonosított Probléma - Az Aspektus amit Javítunk

### Fő Probléma: "Pontosság és Teljesség"

**Definíció:** Az AI módosítja/kihagyja az adatbázisban lévő receptek összetevőit helyett 100%-ban azt követve.

**Tünetek:**
- Ingrediensek kihagyása (mint a Hummus esetében).
- Az AI saját tudásából "javítja" a recepteket.
- Nem szigorú az "ONLY use database information" instrukció követésében.

**Miért fontos?**
- Receptnél a **pontosság KRITIKUS** - ha hiányzik egy-egy összetevő, az étel rossz lesz.
- A RAG rendszer lényege, hogy **csak az adatbázist követi**, nem a saját tudást
- **Hallucináció megelőzése**

---

## 5. Iterációs Fejlesztés

(Még nem hajtott végre - Baseline után)

### Iteráció 1: System Prompt szigorítás
- "MUST include ALL ingredients EXACTLY as listed in database"
- Stricter RAG adherence

### Iteráció 2: Temperature/Sampling módosítás
- Lower temperature (0.5 → 0.3) = konzervativabb válaszok

### Iteráció 3: Prompt engineering
- Explicit format: "List ingredients in this exact order from database"

---

## Evaluation Framework

A projekt iteratív fejlesztéséhez egy **evaluation/** mappa tartozik, amely Python szkripteket, szimulált felhasználói perszónákat, és egy LLM-as-a-Judge alapú kiértékelő rendszert tartalmaz.

### Multi-Turn Evaluation Framework

A házi feladatnak megfelelően egy többkörös (multi-turn) kiértékelési rendszert építettünk ki, hogy az asszisztens teljesítményét valósághű, beszélgetés-szerű helyzetekben mérjük.

#### Metodológia
1.  **Perszóna-alapú Szimuláció (`evaluation/simulation.py`):**
    *   Létrehoztunk két szimulált felhasználói perszónát, akiknek konkrét céljaik vannak:
        *   **Anna, a Precíz Szakács:** Neki a receptek pontossága és teljessége a legfontosabb. Célja, hogy ellenőrizze, a chatbot nem hagy-e ki összetevőket, és rákérdez a hiányzó részletekre.
        *   **Bence, a Kezdő Felfedező:** Új recepteket szeretne felfedezni. Általános kérdéssel indít, majd a kapott válaszok alapján mélyebbre ás.
    *   A szkript ezekkel a perszónákkal játszik le 3-4 körös beszélgetéseket, amelyek során a perszóna viselkedését egy LLM vezérli, reagálva a chatbot válaszaira.
    *   A teljes beszélgetéseket a `evaluation/results/simulation_conversations.json` fájlba menti.

2.  **Többkörös Kiértékelés (`evaluation/multi_turn_evaluation.py`):**
    *   Ez a szkript beolvassa a szimulált beszélgetéseket.
    *   Egy LLM-as-a-Judge (GPT-4) segítségével, egy komplex prompt alapján kiértékeli a **teljes beszélgetést** a "Pontosság és Teljesség" szempontjából.
    *   A "bíró" 0-3 közötti pontszámot ad, figyelembe véve, hogy a chatbot helyesen válaszolt-e a kiegészítő kérdésekre és a felhasználó elérte-e a célját.
    *   Az eredményeket a `evaluation/results/multi_turn_evaluation_results.json` fájlba menti.

### Multi-Turn Baseline Evaluation Results

Ez a mérés a jelenlegi rendszer kiinduló állapotát mutatja a többkörös szimulációk alapján.

**Baseline Teljesítmény:**
- **Átlagos Pontszám: 3.0/3.0** ✅ (Kiváló)

**Megállapítás:**
A jelenlegi rendszer a többkörös, valósághűbb szimulációk során is **kiválóan** teljesített a "Pontosság és Teljesség" szempontjából. Az asszisztens nem csak pontos információkat adott, de a hiányzó részletekre vonatkozó kiegészítő kérdéseket is hibátlanul kezelte.

**Részletes Bontás:**

| Persona & Goal 	| Score | Indoklás (Összefoglaló) 												|
|-------------------|-------|-----------------------------------------------------------------------|
| Anna (Hummus) 	| 3/3 	| Kiválóan kezelte a só és víz mennyiségére vonatkozó kiegészítő kérdéseket. |
| Bence (Thai)  	| 3/3 	| Több, teljes és pontos receptet adott, zökkenőmentesen kezelve a párbeszédet. |
| Anna (Quinoa/Brokkoli)| 3/3 	| Helyesen jelezte a nem létező receptet, majd a kért új receptnél is pontosan válaszolt a kiegészítő kérdésre. |

### Iterációs Fejlesztés Terve

Bár a baseline eredmény kiváló, a házi feladat az iterációs folyamat dokumentálásáról szól. A következő lépés egy tervezett iteráció végrehajtása és annak hatásának mérése.

**Következő Iteráció:** **Temperature csökkentése (0.7 -> 0.3)**.
- **Hipotézis:** Bár a rendszer most is pontos, egy alacsonyabb temperature érték még determinisztikusabbá, "robotosabbá" teheti a válaszokat, ami potenciálisan csökkenti a kreativitást, de növeli a reprodukálhatóságot. Megvizsgáljuk, hogy ez a változtatás ront-e a felhasználói élményen vagy a pontszámon.

### Fájlok és Dokumentáció

- **evaluation/simulation.py**: Többkörös beszélgetések szimulációja perszónákkal.
- **evaluation/multi_turn_evaluation.py**: A szimulált beszélgetések kiértékelése LLM-as-a-Judge segítségével.
- **evaluation/results/**: A szimulációk és kiértékelések JSON kimeneti fájljai.
- **README.MD**: Teljes dokumentáció a metodológiáról és az eredményekről.

**Futtatás:**
1. `python evaluation/simulation.py`
2. `python evaluation/multi_turn_evaluation.py`

---

## 6. Fejlesztési Lehetőségek (Jövőbeli)

- [ ] Metadata szűrés (prep_time, vegetarian, cuisine, stb.)
- [ ] Batch evaluáció 20-30 random kérdéssel
- [ ] Hallucináció detektálás (comparing DB vs. output)
- [ ] User feedback loop (thumbs up/down)

---

## Irodalom

**Érdemes elolvasni az előző házira vonatkozóan (Cubix3-ban):**
- Hallucináció problémája és boundary value analysis
- Score tartomány analízis (0.75-0.85 "veszélyes zóna")
- System prompt fine-tuning az adatforrás korlátozásához