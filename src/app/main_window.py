# app/main_window.py
import os
import sys
import customtkinter as ctk
from tkinter import filedialog, messagebox
import pygame
import random
import time
from functools import partial
import threading

from . import data_manager, theme_manager, search
from . import updater
from .ui_components import GradientFrame
from .ui_panels import SidebarFrame, ContentFrame, PlayerControlFrame
from PIL import Image
from .data_manager import FAVORITES_NAME

VERSION = "1.0.4" 

class RaZPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()
        config = data_manager.load_config()
        self.theme_name = config.get("theme", "Яндекс.Ночь")
        self.THEMES = theme_manager.THEMES
        self.playlist_data = {}
        self.current_category = "Все треки"
        self.current_track_index = -1
        self.current_song_length = 0
        self.is_playing = False
        self.is_paused = False
        self.is_shuffle = False
        self.is_repeat = False
        self.is_recommend_mode = False
        self.is_previewing = False
        self.seeking = False
        self.last_seek_position = 0
        self.pygame = pygame
        self.last_volume = float(config.get("volume", 1.0))
        self.download_covers_var = ctk.BooleanVar(value=config.get("download_covers", True))
        
        self.title("RaZ Music Player")
        self.geometry("1100x700")
        self.minsize(950, 650)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        pygame.mixer.init()
        ctk.set_appearance_mode("dark")
        
        self.init_ui()
        self.load_playlist_data()
        self.update_progress()
        self.set_volume(self.last_volume * 100, True)
        self.sidebar.select_playlist_button("Все треки")

        update_thread = threading.Thread(target=updater.check_for_updates, args=(VERSION,), daemon=True)
        update_thread.start()

    def init_ui(self):
        """Инициализирует и размещает основные панели интерфейса."""
        colors = self.THEMES[self.theme_name]
        
        self.bg_frame = GradientFrame(self, color1=colors.get("gradient_top"), color2=colors.get("gradient_bottom"))
        self.bg_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.sidebar = SidebarFrame(self, controller=self)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        
        self.content_frame = ContentFrame(self, controller=self)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=(10, 0))
        
        self.player_bar = PlayerControlFrame(self, controller=self)
        self.player_bar.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

        self.apply_theme()

    def apply_theme(self):
        colors = self.THEMES.get(self.theme_name, list(self.THEMES.values())[0])
        self.bg_frame.update_gradient(colors["gradient_top"], colors["gradient_bottom"])
        self.configure(fg_color=colors["gradient_bottom"])
        self.sidebar.apply_theme(colors)
        self.player_bar.apply_theme(colors)
        self.content_frame.refresh_current_view() # Это перерисует центральную панель с новой темой

    def show_library_view(self, category_name):
        self.current_category = category_name
        self.content_frame.display_playlist_view(category_name, self.playlist_data.get(category_name, []))
        self.stop()

    def show_search_view(self):
        self.content_frame.display_search_view()

    def show_themes_view(self):
        self.content_frame.display_themes_view()

    def load_playlist_data(self):
        self.playlist_data = data_manager.load_playlist()
        self.sidebar.update_playlist_list(list(self.playlist_data.keys()))

    def save_current_config(self):
        data_manager.save_config(self.theme_name, self.last_volume, self.download_covers_var.get())

    def on_closing(self):
        self.save_current_config()
        data_manager.save_playlist(self.playlist_data)
        pygame.mixer.quit()
        self.destroy()

    # --- МЕТОДЫ УПРАВЛЕНИЯ ПЛЕЙЛИСТАМИ (теперь внутри класса) ---
    def add_category(self, new_cat_name):
        if new_cat_name and new_cat_name not in self.playlist_data:
            self.playlist_data[new_cat_name] = []
            self.sidebar.update_playlist_list(list(self.playlist_data.keys()))
            self.sidebar.select_playlist_button(new_cat_name)
            # self.show_library_view(new_cat_name) # select_playlist_button уже это делает
            data_manager.save_playlist(self.playlist_data)
        elif not new_cat_name:
            messagebox.showwarning("Ошибка", "Имя категории не может быть пустым.")
        else:
            messagebox.showwarning("Ошибка", f"Категория '{new_cat_name}' уже существует.")

    def delete_category(self, cat_to_delete):
        if cat_to_delete in ["Все треки", "Загруженное", FAVORITES_NAME]:
            messagebox.showerror("Ошибка", f"Нельзя удалить системную категорию '{cat_to_delete}'.")
            return

        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить категорию '{cat_to_delete}'?"):
            
            if self.sidebar.current_playlist_button and self.sidebar.current_playlist_button.cget("text") == cat_to_delete:
                self.sidebar.current_playlist_button = None

            del self.playlist_data[cat_to_delete]
            self.sidebar.update_playlist_list(list(self.playlist_data.keys()))
            self.sidebar.select_playlist_button("Все треки")
            data_manager.save_playlist(self.playlist_data)

    def add_track(self):
        filepaths = filedialog.askopenfilenames(filetypes=(("Аудиофайлы", "*.mp3 *.wav *.ogg"), ("Все файлы", "*.*")))
        if not filepaths: return
        added_to_current = False
        for path in filepaths:
            filename = os.path.basename(path)
            track_data = {"name": filename, "path": path, "score": 0, "cover_path": None}
            if not any(t['path'] == path for t in self.playlist_data["Все треки"]):
                self.playlist_data["Все треки"].append(track_data)
            if self.current_category not in ["Все треки", "Загруженное", FAVORITES_NAME]:
                if not any(t['path'] == path for t in self.playlist_data[self.current_category]):
                    self.playlist_data[self.current_category].append(track_data)
                    added_to_current = True
        if self.current_category == "Все треки" or added_to_current:
            self.content_frame.display_playlist_view(self.current_category, self.playlist_data.get(self.current_category, []))
        data_manager.save_playlist(self.playlist_data)

    def remove_track(self, track_index_in_view):
        if track_index_in_view == -1:
            messagebox.showwarning("Ошибка", "Сначала выберите трек для удаления.")
            return
        track_to_remove = self.playlist_data[self.current_category][track_index_in_view]
        if self.current_category == "Все треки":
            if messagebox.askyesno("Подтверждение", f"Удалить трек '{track_to_remove['name']}' из ВСЕХ плейлистов? Это действие необратимо."):
                path_to_remove = track_to_remove.get('path')
                for category in self.playlist_data: self.playlist_data[category] = [t for t in self.playlist_data[category] if t.get('path') != path_to_remove]
            else: return
        else: self.playlist_data[self.current_category].pop(track_index_in_view)
        self.stop()
        self.content_frame.display_playlist_view(self.current_category, self.playlist_data.get(self.current_category, []))
        data_manager.save_playlist(self.playlist_data)

    def add_downloaded_track(self, file_path, cover_path):
        filename = os.path.basename(file_path)
        track_data = {"name": filename, "path": file_path, "score": 0, "cover_path": cover_path}
        if not any(t['path'] == file_path for t in self.playlist_data["Загруженное"]):
            self.playlist_data["Загруженное"].append(track_data)
        if not any(t['path'] == file_path for t in self.playlist_data["Все треки"]):
            self.playlist_data["Все треки"].append(track_data)
        if self.current_category in ["Все треки", "Загруженное"]:
            self.content_frame.display_playlist_view(self.current_category, self.playlist_data.get(self.current_category, []))
        data_manager.save_playlist(self.playlist_data)
        messagebox.showinfo("Загрузка завершена", f"Трек '{filename}' добавлен в 'Загруженное' и 'Все треки'.")

    def select_and_play(self, index):
        self.current_track_index = index
        self.play_track()
        self.content_frame.update_active_track_highlight(index)

    def play_track(self, start_time=0):
        self.is_previewing = False
        if self.current_track_index == -1 or not self.playlist_data.get(self.current_category):
            self.stop()
            return
        
        track_info = self.playlist_data[self.current_category][self.current_track_index]
        try:
            pygame.mixer.music.load(track_info['path'])
            
            # --- КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ 1: ---
            # Длина трека определяется ВСЕГДА при загрузке, а не только при старте с нуля.
            sound = pygame.mixer.Sound(track_info['path'])
            self.current_song_length = sound.get_length()
            
            # Этот метод теперь - ЕДИНСТВЕННОЕ место, где устанавливается смещение.
            self.last_seek_position = start_time
            # --- КОНЕЦ ИСПРАВЛЕНИЯ 1 ---
            
            pygame.mixer.music.play(start=start_time)

            self.is_playing = True
            self.is_paused = False
            self.player_bar.update_play_pause_button(True)
            self.player_bar.update_track_info_display(track_info)
            self.player_bar.update_fav_button_status()
        except pygame.error as e:
            messagebox.showerror("Ошибка", f"Не удалось воспроизвести: {e}")
            self.is_playing = False

    def stop(self, is_stopping_for_preview=False):
        pygame.mixer.music.stop(); self.is_playing = False; self.current_track_index = -1
        self.player_bar.update_play_pause_button(False); self.player_bar.reset_progress()
        self.content_frame.update_active_track_highlight(-1)
        if not is_stopping_for_preview: self.player_bar.clear_track_info()

    def play_pause(self):
        if self.is_playing or self.is_previewing:
            if self.is_paused:
                current_absolute_pos = self.last_seek_position + (pygame.mixer.music.get_pos() / 1000)
                self.last_seek_position = current_absolute_pos
                
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.player_bar.update_play_pause_button(True)
            else:
                pygame.mixer.music.pause()
                self.is_paused = True
                self.player_bar.update_play_pause_button(False)
        elif self.current_track_index != -1:
            self.play_track()
    def next_track(self):
        track_list = self.playlist_data.get(self.current_category, [])
        if not track_list: return
        if self.is_recommend_mode: new_index = self._get_recommended_track_index()
        elif self.is_shuffle: new_index = random.randint(0, len(track_list) - 1)
        else: new_index = (self.current_track_index + 1) % len(track_list)
        self.select_and_play(new_index)

    def prev_track(self):
        track_list = self.playlist_data.get(self.current_category, []);
        if not track_list: return
        new_index = (self.current_track_index - 1) % len(track_list); self.select_and_play(new_index)

    def update_progress(self):
        if (self.is_playing or self.is_previewing) and not self.is_paused and not self.seeking:
            if self.current_song_length > 0:
                time_since_play_start = pygame.mixer.music.get_pos() / 1000
                if time_since_play_start >= 0:
                    absolute_pos = self.last_seek_position + time_since_play_start
                    if absolute_pos > self.current_song_length: absolute_pos = self.current_song_length
                    self.player_bar.update_progress_slider(absolute_pos, self.current_song_length)
        if (self.is_playing or self.is_previewing) and not pygame.mixer.music.get_busy() and not self.is_paused:
            self.last_seek_position = 0
            if self.is_previewing: self.stop(); self.is_previewing = False
            elif self.is_repeat: self.play_track()
            else: self.next_track()
        self.after(100, self.update_progress)

    def on_slider_press(self, event): self.seeking = True

    def on_slider_drag(self, value_str):
        if self.seeking and self.current_song_length > 0:
            seek_time = self.current_song_length * (float(value_str) / 100)

            self.player_bar.update_current_time_label(seek_time)

    def on_slider_seek_release(self, event):

        self.after(50, self._perform_seek)

    def _perform_seek(self):
        self.seeking = False
        if (self.is_playing or self.is_previewing) and self.current_song_length > 0:
            # Получаем финальное значение ползунка
            value = self.player_bar.progress_slider.get()
            seek_time = self.current_song_length * (value / 100)
            
            if self.is_previewing:
                pygame.mixer.music.set_pos(seek_time)
            else:
                self.play_track(start_time=seek_time)

    def set_theme(self, theme_name):
        self.theme_name = theme_name; self.apply_theme(); self.save_current_config()

    def set_volume(self, value, from_start=False):
        volume = float(value) / 100; pygame.mixer.music.set_volume(volume)
        if not from_start: self.last_volume = volume
        self.player_bar.volume_slider.set(value)
        self.player_bar.update_mute_button_status(volume > 0)

    def toggle_mute(self):
        current_volume = pygame.mixer.music.get_volume()
        if current_volume > 0: self._unmuted_volume = current_volume; self.set_volume(0)
        else: volume_to_restore = getattr(self, '_unmuted_volume', 1.0) * 100; self.set_volume(volume_to_restore)

    def toggle_shuffle(self):
        self.is_shuffle = not self.is_shuffle
        if self.is_shuffle: self.is_recommend_mode = False
        self.player_bar.update_mode_buttons()

    def toggle_repeat(self):
        self.is_repeat = not self.is_repeat; self.player_bar.update_mode_buttons()

    def toggle_recommend_mode(self):
        self.is_recommend_mode = not self.is_recommend_mode
        if self.is_recommend_mode: self.is_shuffle = False
        self.player_bar.update_mode_buttons()

    def _get_recommended_track_index(self):
        track_list = self.playlist_data.get(self.current_category, [])
        if not track_list: return -1
        weights = [max(1, 10 + track.get('score', 0)) for track in track_list]
        try: recommended_track = random.choices(track_list, weights=weights, k=1)[0]; return track_list.index(recommended_track)
        except IndexError: return 0 if track_list else -1

    def toggle_favorite(self):
        if self.current_track_index == -1: return
        track_info = dict(self.playlist_data[self.current_category][self.current_track_index])
        fav_list = self.playlist_data.get(FAVORITES_NAME, [])
        found_track_in_fav = -1
        for i, fav_track in enumerate(fav_list):
            if fav_track['path'] == track_info['path']: found_track_in_fav = i; break
        if found_track_in_fav != -1: fav_list.pop(found_track_in_fav)
        else: fav_list.append(track_info)
        data_manager.save_playlist(self.playlist_data)
        self.player_bar.update_fav_button_status()
        if self.current_category == FAVORITES_NAME: self.content_frame.display_playlist_view(self.current_category, self.playlist_data.get(self.current_category, []))

    def _rate_track(self, value):
        if self.current_track_index == -1: return
        current_path = self.playlist_data[self.current_category][self.current_track_index]['path']
        for category in self.playlist_data:
            for track in self.playlist_data[category]:
                if track.get('path') == current_path: track['score'] = track.get('score', 0) + value
        data_manager.save_playlist(self.playlist_data)
        self.player_bar.update_track_info_display(self.playlist_data[self.current_category][self.current_track_index])

    def like_track(self): self._rate_track(1)
    
    def dislike_track(self): self._rate_track(-1)