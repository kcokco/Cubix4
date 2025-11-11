import requests
import os
import sys

"""open(filepath, 'r', encoding='utf-8'): Megnyitja a fájlt olvasásra ('r' = read). Az encoding='utf-8' azért kell, hogy a magyar ékezeteket is jól kezelje.
with ... as f:: Ez egy context manager. Automatikusan bezárja a fájlt, ha végeztél vele, még akkor is, ha hiba történik.
f.read(): Beolvassa az egész fájl tartalmát egy hosszú string-ként.
"""
def read_file(filepath):
    """Beolvassa a fájl tartalmát"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Hiba: A fájl nem található: {filepath}")
        sys.exit(1)
    except PermissionError:
        print(f"❌ Hiba: Nincs jogosultság a fájl olvasásához: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Hiba a fájl olvasása közben: {e}")
        sys.exit(1)

"""Ez egy list comprehension (lista generálás).
    text.split('.'): A teljes szöveget pontok mentén szétdarabolja. Pl.:
    python   "Hello. How are you." → ["Hello", " How are you", ""]
    for s in text.split('.'): Végigmegy minden darabon
    s.strip(): Levágja a felesleges szóközöket az elejéről és végéről:
    python   " How are you" → "How are you"
    if s.strip(): Kiszűri az üres stringeket (ahol csak szóköz volt vagy semmi)
    [s.strip() for ...]: Minden érvényes darabból csinál egy lista elemet
    Eredmény:
    python["Hello", "How are you"]
"""
def chunk_text(text):
    """Szöveg darabolása mondatokra"""
    chunks = [s.strip() for s in text.split('.') if s.strip()]
    return chunks

"""payload: Ez egy dictionary (kulcs-érték párok), amit JSON formátumban küldünk a szervernek.
    requests.post(url, json=payload): HTTP POST kérést küld a szerverhez. A json=payload automatikusan átalakítja a dictionary-t JSON formátumba.
    Mit kap a szerver:
    json{
        "chunks": ["Hello", "How are you"],
        "filename": "test.txt"
    }
"""
def upload_to_server(chunks, filename):
    """Feltölti a chunk-okat a szerverhez"""
    url = "http://localhost:3000/api/upload"
    
    payload = {
        "chunks": chunks,
        "filename": filename
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()  # Hibát dob, ha nem 2xx status
        
        print(f"✅ Sikeres feltöltés: {filename}")
        print(f"   {len(chunks)} chunk feltöltve")
    except requests.exceptions.ConnectionError:
        print("❌ Hiba: Nem lehet csatlakozni a szerverhez. Fut a Next.js szerver (pnpm dev)?")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("❌ Hiba: Időtúllépés - a szerver nem válaszolt 10 másodpercen belül")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Hiba: {response.status_code}")
        print(response.text)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Váratlan hiba a feltöltés közben: {e}")
        sys.exit(1)




"""_summary_
    """
import requests
import os
import sys

def read_file(filepath):
    """Beolvassa a fájl tartalmát"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Hiba: A fájl nem található: {filepath}")
        sys.exit(1)
    except PermissionError:
        print(f"❌ Hiba: Nincs jogosultság a fájl olvasásához: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Hiba a fájl olvasása közben: {e}")
        sys.exit(1)

def chunk_text(text):
    """Szöveg darabolása mondatokra"""
    chunks = [s.strip() for s in text.split('.') if s.strip()]
    return chunks

def upload_to_server(chunks, filename):
    """Feltölti a chunk-okat a szerverhez"""
    url = "http://localhost:3000/api/upload"
    
    payload = {
        "chunks": chunks,
        "filename": filename
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()  # Hibát dob, ha nem 2xx status
        
        print(f"✅ Sikeres feltöltés: {filename}")
        print(f"   {len(chunks)} chunk feltöltve")
    except requests.exceptions.ConnectionError:
        print("❌ Hiba: Nem lehet csatlakozni a szerverhez. Fut a Next.js szerver (pnpm dev)?")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("❌ Hiba: Időtúllépés - a szerver nem válaszolt 10 másodpercen belül")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Hiba: {response.status_code}")
        print(response.text)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Váratlan hiba a feltöltés közben: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Használat: python upload_script.py <fájlnév>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    # Ellenőrzés ELTÁVOLÍTVA - a read_file() kivételkezelése gondoskodik róla
    
    text = read_file(filepath)
    
    if not text.strip():
        print(f"❌ Hiba: A fájl üres: {filepath}")
        sys.exit(1)
    
    chunks = chunk_text(text)
    
    if not chunks:
        print(f"❌ Hiba: Nem sikerült chunk-okat generálni a fájlból")
        sys.exit(1)
    
    filename = os.path.basename(filepath)
    upload_to_server(chunks, filename)

if __name__ == "__main__":
    main()