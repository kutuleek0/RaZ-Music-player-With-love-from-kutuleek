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
import mutagen

from . import data_manager, theme_manager, search
from . import updater
from .ui_components import GradientFrame, VolumeDialog, SelectPlaylistDialog
from .ui_panels import SidebarFrame, ContentFrame, PlayerControlFrame
from PIL import Image
from .data_manager import FAVORITES_NAME
from .theme_editor import ThemeEditor

VERSION = "1.0.5" # Версия обновлена

class RaZPlayer(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
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
        self.seeking = False
        self.last_seek_position = 0
        self.pygame = pygame
        self.last_volume = float(config.get("volume", 1.0))
        self.download_covers_var = ctk.BooleanVar(value=config.get("download_covers", True))
        
        self.search_results_cache = []

        self.view_cache = {}
        self.current_content_frame = None
        
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
        colors = self.THEMES[self.theme_name]
        self.bg_frame = GradientFrame(self, color1=colors.get("gradient_top"), color2=colors.get("gradient_bottom"))
        self.bg_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.sidebar = SidebarFrame(self, controller=self)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=(10, 0))
        
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)
        
        self.player_bar = PlayerControlFrame(self, controller=self)
        self.player_bar.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

        self.apply_theme()

    def apply_theme(self):
        colors = self.THEMES.get(self.theme_name, list(self.THEMES.values())[0])
        self.bg_frame.update_gradient(colors["gradient_top"], colors["gradient_bottom"])
        self.configure(fg_color=colors["gradient_bottom"])
        self.sidebar.apply_theme(colors)
        self.player_bar.apply_theme(colors)
        
        if self.current_content_frame and self.current_content_frame.winfo_exists():
            self.current_content_frame.refresh_current_view()
        
    def show_view(self, view_id):
        if view_id in self.view_cache:
            if self.current_content_frame:
                self.current_content_frame.grid_remove()
            self.current_content_frame = self.view_cache[view_id]
            self.current_content_frame.grid(row=0, column=0, sticky="nsew")
            # Обновление контента (списка треков) происходит внутри refresh_current_view
            self.current_content_frame.refresh_current_view() 
        else:
            if self.current_content_frame:
                self.current_content_frame.grid_remove()
                
            new_frame = ContentFrame(self.content_container, controller=self)
            self.view_cache[view_id] = new_frame
            self.current_content_frame = new_frame
            self.current_content_frame.grid(row=0, column=0, sticky="nsew")

            if view_id.startswith("playlist_"):
                category_name = view_id.replace("playlist_", "")
                self.current_category = category_name
                tracks = self.playlist_data.get(category_name, [])
                self.current_content_frame.display_playlist_view(category_name, tracks)
            elif view_id == "search":
                self.current_content_frame.display_search_view()
            elif view_id == "themes":
                self.current_content_frame.display_themes_view()


    def show_library_view(self, category_name):
        self.current_category = category_name
        self.show_view(f"playlist_{category_name}")
        if (self.is_playing or self.is_paused) and self.current_content_frame:
            self.current_content_frame.update_active_track_highlight()

    def show_search_view(self): self.show_view("search")
    def show_themes_view(self): self.show_view("themes")

    def load_playlist_data(self):
        self.playlist_data = data_manager.load_playlist()
        self.sidebar.update_playlist_list(list(self.playlist_data.keys()))

    def save_current_config(self):
        data_manager.save_config(self.theme_name, self.last_volume, self.download_covers_var.get())

    def on_closing(self):
        self.save_current_config()
        data_manager.save_playlist(self.playlist_data)
        pygame.mixer.quit()
        self.master.destroy()

    def handle_drop(self, event):
        filepaths = self.master.tk.splitlist(event.data)
        supported_extensions = (".mp3", ".wav", ".ogg", ".flac")
        audio_files = [path for path in filepaths if path.lower().endswith(supported_extensions)]
        if audio_files: self.add_tracks_by_path(audio_files)

    def add_tracks_by_path(self, filepaths):
        if not filepaths: return
        added_count = 0
        current_playlist = self.playlist_data.get(self.current_category)
        is_system_playlist = self.current_category in ["Все треки", "Загруженное", FAVORITES_NAME]

        for path in filepaths:
            # Добавляем в "Все треки" если его там нет
            if not any(t['path'] == path for t in self.playlist_data["Все треки"]):
                metadata = self._get_track_metadata(path)
                track_data = {"name": metadata.get('title', os.path.basename(path)), "path": path, "score": 0, "cover_path": None, "play_count": 0, "album": metadata.get('album', 'Неизвестный альбом'), "artist": metadata.get('artist', 'Неизвестный исполнитель'), "duration": metadata.get('duration', 0), "date_added": time.time(), "volume_multiplier": 1.0}
                self.playlist_data["Все треки"].append(track_data)
                added_count += 1
                # Если текущий плейлист не системный, добавляем трек и в него
                if not is_system_playlist and not any(t['path'] == path for t in current_playlist):
                    current_playlist.append(track_data)
            # Если трек уже есть в "Всех треках", но не в текущем (пользовательском) плейлисте
            elif not is_system_playlist and not any(t['path'] == path for t in current_playlist):
                # Находим данные трека и добавляем
                track_data = next((t for t in self.playlist_data["Все треки"] if t['path'] == path), None)
                if track_data:
                    current_playlist.append(track_data)

        if added_count > 0:
            messagebox.showinfo("Треки добавлены", f"{added_count} новых трек(ов) успешно добавлено в медиатеку.")
        
        # Обновляем вид в любом случае, так как пользовательский плейлист мог измениться
        self.view_cache.clear() # Проще всего очистить весь кеш
        self.show_view(f"playlist_{self.current_category}")
        data_manager.save_playlist(self.playlist_data)


    def add_downloaded_track(self, file_path, cover_path=None):
        """Обрабатывает трек, скачанный через поиск."""
        metadata = self._get_track_metadata(file_path)
        track_data = {
            "name": metadata.get('title', os.path.basename(file_path)),
            "path": file_path,
            "cover_path": cover_path,
            "album": metadata.get('album', 'Неизвестный альбом'),
            "artist": metadata.get('artist', 'Неизвестный исполнитель'),
            "duration": metadata.get('duration', 0),
            "date_added": time.time(),
            "score": 0,
            "play_count": 0,
            "volume_multiplier": 1.0
        }

        # Добавляем в "Загруженное" и "Все треки"
        for category_name in ["Все треки", "Загруженное"]:
            if not any(t['path'] == file_path for t in self.playlist_data[category_name]):
                self.playlist_data[category_name].append(track_data)
        
        # Сбрасываем кеш для этих плейлистов, чтобы они обновились
        self.view_cache.pop(f"playlist_Все треки", None)
        self.view_cache.pop(f"playlist_Загруженное", None)

        # Если пользователь смотрит один из этих плейлистов, обновляем вид
        if self.current_category in ["Все треки", "Загруженное"]:
            self.show_view(f"playlist_{self.current_category}")
        
        data_manager.save_playlist(self.playlist_data)
        messagebox.showinfo("Загрузка завершена", f"Трек '{track_data['name']}' добавлен в 'Загруженное'.")


    def add_track(self):
        filepaths = filedialog.askopenfilenames(filetypes=(("Аудиофайлы", "*.mp3 *.wav *.ogg *.flac"), ("Все файлы", "*.*")))
        if filepaths: self.add_tracks_by_path(filepaths)

    def remove_tracks(self, indices_to_remove):
        if not indices_to_remove or not self.current_content_frame: return

        current_playlist_view = self.playlist_data[self.current_category]
        tracks_to_remove_info = [current_playlist_view[i] for i in indices_to_remove]
        
        track_names = "\n".join([f"- {t['name']}" for t in tracks_to_remove_info[:5]])
        if len(tracks_to_remove_info) > 5: track_names += "\n..."
        
        is_all_tracks = self.current_category == "Все треки"
        msg = (f"Вы уверены, что хотите удалить следующие треки из ВСЕХ плейлистов и с диска?\n\n{track_names}\n\nЭто действие необратимо." 
               if is_all_tracks else 
               f"Вы уверены, что хотите удалить следующие треки из плейлиста '{self.current_category}'?\n\n{track_names}")

        if not messagebox.askyesno("Подтверждение удаления", msg): return

        paths_to_remove = {t['path'] for t in tracks_to_remove_info}

        if is_all_tracks:
            for path in paths_to_remove:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        base, _ = os.path.splitext(path)
                        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                            cover = base + ext
                            if os.path.exists(cover): os.remove(cover)
                    except OSError as e:
                        messagebox.showerror("Ошибка", f"Не удалось удалить файл трека: {e}")

            self.view_cache.clear() 
            for cat in list(self.playlist_data.keys()):
                self.playlist_data[cat] = [t for t in self.playlist_data[cat] if t.get('path') not in paths_to_remove]
        else:
            self.playlist_data[self.current_category] = [t for t in current_playlist_view if t.get('path') not in paths_to_remove]
            if f"playlist_{self.current_category}" in self.view_cache:
                del self.view_cache[f"playlist_{self.current_category}"]

        self.stop()
        self.show_view(f"playlist_{self.current_category}")
        data_manager.save_playlist(self.playlist_data)


    def select_and_play(self, index):
        if self.current_content_frame:
            self.current_content_frame.clear_selection()
            self.current_content_frame.add_to_selection(index)
        self.current_track_index = index
        self.play_track()
        if self.current_content_frame:
            self.current_content_frame.update_active_track_highlight()

    def play_track(self, start_time=0):
        self.is_previewing = False
        if self.current_track_index == -1: self.stop(); return

        current_playlist = self.playlist_data.get(self.current_category, [])
        if not (0 <= self.current_track_index < len(current_playlist)): self.stop(); return

        track_info = current_playlist[self.current_track_index]
        track_path = track_info.get('path')

        try:
            pygame.mixer.music.load(track_path)

            if not track_info.get('duration'):
                 metadata = self._get_track_metadata(track_path)
                 track_info.update(metadata)
                 for category in self.playlist_data.values():
                     for track in category:
                         if track.get('path') == track_path:
                             track.update(metadata)

            self.current_song_length = track_info.get('duration', 0)
            self.last_seek_position = start_time

            # --- ИЗМЕНЕНИЕ: Логика увеличения play_count отсюда УДАЛЕНА ---
            # Сразу обновляем информацию на плеере
            self.player_bar.update_track_info_display(track_info)

            vol_mult = track_info.get('volume_multiplier', 1.0)
            effective_volume = self.last_volume * vol_mult
            pygame.mixer.music.set_volume(min(effective_volume, 1.0))

            pygame.mixer.music.play(start=start_time)
            self.is_playing, self.is_paused = True, False
            self.player_bar.update_play_pause_button(True)
            self.player_bar.update_fav_button_status()
        except pygame.error as e:
            messagebox.showerror("Ошибка", f"Не удалось воспроизвести: {e}")
            self.is_playing = False

    def stop(self):
        pygame.mixer.music.stop()
        self.is_playing, self.is_paused = False, False
        self.current_track_index = -1

        self.player_bar.clear_track_info()
        self.player_bar.update_play_pause_button(False)
        self.player_bar.reset_progress()

        if self.current_content_frame:
            self.current_content_frame.update_active_track_highlight()


    def play_pause(self):
        # Если ничего не выбрано и не на паузе - ничего не делаем
        if self.current_track_index == -1 and not self.is_paused:
             # Может быть, стоит начать играть первый трек? Пока нет.
            return

        # Если музыка уже играет (или превью)
        if self.is_playing or self.is_previewing:
            if self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.player_bar.update_play_pause_button(True)
            else:
                pygame.mixer.music.pause()
                self.is_paused = True
                self.player_bar.update_play_pause_button(False)
        # Если музыка не играет, но трек выбран (например, после паузы и стопа)
        elif self.current_track_index != -1:
            self.play_track()

    def next_track(self):
        track_list = self.playlist_data.get(self.current_category, [])
        if not track_list: return
        data_manager.save_playlist(self.playlist_data)
        
        if self.is_recommend_mode:
            new_index = self._get_recommended_track_index()
        elif self.is_shuffle:
            new_index = random.randint(0, len(track_list) - 1)
        else:
            new_index = (self.current_track_index + 1) % len(track_list)
        
        self.select_and_play(new_index)

    def prev_track(self):
        track_list = self.playlist_data.get(self.current_category, [])
        if not track_list: return
        data_manager.save_playlist(self.playlist_data)
        
        current_pos = self.last_seek_position + (pygame.mixer.music.get_pos() / 1000)
        if current_pos > 3:
            self.select_and_play(self.current_track_index)
        else:
            new_index = (self.current_track_index - 1) % len(track_list)
            self.select_and_play(new_index)

    def update_progress(self):
        current_pos = 0
        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        if self.is_playing and not self.is_paused:
            is_busy = pygame.mixer.music.get_busy()

            if self.current_song_length > 0 and not self.seeking:
                current_pos = self.last_seek_position + (pygame.mixer.music.get_pos() / 1000)
                if current_pos > self.current_song_length:
                    current_pos = self.current_song_length
                self.player_bar.update_progress_slider(current_pos, self.current_song_length)

            if not is_busy and not self.seeking:
                if self.current_song_length > 0 and (current_pos / self.current_song_length) > 0.6:
                    if 0 <= self.current_track_index < len(self.playlist_data[self.current_category]):
                        track_info = self.playlist_data[self.current_category][self.current_track_index]
                        track_path = track_info.get('path')

                        for category in self.playlist_data.values():
                            for track in category:
                                if track.get('path') == track_path:
                                    track['play_count'] = track.get('play_count', 0) + 1

                        self.player_bar.update_track_info_display(track_info)

                self.last_seek_position = 0
                if self.is_repeat:
                    self.play_track()
                else:
                    self.next_track()

    def on_slider_press(self, event): self.seeking = True
    def on_slider_drag(self, value_str):
        if self.seeking and self.current_song_length > 0:
            seek_time = self.current_song_length * (float(value_str) / 100)
            self.player_bar.update_current_time_label(seek_time)

    def on_slider_seek_release(self, event):
        self.after(50, self._perform_seek)
        
    def _perform_seek(self):
        if not self.seeking: return
        self.seeking = False
        if (self.is_playing or self.is_previewing or self.is_paused) and self.current_song_length > 0:
            value = self.player_bar.progress_slider.get()
            seek_time = self.current_song_length * (value / 100)
            self.last_seek_position = seek_time
            
            if self.is_previewing:
                 pygame.mixer.music.play(start=seek_time)
            else:
                 self.play_track(start_time=seek_time)
                 if self.is_paused:
                     pygame.mixer.music.pause()

    def set_theme(self, theme_name):
        if self.theme_name != theme_name:
            self.theme_name = theme_name
            self.view_cache.clear() 
            self.apply_theme()
            self.save_current_config()
            if self.current_content_frame:
                self.show_view(self.current_content_frame.view_id)

    def open_theme_editor(self, theme_name_to_edit=None):
        """Открывает окно редактора тем."""
        theme_data_to_edit = None
        if theme_name_to_edit:
            theme_data_to_edit = self.THEMES.get(theme_name_to_edit)

        # Передаем колбэк-функцию в редактор
        ThemeEditor(self, self._on_theme_editor_close, 
                    theme_name=theme_name_to_edit, 
                    theme_data=theme_data_to_edit)
    def _on_theme_editor_close(self, old_name, new_name, new_data):
        """Колбэк, который вызывается после закрытия редактора тем."""
        if not new_name or not new_data:
            return # Пользователь нажал "Отмена"

        # Если имя было изменено и старое имя не было системным, удаляем старую тему
        if old_name and old_name != new_name and old_name not in theme_manager.get_default_themes():
            if old_name in self.THEMES:
                del self.THEMES[old_name]

        self.THEMES[new_name] = new_data
        theme_manager.save_themes(self.THEMES)

        # Перезагружаем темы из файла, чтобы убедиться в консистентности
        self.THEMES = theme_manager.load_themes()

        # Обновляем вид и сразу применяем новую тему
        self.set_theme(new_name)


    def set_volume(self, value, from_start=False):
        volume_percent = float(value) / 100
        if not from_start:
            self.last_volume = volume_percent
            
        effective_volume = self.last_volume
        if self.is_playing and self.current_track_index != -1 and self.playlist_data.get(self.current_category):
            track_info = self.playlist_data[self.current_category][self.current_track_index]
            effective_volume *= track_info.get('volume_multiplier', 1.0)
            
        pygame.mixer.music.set_volume(min(effective_volume, 1.0))
        
        self.player_bar.volume_slider.set(value)
        self.player_bar.update_mute_button_status(volume_percent > 0)

    def toggle_mute(self):
        current_volume = self.player_bar.volume_slider.get()
        if current_volume > 0:
            self._unmuted_volume = current_volume
            self.set_volume(0)
        else:
            self.set_volume(getattr(self, '_unmuted_volume', 100.0))
        
    def _get_track_metadata(self, path):
        metadata = {}
        try:
            audio = mutagen.File(path, easy=True)
            if audio is None: raise mutagen.MutagenError("Не удалось прочитать теги")
            metadata['duration'] = audio.info.length
            if 'title' in audio: metadata['title'] = audio['title'][0]
            if 'artist' in audio: metadata['artist'] = audio['artist'][0]
            if 'album' in audio: metadata['album'] = audio['album'][0]
        except Exception:
            try:
                sound = self.pygame.mixer.Sound(path)
                metadata['duration'] = sound.get_length()
            except self.pygame.error:
                metadata['duration'] = 0
        return metadata

    def change_album_art(self, album_name):
        new_cover_path = filedialog.askopenfilename(
            title=f"Выберите обложку для альбома '{album_name}'",
            filetypes=(("Изображения", "*.jpg *.jpeg *.png"), ("Все файлы", "*.*"))
        )
        if not new_cover_path: return

        for category in self.playlist_data.values():
            for track in category:
                if track.get('album') == album_name:
                    track['cover_path'] = new_cover_path
                    
        data_manager.save_playlist(self.playlist_data)
        
        self.view_cache.clear()
        if self.current_content_frame:
            self.show_view(self.current_content_frame.view_id)


    def set_track_volume(self, indices):
        if len(indices) != 1: return
        track_info = self.playlist_data[self.current_category][indices[0]]
        
        dialog = VolumeDialog(self.master, track_info.get('volume_multiplier', 1.0))
        new_multiplier = dialog.result
        
        if new_multiplier is not None:
            track_path = track_info.get('path')
            for category in self.playlist_data.values():
                for track in category:
                    if track.get('path') == track_path:
                        track['volume_multiplier'] = new_multiplier

            if self.current_track_index == indices[0]:
                self.set_volume(self.player_bar.volume_slider.get())
            
            data_manager.save_playlist(self.playlist_data)
    
    def add_tracks_to_playlist(self, indices_to_add):
        if not indices_to_add: return

        user_playlists = [name for name in self.playlist_data.keys() if name not in ["Все треки", "Загруженное", FAVORITES_NAME]]

        if not user_playlists:
            messagebox.showinfo("Информация", "Сначала создайте плейлист, чтобы добавить в него треки.")
            return

        # --- ИЗМЕНЕНИЕ: Используем новый диалог вместо CTkInputDialog ---
        dialog = SelectPlaylistDialog(self, title="Добавить в плейлист", playlist_names=user_playlists)
        playlist_name = dialog.result

        if playlist_name and playlist_name in self.playlist_data:
            tracks_to_add = [self.playlist_data[self.current_category][i] for i in indices_to_add]
            target_playlist = self.playlist_data[playlist_name]
            added_count = 0

            for track in tracks_to_add:
                if not any(t['path'] == track['path'] for t in target_playlist):
                    target_playlist.append(track)
                    added_count += 1

            if added_count > 0:
                if f"playlist_{playlist_name}" in self.view_cache:
                    del self.view_cache[f"playlist_{playlist_name}"]
                data_manager.save_playlist(self.playlist_data)
                messagebox.showinfo("Успешно", f"{added_count} трек(ов) добавлено в '{playlist_name}'.")
            else:
                messagebox.showinfo("Информация", "Все выбранные треки уже есть в этом плейлисте.")
        elif playlist_name:
            # Эта ветка теперь маловероятна, но оставляем на всякий случай
            messagebox.showerror("Ошибка", f"Плейлист '{playlist_name}' не найден.")

    def add_category(self, new_cat_name):
        if new_cat_name and new_cat_name not in self.playlist_data:
            self.playlist_data[new_cat_name] = []
            self.sidebar.update_playlist_list(list(self.playlist_data.keys()))
            self.sidebar.select_playlist_button(new_cat_name)
            data_manager.save_playlist(self.playlist_data)
        elif not new_cat_name:
            messagebox.showwarning("Ошибка", "Имя категории не может быть пустым.")
        else:
            messagebox.showwarning("Ошибка", f"Категория '{new_cat_name}' уже существует.")

    def delete_category(self, cat_to_delete):
        if cat_to_delete in ["Все треки", "Загруженное", FAVORITES_NAME]:
            messagebox.showerror("Ошибка", f"Нельзя удалить системную категорию '{cat_to_delete}'."); return
        
        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить плейлист '{cat_to_delete}'? Треки останутся в медиатеке."):
            if f"playlist_{cat_to_delete}" in self.view_cache:
                del self.view_cache[f"playlist_{cat_to_delete}"]
            
            del self.playlist_data[cat_to_delete]
            
            self.sidebar.update_playlist_list(list(self.playlist_data.keys()))
            self.sidebar.select_playlist_button("Все треки")
            data_manager.save_playlist(self.playlist_data)
            
    def toggle_shuffle(self): self.is_shuffle = not self.is_shuffle; self.player_bar.update_mode_buttons()
    def toggle_repeat(self): self.is_repeat = not self.is_repeat; self.player_bar.update_mode_buttons()
    def toggle_recommend_mode(self): self.is_recommend_mode = not self.is_recommend_mode; self.player_bar.update_mode_buttons()
        
    def _get_recommended_track_index(self):
        track_list = self.playlist_data.get(self.current_category, [])
        if not track_list: return -1
        
        weights = [max(0.1, 10 + track.get('score', 0)) for track in track_list]
        
        try:
            chosen_track = random.choices(track_list, weights=weights, k=1)[0]
            return track_list.index(chosen_track)
        except IndexError:
            return 0 if track_list else -1
        
    def toggle_favorite(self):
        if self.current_track_index == -1: return
        
        track_info = dict(self.playlist_data[self.current_category][self.current_track_index])
        fav_list = self.playlist_data.get(FAVORITES_NAME, [])
        
        found_track_in_fav = -1
        for i, fav_track in enumerate(fav_list):
            if fav_track['path'] == track_info['path']:
                found_track_in_fav = i
                break
        
        if found_track_in_fav != -1:
            fav_list.pop(found_track_in_fav)
        else:
            fav_list.append(track_info)
        
        if f"playlist_{FAVORITES_NAME}" in self.view_cache:
            del self.view_cache[f"playlist_{FAVORITES_NAME}"]
        
        if self.current_category == FAVORITES_NAME:
            self.show_view(f"playlist_{FAVORITES_NAME}")
            
        data_manager.save_playlist(self.playlist_data)
        self.player_bar.update_fav_button_status()


    def _rate_track(self, value):
        if self.current_track_index == -1: return
        current_path = self.playlist_data[self.current_category][self.current_track_index]['path']

        for category in self.playlist_data:
            for track in self.playlist_data[category]:
                if track.get('path') == current_path:
                    track['score'] = track.get('score', 0) + value

        data_manager.save_playlist(self.playlist_data)
        
        current_track_info = self.playlist_data[self.current_category][self.current_track_index]
        self.player_bar.update_track_info_display(current_track_info)

    def like_track(self): self._rate_track(1)
    def dislike_track(self): self._rate_track(-1)