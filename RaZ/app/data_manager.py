# app/data_manager.py
import json
import os

# --- НОВАЯ СТРУКТУРА ---
DATA_DIR = "RaZ_Data"
# Создаем директорию, если она не существует
os.makedirs(DATA_DIR, exist_ok=True)

def _get_data_path(filename):
    """Возвращает полный путь к файлу данных."""
    return os.path.join(DATA_DIR, filename)

DATA_FILE = _get_data_path("raz_playlist_v2.json")
CONFIG_FILE = _get_data_path("raz_config.json")
# --- КОНЕЦ ИЗМЕНЕНИЙ ---

FAVORITES_NAME = "❤️ Избранное"

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f: 
            config = json.load(f)
            if 'download_covers' not in config:
                config['download_covers'] = True
            return config
    except (FileNotFoundError, json.JSONDecodeError):
        return {"theme": "Яндекс.Ночь", "volume": 1.0, "download_covers": True}

def save_config(theme, volume, download_covers):
    with open(CONFIG_FILE, 'w') as f: 
        json.dump({"theme": theme, "volume": volume, "download_covers": download_covers}, f, indent=4)

def load_playlist():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f: playlist_data = json.load(f)
            
            if "Избранное" in playlist_data and FAVORITES_NAME not in playlist_data:
                playlist_data[FAVORITES_NAME] = playlist_data.pop("Избранное")

            for cat in ["Все треки", "Загруженное", FAVORITES_NAME]:
                if cat not in playlist_data: playlist_data[cat] = []
            
            for category in playlist_data:
                for track in playlist_data[category]:
                    if "score" not in track: track["score"] = 0
                    if "cover_path" not in track: track["cover_path"] = None
            return playlist_data
        except (json.JSONDecodeError, TypeError): pass
    return {"Все треки": [], "Загруженное": [], FAVORITES_NAME: []}

def save_playlist(playlist_data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(playlist_data, f, indent=4, ensure_ascii=False)
    except Exception as e: print(f"Ошибка сохранения плейлиста: {e}")