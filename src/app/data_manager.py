import json
import os
import sys
import time

# ... (Код определения путей без изменений) ...
def is_frozen():
    return getattr(sys, 'frozen', False)

def get_project_root():
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_app_root():
    if is_frozen():
        return sys._MEIPASS
    return get_project_root()

PROJECT_ROOT = get_project_root()
APP_ROOT = get_app_root()

DATA_DIR = os.path.join(PROJECT_ROOT, "RaZ_Data")
os.makedirs(DATA_DIR, exist_ok=True)

def _get_data_path(filename):
    return os.path.join(DATA_DIR, filename)

DATA_FILE = _get_data_path("raz_playlist_v2.json")
CONFIG_FILE = _get_data_path("raz_config.json")
FAVORITES_NAME = "❤️ Избранное"

def load_config():
    # ... (Код без изменений) ...
    try:
        with open(CONFIG_FILE, 'r') as f: config = json.load(f)
        if 'download_covers' not in config: config['download_covers'] = True
        return config
    except (FileNotFoundError, json.JSONDecodeError):
        return {"theme": "Яндекс.Ночь", "volume": 1.0, "download_covers": True}


def save_config(theme, volume, download_covers):
    # ... (Код без изменений) ...
    with open(CONFIG_FILE, 'w') as f: json.dump({"theme": theme, "volume": volume, "download_covers": download_covers}, f, indent=4)


def load_playlist():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)

            if "Избранное" in playlist_data and FAVORITES_NAME not in playlist_data:
                playlist_data[FAVORITES_NAME] = playlist_data.pop("Избранное")

            for cat in ["Все треки", "Загруженное", FAVORITES_NAME]:
                if cat not in playlist_data:
                    playlist_data[cat] = []

            for category in playlist_data:
                for track in playlist_data[category]:
                    track.setdefault('score', 0)
                    track.setdefault('cover_path', None)
                    track.setdefault('play_count', 0)
                    track.setdefault('album', 'Неизвестный альбом')
                    track.setdefault('artist', 'Неизвестный исполнитель')
                    track.setdefault('duration', 0)
                    track.setdefault('date_added', time.time()) 
                    # --- НОВОЕ ПОЛЕ ---
                    track.setdefault('volume_multiplier', 1.0)

            return playlist_data
        except (json.JSONDecodeError, TypeError):
            pass

    return {"Все треки": [], "Загруженное": [], FAVORITES_NAME: []}

def save_playlist(playlist_data):
    # ... (Код без изменений) ...
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(playlist_data, f, indent=4, ensure_ascii=False)
    except Exception as e: print(f"Ошибка сохранения плейлиста: {e}")