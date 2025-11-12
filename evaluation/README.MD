# Evaluation Framework - Baseline & Iterative Testing

Ez a mappa tartalmazza az **evaluációs eszközöket** a RAG asszisztens iteratív fejlesztéséhez.

## Fájlok

- **single_turn_evaluation.py** - LLM Judge alapú evaluáció (0-3 skála)
- **response_generator.py** - RAG pipeline (query → recept generálás)
- **vectordb.py** - Vector database kezelés
- **golden_dataset.json** - Baseline tesztadatok
- **requirements.txt** - Python függőségek

---

## Golden Dataset - Metodológia

A `golden_dataset.json` a **receptadatbázisonból származó kérdés-válasz párokból** áll.

### Miért receptek alapúak?

1. **Adatbázis reprezentációja**: Az AI csak a 85 feltöltött receptből kell válaszoljon
2. **Reális használati eset**: A felhasználók praktikusan receptekre kérdeznek
3. **Objektív értékelés**: Az LLM Judge pontosan meg tudja mérni az ingrediensek pontosságát
4. **Hallucináció detektálása**: Ha az AI hiányzó vagy kitalált recepteket ad, azonnal látszik

### Szerkezete

```json
{
  "metadata": { ... },
  "entries": [
    {
      "query": "What can I make with chickpeas?",
      "response": "Hummus, Channa Masala, Chickpea Salad"
    }
  ]
}

## Használat

### 1. Setup

```bash
cp .env.example .env
# API key beállítása
pip install -r requirements.txt
