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


## 4. Baseline Mérés Terve

A Python evaluációs scriptek (02_code) segítségével:

1. **LLM Judge alapú értékelés**: 0-3 skálán (0=rossz, 3=tökéletes)
2. **Metrikai pontosság**: Hány % az olyan receptek száma, ahol az összetevők 100%-ban azonosak?
3. **Teljesség**: Hány % az olyan receptek, ahol nem hiányzik vagy módosított az információ?


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

## 6. Fejlesztési Lehetőségek (Jövőbeli)

- [ ] Metadata szűrés (prep_time, vegetarian, cuisine, stb.)
- [ ] Batch evaluáció 20-30 random kérdéssel
- [ ] Hallucináció detektálás (comparing DB vs. output)
- [ ] User feedback loop (thumbs up/down)



## Irodalom

**Érdemes elolvasni az előző házira vonatkozóan (Cubix3-ban):**
- Hallucináció problémája és boundary value analysis
- Score tartomány analízis (0.75-0.85 "veszélyes zóna")
- System prompt fine-tuning az adatforrás korlátozásához