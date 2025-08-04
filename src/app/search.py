# src/app/search.py
import os
import time
import threading
import yt_dlp
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image
import requests
from io import BytesIO
from . import data_manager

DOWNLOAD_PATH = os.path.join(data_manager.DATA_DIR, "music")
FFMPEG_PATH = os.path.join(data_manager.APP_ROOT, "ffmpeg.exe") 

def load_image_from_url(url, size, callback):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        image_data = BytesIO(response.content)
        pil_image = Image.open(image_data)
        ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=size)
        callback(ctk_image)
    except Exception as e:
        print(f"Ошибка загрузки обложки: {e}")
        callback(None)

def start_image_load_thread(url, size, callback):
    threading.Thread(target=load_image_from_url, args=(url, size, callback), daemon=True).start()

def start_search_thread(app):
    query = app.current_content_frame.search_entry.get()
    
    if not query.strip():
        app.current_content_frame.search_status_label.configure(text="Введите поисковый запрос.")
        return
        
    for widget in app.current_content_frame.search_results_frame.winfo_children():
        widget.destroy()
        
    app.search_results_cache = []
    app.current_content_frame.search_status_label.configure(text="Идет поиск...")
    app.current_content_frame.search_button.configure(state="disabled")
    threading.Thread(target=search_tracks_parallel, args=(app, query), daemon=True).start()

def _search_source(query, source, result_list):
    ydl_opts = {'format': 'bestaudio', 'noplaylist': True, 'default_search': source, 'quiet': True, 'extract_flat': 'in_playlist'}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_result = ydl.extract_info(query, download=False)
            if 'entries' in search_result:
                for entry in search_result['entries']:
                    if entry.get('ie_key') == 'Youtube':
                        video_id = entry.get('id')
                        if video_id: entry['thumbnail'] = f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
                    if entry.get('thumbnail'): result_list.append(entry)
    except Exception as e:
        print(f"Ошибка при поиске на {source}: {e}")

def search_tracks_parallel(app, query):
    threads = []
    results = []
    sources = ["ytsearch7", "scsearch7"]
    for source in sources:
        thread = threading.Thread(target=_search_source, args=(f"{source}:{query}", source, results), daemon=True)
        threads.append(thread)
        thread.start()
    for thread in threads: thread.join()
    app.search_results_cache = results
    app.after(0, app.current_content_frame.display_search_results)

def start_download_thread(app, track_data, download_btn):
    download_btn.configure(text="...", state="disabled")
    threading.Thread(target=download_track, args=(app, track_data, download_btn), daemon=True).start()

def download_track(app, track_data, download_btn):
    url = track_data.get('url')
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    
    filename_template = os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s')
    ffmpeg_location = FFMPEG_PATH if os.path.exists(FFMPEG_PATH) else "ffmpeg"

    ydl_opts = {
        'format': 'bestaudio/best', 'outtmpl': filename_template,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'ffmpeg_location': ffmpeg_location, 'quiet': True, 'nocheckcertificate': True
    }
    if app.download_covers_var.get(): ydl_opts['writethumbnail'] = True
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base_path, _ = os.path.splitext(ydl.prepare_filename(info))
            downloaded_file_path = base_path + ".mp3"
            cover_path = None
            if app.download_covers_var.get():
                for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    if os.path.exists(base_path + ext): cover_path = base_path + ext; break
            if os.path.exists(downloaded_file_path):
                app.after(0, app.add_downloaded_track, downloaded_file_path, cover_path)
                if download_btn.winfo_exists(): app.after(0, lambda: download_btn.configure(text="✓"))
            else: raise FileNotFoundError(f"Файл не найден после конвертации: {downloaded_file_path}")
    except Exception as e:
        print(f"Ошибка скачивания: {e}")
        if download_btn.winfo_exists():
            app.after(0, lambda: download_btn.configure(text="X", fg_color="red"))
            app.after(1500, lambda: download_btn.configure(text="⏬", fg_color=app.THEMES[app.theme_name]["bg"], state="normal"))