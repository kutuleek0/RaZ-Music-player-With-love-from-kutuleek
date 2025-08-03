# app/theme_manager.py
import json
from . import data_manager

THEMES_FILE = data_manager._get_data_path("themes.json")

def get_default_themes():
    return {
      "Яндекс.Ночь": {
        "gradient_top": "#2a2a2a", "gradient_bottom": "#121212", "bg": "#121212",
        "frame": "#1c1c1c", "frame_secondary": "#121212",
        "accent": "#FFD600", "hover": "#f9e04a", "text": "#FFFFFF",
        "text_dim": "#b3b3b3", "text_bright": "#FFFFFF", "text_on_accent": "#000000"
      },
      "Северное сияние": {
        "gradient_top": "#e9eef2", "gradient_bottom": "#f4f6f8", "bg": "#ffffff",
        "frame": "#e9eef2", "frame_secondary": "#dfe5ea",
        "accent": "#0077c2", "hover": "#005a9e", "text": "#000000",
        "text_dim": "#555555", "text_bright": "#000000", "text_on_accent": "#FFFFFF"
      },
      "Глубокий космос": {
        "gradient_top": "#0f0c29", "gradient_bottom": "#24243e", "bg": "#0f0c29",
        "frame": "#1f1f3a", "frame_secondary": "#1a1a32",
        "accent": "#7e57c2", "hover": "#5e35b1", "text": "#e0e0e0",
        "text_dim": "#9e9e9e", "text_bright": "#ffffff", "text_on_accent": "#FFFFFF"
      },
      "Специальная 1": {
        "gradient_top": "#2c2a4a", "gradient_bottom": "#1e1c32", "bg": "#2c2a4a",
        "frame": "#3b3861", "frame_secondary": "#302e52",
        "accent": "#c792ea", "hover": "#e1b6ff", "text": "#e0e0e0",
        "text_dim": "#a0a0a0", "text_bright": "#ffffff", "text_on_accent": "#000000"
      },
      "Специальная 2": {
        "gradient_top": "#f2e7fe", "gradient_bottom": "#e8d9f5", "bg": "#f2e7fe",
        "frame": "#e8d9f5", "frame_secondary": "#ddcde8",
        "accent": "#8e44ad", "hover": "#a569bd", "text": "#333333",
        "text_dim": "#666666", "text_bright": "#000000", "text_on_accent": "#ffffff"
      }
    }

def save_themes(themes_data):
    global THEMES
    THEMES = themes_data
    try:
        with open(THEMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(themes_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка сохранения тем: {e}")

def load_themes():
    default_themes = get_default_themes()
    try:
        with open(THEMES_FILE, 'r', encoding='utf-8') as f:
            loaded_themes = json.load(f)
        for theme_name, theme_data in loaded_themes.items():
            reference_theme = default_themes.get(theme_name, default_themes["Яндекс.Ночь"])
            for key, value in reference_theme.items():
                 if key not in theme_data:
                      print(f"В теме '{theme_name}' отсутствует ключ '{key}'. Добавляем значение по умолчанию.")
                      theme_data[key] = value
        return loaded_themes
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Файл тем '{THEMES_FILE}' не найден или поврежден. Создаем новый с темами по умолчанию.")
        save_themes(default_themes)
        return default_themes

THEMES = load_themes()