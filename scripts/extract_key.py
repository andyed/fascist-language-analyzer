import sqlite3
import json
import os

DB_PATH = "/Users/andyed/Documents/dev/nanobot/webui_data/webui.db.original"

def extract_key():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM config ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            config = json.loads(row[0])
            print("Config keys:", config.keys())
            if "openai" in config:
                print("OpenAI config keys:", config["openai"].keys())
                print("OpenAI config dump:", json.dumps(config["openai"], indent=2))
        else:
            print("No config row found in DB.")
            
    except Exception as e:
        print(f"Error reading DB: {e}")

if __name__ == "__main__":
    extract_key()
