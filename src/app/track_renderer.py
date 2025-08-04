# app/track_renderer.py
import customtkinter as ctk
import time
import datetime
import itertools
from PIL import Image, ImageDraw
from functools import partial
from .ui_components import Tooltip, _adjust_color_brightness

class TrackRenderer:
    def __init__(self, controller, parent_frame, fonts, image_cache):
        self.controller = controller
        self.parent_frame = parent_frame
        self.fonts = fonts
        self.image_cache = image_cache
        self.placeholder_img = None
        self.track_widgets = []
        self.rendered_items_count = 0
        self.CHUNK_SIZE = 50
        self._lazy_load_job = None
        
        self.get_sorted_data = lambda: []
        self.get_original_tracks = lambda: []
        self.handle_track_click = lambda e, i: None
        self.show_context_menu = lambda e: None
        self.group_by_album = False
        self.dynamic_column_key = 'date_added'

    def render(self):
        for item in self.track_widgets: item['widget'].destroy()
        self.track_widgets.clear()
        self.rendered_items_count = 0
        if self.group_by_album:
            self._render_album_grouped(self.get_original_tracks())
        else:
            self._render_chunk(self.get_original_tracks())

    def _on_scroll(self, *args):
        self.parent_frame._parent_canvas.yview(*args)
        if self.parent_frame._scrollbar.get()[1] > 0.9 and self._lazy_load_job is None and not self.group_by_album:
            self._lazy_load_job = self.parent_frame.after(50, self._render_chunk, self.get_original_tracks())

    def _render_chunk(self, original_tracks):
        start, end = self.rendered_items_count, min(self.rendered_items_count + self.CHUNK_SIZE, len(self.get_sorted_data()))
        if start >= end: self._lazy_load_job = None; return
        for i in range(start, end):
            track_data = self.get_sorted_data()[i]
            original_index = original_tracks.index(track_data)
            widget = self._create_track_widget(self.parent_frame, track_data, original_index, display_index=i + 1)
            widget.pack(fill="x", pady=1, padx=5)
            self.track_widgets.append({'widget': widget, 'original_index': original_index})
        self.rendered_items_count = end
        self._lazy_load_job = None

    def _render_album_grouped(self, original_tracks):
        album_key = lambda t: t.get('album', 'Неизвестный альбом')
        for album_name, track_group in itertools.groupby(self.get_sorted_data(), key=album_key):
            track_list_for_album = list(track_group)
            banner = self._create_album_banner_widget(self.parent_frame, track_list_for_album[0])
            banner.pack(fill="x", pady=(15, 5), padx=5)
            self.track_widgets.append({'widget': banner, 'original_index': -1})
            for track_data in track_list_for_album:
                original_index = original_tracks.index(track_data)
                widget = self._create_track_widget(self.parent_frame, track_data, original_index)
                widget.pack(fill="x", pady=1, padx=5)
                self.track_widgets.append({'widget': widget, 'original_index': original_index})

    def _truncate_text(self, text, font, max_width):
        if font.measure(text) <= max_width: return text, None
        original_text = text
        while font.measure(text + "...") > max_width and len(text) > 0: text = text[:-1]
        return text + "...", original_text

    def _create_album_banner_widget(self, parent, track_data):
        colors = self.controller.THEMES[self.controller.theme_name]
        banner = ctk.CTkFrame(parent, fg_color=_adjust_color_brightness(colors['frame'], 0.8), height=120, corner_radius=8)
        banner.grid_columnconfigure(1, weight=1)
        cover_img = self._get_cached_image(track_data.get('cover_path'), size=(100, 100))
        cover_label = ctk.CTkLabel(banner, text="", image=cover_img, corner_radius=6)
        cover_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        info_frame = ctk.CTkFrame(banner, fg_color="transparent")
        info_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(info_frame, text=track_data.get('album', ''), font=self.fonts['album_banner'], text_color=colors['text_bright'], anchor="sw").pack(side="top", anchor="w", expand=True)
        ctk.CTkLabel(info_frame, text=track_data.get('artist', ''), font=self.fonts['track_title'], text_color=colors['text_dim'], anchor="nw").pack(side="bottom", anchor="w", expand=True)
        return banner

    def _create_track_widget(self, parent, track_data, original_index, display_index=None):
        colors = self.controller.THEMES[self.controller.theme_name]
        row_frame = ctk.CTkFrame(parent, fg_color="transparent", height=56)
        
        row_frame.grid_columnconfigure(1, weight=5) # Name/Artist
        row_frame.grid_columnconfigure(2, weight=4) # Album
        row_frame.grid_columnconfigure(3, weight=3) # Dynamic column
        row_frame.grid_columnconfigure(4, weight=1) # Duration

        idx_text = str(display_index) if display_index is not None else '•'
        index_label = ctk.CTkLabel(row_frame, text=idx_text, font=self.fonts['artist'], text_color=colors['text_dim'], width=35)
        index_label.grid(row=0, column=0, rowspan=2, padx=(5,0))

        cover_container = ctk.CTkFrame(row_frame, fg_color="transparent")
        cover_container.grid(row=0, column=1, rowspan=2, sticky="w")
        cover_img = self._get_cached_image(track_data.get('cover_path'))
        cover_label = ctk.CTkLabel(cover_container, text="", image=cover_img, width=48); cover_label.pack(side="left")
        
        info_frame = ctk.CTkFrame(cover_container, fg_color="transparent")
        info_frame.pack(side="left", padx=10)
        
        truncated_title, full_title = self._truncate_text(track_data.get('name', ''), self.fonts['track_title'], 250)
        title_label = ctk.CTkLabel(info_frame, text=truncated_title, font=self.fonts['track_title'], text_color=colors['text_bright'], anchor="w")
        title_label.pack(anchor="w")
        if full_title: Tooltip(title_label, full_title)
        
        truncated_artist, full_artist = self._truncate_text(track_data.get('artist', ''), self.fonts['artist'], 250)
        artist_label = ctk.CTkLabel(info_frame, text=truncated_artist, font=self.fonts['artist'], text_color=colors['text_dim'], anchor="w")
        artist_label.pack(anchor="w")
        if full_artist: Tooltip(artist_label, full_artist)

        truncated_album, full_album = self._truncate_text(track_data.get('album', ''), self.fonts['artist'], 180)
        album_label = ctk.CTkLabel(row_frame, text=truncated_album, text_color=colors['text_dim'], font=self.fonts['artist'], anchor="w")
        album_label.grid(row=0, column=2, rowspan=2, sticky="w", padx=10)
        if full_album: Tooltip(album_label, full_album)

        key = self.dynamic_column_key
        if key == 'date_added': dynamic_text = datetime.datetime.fromtimestamp(track_data.get(key, 0)).strftime('%d %b %Y')
        else: dynamic_text = str(track_data.get(key, ''))
        truncated_dynamic, full_dynamic = self._truncate_text(dynamic_text, self.fonts['artist'], 120)
        dynamic_label = ctk.CTkLabel(row_frame, text=truncated_dynamic, text_color=colors['text_dim'], font=self.fonts['artist'], anchor="w")
        dynamic_label.grid(row=0, column=3, rowspan=2, sticky="w", padx=10)
        if full_dynamic: Tooltip(dynamic_label, full_dynamic)

        duration_str = time.strftime('%M:%S', time.gmtime(track_data.get('duration', 0)))
        ctk.CTkLabel(row_frame, text=duration_str, text_color=colors['text_dim'], font=self.fonts['artist']).grid(row=0, column=4, rowspan=2, padx=10)
        
        def on_enter(e):
            if original_index not in self.controller.current_content_frame.selected_indices: row_frame.configure(fg_color=colors['frame_secondary'])
        def on_leave(e):
            if original_index not in self.controller.current_content_frame.selected_indices: row_frame.configure(fg_color='transparent')
        
        all_widgets_in_row = [row_frame, index_label, title_label, artist_label, album_label, dynamic_label, cover_container, cover_label, info_frame]
        for widget in all_widgets_in_row:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", lambda e, i=original_index: self.handle_track_click(e, i))
            widget.bind("<Button-3>", self.show_context_menu)
        return row_frame

    def _get_cached_image(self, path, size=(48, 48)):
        if not path or not os.path.exists(path): return self.placeholder_img
        cache_key = f"{path}_{size[0]}"
        if cache_key in self.image_cache: return self.image_cache[cache_key]
        try:
            img = Image.open(path)
            ctk_img = ctk.CTkImage(light_image=img, size=size)
            self.image_cache[cache_key] = ctk_img
            return ctk_img
        except Exception:
            return self.placeholder_img