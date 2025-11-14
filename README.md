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
- **Kérdések nyelve**: Angol (a system prompt angolul van)
- **Kiértékelés módszere**: Manual testing + a tool hívások eredményének vizsgálata

### Teszt 1: Egyszerű Keresés 
**Kérdés:** "What can I make with chickpeas?"
**Válasz:** Homemade Hummus - Teljes recept
**Tool Output Scores:** 0.8959, 0.8958, 0.8522 (mind 0.85 felett)
**Megállapítás:** Valódi recept az adatbázisból
**AZONBAN - PROBLÉMA AZONOSÍTVA:**
- Az adatbázisban: "1 tsp baking soda", "1 tbsp salt", "6 cups water"
- Az AI válaszában: **HIÁNYZANAK** ezek az összetevők.
- **Az AI módosította a receptet** - hallucináció típusú hiba történt.

### Teszt 2: Komplex Szűrés
**Kérdés:** "Show me recipes that take less than 30 minutes to prepare"
**Válasz:** "No relevant information found"
**Tool Output:** Empty result (nincs szűrési lehetőség az időtartam alapján).
**Megállapítás:** A rendszer nem támogatja az ilyen fajta szűréseket jelenleg.

### Teszt 3: Negatív Teszt 
**Kérdés:** "What can I make with quinoa?"
**Válasz:** Helyesen visszautasította, közölte, hogy nincs információja erről. - "No relevant information found"
**Megállapítás:** Helyesen működik, nem hallucinálja a quinoa recepteket

### Single-Turn Baseline Evaluation Results

Ez a mérés a rendszer kiinduló állapotát mutatja egykörös (single-turn) kérdések alapján.

**Baseline Teljesítmény:**
- **Average Accuracy: 1.5/3** ❌ (Hiányos receptek - csak részleges információ)
- **Average Relevance: 1.75/3** ⚠️ (Általában releváns, de inkonzisztenciákkal)

**Azonosított Probléma:** Az AI csak részleges recepteket ad vissza, ha lenne is több találat, azokat kihagyja.

**Részletes Bontás:**

| Kérdés 	| Accuracy  | Relevance | Probléma 												|
|-----------|-----------|-----------|-------------------------------------------------------|
| Chickpeas | 1/3 		| 3/3 		| Csak 1 recept helyett 3-ból 							|
| Potatoes  | 1/3 		| 0/3 		| Rossz tartalom és hiányzó összetevők 					|
| Thai      | 1/3 		| 3/3 		| Pad Thai-t megtalálja, Thai Fried Rice hiányzik		|
| Quinoa    | 3/3 		| 1/3 		| Helyes, nincs az adatbázisban							|

---

## 3. Azonosított Probléma - A választott aspektus a fentiek alapján a pontosság, teljesség 

### Fő Probléma: "Pontosság és Teljesség"

**Definíció:** Az AI módosítja vagy ki is hagyja az adatbázisban lévő receptek összetevőit, ahelyett, hogy azt 100%-ban azt követné. Ez kritikus probléma lehet bizonyos típusú, feladatú rendszereknél. A főzés is ilyen.

**Tünetek:**
- Összetevők kihagyása, mint a Hummus esetében.
- Az AI a saját tudásából javítja, kiegészíti a recepteket.
- Nem szigorú az "ONLY use database information" instrukció követésében.

**Miért fontos/kritikus ez?**
- Egy receptnél a **pontosság KRITIKUS** - ha hiányzik egy-egy összetevő, az étel rossz lesz.
- A RAG rendszer lényege, hogy **csak az adatbázist követi**, nem a saját tudást.
- **Hallucináció megelőzése**

---

## 5. Iteratív Fejlesztés

A feladat elvégzése közben nem csak az AI hibázott. Az ember is. A chatbot nyelve angol, de én elfelejtettem azt, hogy ez az alkalmazás nem ért magyarul és az iterációk összerakásánál magyarnyelvű szöveget küldtem be.
Amikor észrvettem, akkor úgy gondoltam jó teszt lesz ebből is, megnézem milyen értékeket kapok vissza. Ennek eredményét írtam le itt.
Utána megcsináltam a teszteket újra, módosítottam a bemeneti szöveget angolra. Annak eredményét is leírtam lejjebb.

### Iteráció 1 (Hibás): Temperature Csökkentése (0.7 -> 0.3) - Vegyes nyelvű kommunikáció

