import requests
import os
import sys
import time
import re

def read_file(filepath):
    """Beolvassa a fajl tartalmat kivetelkezelessel"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"  Hiba: A fájl nem létezik: {filepath}")
        return None
    except PermissionError:
        print(f"  Hiba: Nincs olvasási jogosultság: {filepath}")
        return None
    except UnicodeDecodeError:
        print(f"  Hiba: Nem UTF-8 kódolású fájl: {filepath}")
        return None
    except IOError as e:
        print(f"  Hiba I/O művelet közben ({filepath}): {e}")
        return None
    except Exception as e:
        print(f"  Váratlan hiba ({filepath}): {type(e).__name__} - {e}")
        return None


def extract_yaml_frontmatter(text):
    """Kinyeri a YAML front matter-t"""
    yaml_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(yaml_pattern, text, re.DOTALL)
    
    if match:
        yaml_content = match.group(1)
        remaining_text = text[match.end():]
        
        # Egyszerű key-value parsing
        metadata = {}
        for line in yaml_content.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()
        
        return metadata, remaining_text
    
    return {}, text

def chunk_markdown(text):
    """Markdown szöveg darabolása headingek alapján, metaadatokkal"""
    
    # 1. YAML front matter kinyerése
    metadata, content = extract_yaml_frontmatter(text)
    
    # 2. Markdown headingek szerinti darabolás
    # Split by ## headings (h2)
    sections = re.split(r'\n##\s+', content)
    
    chunks = []
    
    # Ha van metadata, az első chunk legyen a metadata
    if metadata:
        metadata_text = ', '.join([f"{k}: {v}" for k, v in metadata.items()])
        chunks.append(f"Recipe metadata: {metadata_text}")
    
    # 3. Minden szakasz = 1 chunk
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        
        # Az első szakasz lehet a bevezetés (ha nincs heading előtte)
        if i == 0 and not section.startswith('#'):
            # Ez a főszöveg heading nélkül
            if section:
                chunks.append(section)
        else:
            # Szakaszok heading-gel
            chunks.append(section)
    
    # Ha nem sikerült markdown chunking, fallback az egyszerű módszerre
    if len(chunks) <= 1:
        chunks = [s.strip() for s in text.split('.') if s.strip()]
    
    return chunks

    
def upload_to_server(chunks, filename):
    """Feltölti a chunk-okat a szerverhez teljes hibakezeléssel"""
    url = "http://localhost:3000/api/upload"
    
    try:
        payload = {
            "chunks": chunks,
            "filename": filename
        }
    except Exception as e:
        print(f"  Hiba a payload készítése közben ({filename}): {e}")
        return False
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        print(f"  Sikeres: {filename} ({len(chunks)} chunk)")
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"  Hiba: Nem lehet csatlakozni a szerverhez")
        print(f"  Ellenorizd, hogy fut-e a Next.js szerver (pnpm dev)")
        return False
    except requests.exceptions.Timeout:
        print(f"  Hiba: Idotullepes 30mp utan ({filename})")
        return False
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 'Unknown'
        print(f"  HTTP hiba ({filename}): {status_code}")
        try:
            print(f"  Uzenet: {e.response.text[:200]}")
        except:
            pass
        return False
    except requests.exceptions.RequestException as e:
        print(f"  Halozati hiba ({filename}): {e}")
        return False
    except Exception as e:
        print(f"  Varatlan hiba a feltoltes soran ({filename}): {type(e).__name__} - {e}")
        return False

def process_folder(folder_path):
    """Feldolgoz egy mappát - .txt és .md fájlokat tölt fel"""
    
    # Mappa létezésének ellenőrzése
    try:
        if not os.path.exists(folder_path):
            print(f"Hiba: A mappa nem talalhato: {folder_path}")
            sys.exit(1)
        
        if not os.path.isdir(folder_path):
            print(f"Hiba: Ez nem egy mappa: {folder_path}")
            sys.exit(1)
    except OSError as e:
        print(f"Hiba a mappa eleresekor: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Varatlan hiba: {type(e).__name__} - {e}")
        sys.exit(1)
    
    # Támogatott fájltípusok
    supported_extensions = ['.txt', '.md']
    
    # Fájlok gyűjtése kivételkezeléssel
    files_to_process = []
    try:
        for filename in os.listdir(folder_path):
            try:
                file_path = os.path.join(folder_path, filename)
                
                # Csak fájlokat, mappákat nem
                if not os.path.isfile(file_path):
                    continue
                
                # Ellenőrizd a kiterjesztést
                _, ext = os.path.splitext(filename)
                if ext.lower() in supported_extensions:
                    files_to_process.append((file_path, filename))
                    
            except OSError as e:
                print(f"  Figyelmeztetes: Nem sikerult elerni a fajlt ({filename}): {e}")
                continue
            except Exception as e:
                print(f"  Figyelmeztetes: Hiba ({filename}): {type(e).__name__} - {e}")
                continue
                
    except PermissionError:
        print(f"Hiba: Nincs jogosultsag a mappa olvasasahoz: {folder_path}")
        sys.exit(1)
    except OSError as e:
        print(f"Hiba a mappa beolvasasakor: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Varatlan hiba a fajlok gyujtese soran: {type(e).__name__} - {e}")
        sys.exit(1)
    
    if not files_to_process:
        print(f"Nem talalhato .txt vagy .md fajl a mappaban: {folder_path}")
        sys.exit(1)
    
    print(f"\nTalalt fajlok: {len(files_to_process)}")
    print(f"Feltoltes kezdese...\n")
    
    success_count = 0
    fail_count = 0
    
    # Fájlok feldolgozása
    for i, (file_path, filename) in enumerate(files_to_process, 1):
        print(f"[{i}/{len(files_to_process)}] {filename}")
        
        try:
            text = read_file(file_path)
            
            if text is None:
                fail_count += 1
                continue
            
            if not text.strip():
                print(f"  Figyelmeztetes: Ures fajl, kihagyva")
                fail_count += 1
                continue
            
            # chunks = chunk_text(text)
            chunks = chunk_markdown(text)
            
            if not chunks:
                print(f"  Figyelmeztetes: Nem sikerult chunk-okat generalni")
                fail_count += 1
                continue
            
            if upload_to_server(chunks, filename):
                success_count += 1
                time.sleep(0.5)  # Kis szünet a szerver terhelésének csökkentésére
            else:
                fail_count += 1
                
        except KeyboardInterrupt:
            print(f"\n\nFeltoltes megszakitva a felhasznalo altal")
            print(f"Eddig feldolgozott: {i-1}/{len(files_to_process)}")
            sys.exit(1)
        except Exception as e:
            print(f"  Varatlan hiba ({filename}): {type(e).__name__} - {e}")
            fail_count += 1
            continue
    
    print(f"\n--- Osszegzes ---")
    print(f"Sikeres: {success_count}")
    print(f"Sikertelen: {fail_count}")
    print(f"Osszes: {len(files_to_process)}")

def main():
    try:
        if len(sys.argv) < 2:
            print("Hasznalat: python upload_folder.py <mappa_nev>")
            print("Pelda: python upload_folder.py recipes/")
            sys.exit(1)
        
        folder_path = sys.argv[1]
        process_folder(folder_path)
        
    except KeyboardInterrupt:
        print("\n\nProgram megszakitva")
        sys.exit(1)
    except Exception as e:
        print(f"\nKritikus hiba: {type(e).__name__} - {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()