**Hipotézis:** A `temperature` csökkentése determinisztikusabbá teszi a válaszokat, javítva a pontosságot.
**Akció:** `temperature` beállítása `0.3`-ra a `route.ts`-ben.
**Eredmények:**
- **Átlagos Pontszám: 2.0/3.0** ❌ (Visszaesés a 3.0-s baseline-ról)
- **Kritikus hiba:** A chatbot egy kiegészítő kérdésre nem adott választ (`API did not return a valid response.`).
- **Hallucináció:** A chatbot egy "bulgur saláta" receptből kihagyta magát a bulgurt.
**Konklúzió:** A hipotézis megbukott. A `temperature` csökkentése rontotta a pontosságot, és új hibatípusokat hozott elő. A nyelvi eltérés (magyar follow-up kérdések) valószínűleg hozzájárult a problémákhoz.

---

### Iteráció 2 (Hibás): System Prompt Szigorítása - Vegyes nyelvű kommunikáció

**Hipotézis:** Szigorúbb system prompt javítja a chatbot ragaszkodását a forrásadatokhoz.
**Akció:** Szigorúbb szabályok hozzáadása a system prompt-hoz a `route.ts`-ben.
**Eredmények:**
- **Átlagos Pontszám: 1.33/3.0** ❌ (Jelentős visszaesés a 3.0-s baseline-ról)
- **Kritikus hiba:** A chatbot azt állította, nincs információja olyan alapvető hozzávalókról, mint a paradicsom és a burgonya.
**Konklúzió:** A szigorítás negatív hatással volt. A túlságosan merev szabályok gátolták a modellt a felhasználói szándék rugalmas értelmezésében és a releváns információk hatékony visszakeresésében. A nyelvi eltérés itt is valószínűleg súlyosbította a helyzetet.

---

### Iteráció 3 (Javított): Temperature Csökkentése (0.7 -> 0.3) - Angol nyelvű kommunikáció

**Hipotézis:** A `temperature` csökkentése determinisztikusabbá teszi a válaszokat, javítva a pontosságot, feltételezve, hogy a kommunikáció végig angolul zajlik.
**Akció:** `temperature` beállítása `0.3`-ra a `route.ts`-ben, és a `simulation.py` módosítása angol nyelvű perszóna kommunikációra.
**Eredmények:**
- **Átlagos Pontszám: 2.33/3.0** ⚠️ (Javulás a vegyes nyelvű 2.0-ról, de még mindig elmarad a baseline-tól)
- **Javulás:** A kritikus hibák (API hiba, alapvető hozzávalók meg nem találása) megszűntek.
- **Probléma:** A modell kevésbé rugalmasan értelmezte a felhasználói szándékot (pl. csicseriborsó salátát ajánlott hummusz helyett), és apróbb kihagyások (pl. fokhagyma lépés) továbbra is előfordultak.
**Konklúzió:** A nyelvi eltérés volt a kritikus hibák fő oka. A `temperature: 0.3` beállítás azonban még angol nyelvű kommunikációval sem érte el a célját, mert a modell kevésbé rugalmas és hajlamosabb apróbb hibákra.

---

### Iteráció 4 (Javított): System Prompt Szigorítása - Angol nyelvű kommunikáció

**Hipotézis:** A szigorúbb system prompt javítja a chatbot ragaszkodását a forrásadatokhoz, feltételezve, hogy a kommunikáció végig angolul zajlik.
**Akció:** A `temperature` visszaállítása alapértelmezettre, és a szigorúbb system prompt alkalmazása a `route.ts`-ben. A `simulation.py` angol nyelvű perszóna kommunikációra van beállítva.
**Eredmények:**
- **Átlagos Pontszám: 2.67/3.0** ⚠️ (Javulás az előző javított iterációhoz (2.33) képest, de még mindig elmarad a baseline-tól)
- **Javulás:** A Hummus és Quinoa/Lencse esetekben tökéletes 3 pontot ért el a chatbot.
- **Probléma:** A Thai recept beszélgetésben kritikus visszaesés történt: a chatbot nem tudott részleteket adni egy általa korábban felsorolt receptről.
**Konklúzió:** A szigorúbb system prompt angol nyelvű kommunikációval is vegyes eredményeket hozott. Bár bizonyos esetekben javított, más esetekben új, kritikus hibákat vezetett be. Ez is azt mutatja, hogy az eredeti, kiegyensúlyozott system prompt volt a leghatékonyabb.

---

### Az Iteratív Fejlesztés Összegzése és Tanulságai

Az iteratív fejlesztési folyamat során a következő fontos tanulságokat vontuk le:

1.  **Nyelvi Eltérés Kritikus Hatása:** A legjelentősebb problémákat a szimulált felhasználók és a chatbot közötti nyelvi eltérés okozta. Amikor a perszónák magyarul tettek fel kiegészítő kérdéseket, a chatbot teljesítménye drasztikusan romlott, kritikus hibákhoz (API hiba, alapvető hozzávalók meg nem találása) vezetett. A kommunikáció angolra váltása azonnal megszüntette ezeket a súlyos problémákat.
2.  **A `temperature` paraméter hatása:** A `temperature` csökkentése `0.3`-ra (még angol nyelvű kommunikációval is) rontotta a chatbot teljesítményét a baseline-hoz képest. A modell kevésbé rugalmasan értelmezte a felhasználói szándékot, és hajlamosabb volt apróbb kihagyásokra.
3.  **A System Prompt szigorításának hatása:** A system prompt szigorítása (még angol nyelvű kommunikációval is) vegyes eredményeket hozott. Bár bizonyos esetekben javított a pontosságon, más esetekben új, kritikus hibákat vezetett be (pl. a Thai receptnél).
4.  **Az Eredeti Baseline Kiváló Teljesítménye:** Az iterációk során bebizonyosodott, hogy az **eredeti baseline konfiguráció (alapértelmezett `temperature`, eredeti system prompt, angol nyelvű kommunikáció)** volt a legjobban teljesítő, tökéletes 3.0-s pontszámmal.
5.  **Az Iteráció Fontossága:** Ez a folyamat kiválóan demonstrálja az iteratív fejlesztés és a mérések fontosságát. A látszólag logikus változtatások is váratlan eredményekhez vezethetnek, és csak a szisztematikus tesztelés és kiértékelés segítségével lehet azonosítani a valódi problémákat és a hatékony megoldásokat.

**Következtetés:**
A projekt célja az volt, hogy egy konkrét aspektust (Pontosság és Teljesség) azonosítsunk, mérjünk és javítsunk. Bár a kezdeti baseline már jó eredményt produkált, az iterációk során szerzett tapasztalatok rávilágítottak a nyelvi kompatibilitás kritikus szerepére, és arra, hogy a modell finomhangolása során a "kevesebb néha több" elv érvényesülhet. Az eredeti konfiguráció bizonyult a legrobosztusabbnak és legpontosabbnak.

---

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

- [ ] Batch evaluáció 20-30 random kérdéssel
- [ ] Hallucináció detektálás (comparing DB vs. output)
- [ ] User feedback loop (thumbs up/down)
- [ ] Metadata szűrés (prep_time, vegetarian, cuisine, stb.)

---

## Irodalom

**Érdemes elolvasni az előző házira vonatkozóan (Cubix3-ban):**
- Hallucináció problémája és boundary value analysis
- Score tartomány analízis (0.75-0.85 "veszélyes zóna")
- System prompt fine-tuning az adatforrás korlátozásához

---

## Evaluation Framework

A projekt iteratív fejlesztéséhez egy **evaluation/** mappa tartozik, amely Python szkripteket, szimulált felhasználói perszónákat, és egy LLM-as-a-Judge alapú kiértékelő rendszert tartalmaz.

### Multi-Turn Evaluation Framework

A házi feladatnak megfelelően egy többkörös (multi-turn) kiértékelési rendszert tartalmaz, hogy az asszisztens teljesítményét valósághű, beszélgetés-szerű helyzetekben mérjük.

#### Metodológia
1.  **Perszóna-alapú Szimuláció (`evaluation/simulation.py`):**
    *   Létrehoztam két szimulált felhasználói perszónát, akiknek konkrét céljaik vannak:
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

| Persona & Goal 	| Score | Indoklás (Összefoglaló) 														|
|-------------------|-------|-------------------------------------------------------------------------------|
| Anna (Hummus) 	| 3/3 	| Kiválóan kezelte a só és víz mennyiségére vonatkozó kiegészítő kérdéseket. 	|
| Bence (Thai)  	| 3/3 	| Több, teljes és pontos receptet adott, zökkenőmentesen kezelve a párbeszédet. |
| Anna (Quinoa/Brokkoli)| 3/3 	| Helyesen jelezte a nem létező receptet, majd a kért új receptnél is pontosan válaszolt a kiegészítő kérdésre. |

### Iterációs Fejlesztés Terve

Bár a baseline eredmény kiváló, a házi feladat az iterációs folyamat dokumentálásáról szól. A következő lépés egy tervezett iteráció végrehajtása és annak hatásának mérése.

**Következő Iteráció:** **Temperature csökkentése (0.7 -> 0.3)**.
- **Hipotézis:** Bár a rendszer most is pontos, egy alacsonyabb temperature érték még determinisztikusabbá, "robotosabbá" teheti a válaszokat, ami potenciálisan csökkenti a kreativitást, de növeli a reprodukálhatóságot. Megvizsgáltam, hogy ez a változtatás ront-e a felhasználói élményen vagy a pontszámon.

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

- [ ] Batch evaluáció 20-30 random kérdéssel
- [ ] Hallucináció detektálás (comparing DB vs. output)
- [ ] User feedback loop (thumbs up/down)
- [ ] Metadata szűrés (prep_time, vegetarian, cuisine, stb.)

---
