# --- ФАЙЛ: app/ui_panels.py (ФИНАЛЬНАЯ ВЕРСИЯ) ---

import customtkinter as ctk
from tkinter import messagebox, Menu
from functools import partial
import os
import time
import datetime
import itertools
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont

from .ui_components import Tooltip, _adjust_color_brightness
from .ui_components import Tooltip, _adjust_color_brightness
from . import search, theme_manager
from .data_manager import FAVORITES_NAME

def _apply_text_hover_effect(button, dim_color, bright_color):
    button.bind("<Enter>", lambda e: button.configure(text_color=bright_color), add="+")
    button.bind("<Leave>", lambda e: button.configure(text_color=dim_color), add="+")

class SortMenu(ctk.CTkToplevel):
    def __init__(self, master, options, callback):
        super().__init__(master)
        self.callback = callback
        self.overrideredirect(True)
        colors = master.controller.THEMES[master.controller.theme_name]
        self.frame = ctk.CTkFrame(self, corner_radius=6, border_width=1, border_color=colors['frame_secondary'])
        self.frame.pack()
        for key, name in options.items():
            btn = ctk.CTkButton(self.frame, text=name, anchor="w", fg_color="transparent", hover_color=colors['accent'], command=lambda k=key: self._on_select(k))
            btn.pack(fill="x", padx=5, pady=2)
        self.bind("<FocusOut>", lambda e: self.destroy())
        self.after(100, self.focus_set)

    def _on_select(self, key):
        self.callback(key)
        self.destroy()

# =============================================================================
# КЛАСС SIDEBARFRAME
# =============================================================================
class SidebarFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        self.controller = kwargs.pop("controller")
        super().__init__(master, **kwargs)
        self.theme_colors = self.controller.THEMES[self.controller.theme_name]
        self.playlist_buttons = {}
        self.current_nav_button = None
        self.current_playlist_button = None
        self.grid_rowconfigure(2, weight=1)

        # --- ВОССТАНОВЛЕННЫЙ БЛОК СОЗДАНИЯ ВИДЖЕТОВ ---
        self.logo_label = ctk.CTkLabel(self, text="RaZ Player", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=20)

        self.nav_container = ctk.CTkFrame(self, corner_radius=8)
        self.nav_container.grid(row=1, column=0, sticky="nsew", padx=10)

        self.library_button = ctk.CTkButton(self.nav_container, text="Моя медиатека", anchor="w", command=self.on_library_click)
        self.library_button.pack(fill="x", pady=5, padx=5)

        self.search_button = ctk.CTkButton(self.nav_container, text="Поиск", anchor="w", command=self.on_search_click)
        self.search_button.pack(fill="x", pady=(0,5), padx=5)

        self.themes_button = ctk.CTkButton(self.nav_container, text="Темы", anchor="w", command=self.on_themes_click)
        self.themes_button.pack(fill="x", pady=(0,5), padx=5)

        self.playlist_container = ctk.CTkFrame(self, corner_radius=8)
        self.playlist_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.playlist_container.grid_rowconfigure(1, weight=1)
        self.playlist_container.grid_columnconfigure(0, weight=1)

        self.playlist_header_frame = ctk.CTkFrame(self.playlist_container, fg_color="transparent")
        self.playlist_header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5,0))
        self.playlist_header_frame.grid_columnconfigure(0, weight=1)

        self.playlist_label = ctk.CTkLabel(self.playlist_header_frame, text="ПЛЕЙЛИСТЫ", font=ctk.CTkFont(weight="bold"))
        self.playlist_label.grid(row=0, column=0, sticky="")

        self.add_playlist_button_small = ctk.CTkButton(self.playlist_header_frame, text="+", width=28, height=28, command=self.show_add_playlist_dialog)
        self.add_playlist_button_small.grid(row=0, column=1, sticky="e")

        self.playlists_scroll_frame = ctk.CTkScrollableFrame(self.playlist_container, label_text="")
        self.playlists_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def apply_theme(self, colors):
        self.theme_colors = colors
        self.configure(fg_color=colors["frame"])
        self.logo_label.configure(text_color=colors["text_bright"])

        is_dark = colors.get("bg", "#000000") < "#888888"
        secondary_color = _adjust_color_brightness(colors["frame"], 1.1 if is_dark else 0.95)

        self.nav_container.configure(fg_color=secondary_color)
        self.playlist_container.configure(fg_color=secondary_color)
        self.playlist_label.configure(text_color=colors["text_dim"])
        self.add_playlist_button_small.configure(fg_color=colors["accent"], text_color=colors["text_on_accent"], hover_color=colors["hover"])

        self.playlists_scroll_frame.configure(label_text="", fg_color="transparent", scrollbar_button_color=colors.get("accent"), scrollbar_button_hover_color=colors.get("hover"))
        if hasattr(self.playlists_scroll_frame, "_scrollbar"):
            self.playlists_scroll_frame._scrollbar.configure(button_color=colors.get("accent"), button_hover_color=colors.get("hover"))

        all_buttons = list(self.playlist_buttons.values()) + [self.library_button, self.search_button, self.themes_button]
        for btn in all_buttons:
            if btn.winfo_exists():
                is_nav_selected = (self.current_nav_button == btn)
                is_playlist_selected = (self.current_playlist_button == btn)
                self.apply_theme_to_button(btn, is_selected=(is_nav_selected or is_playlist_selected))

    def apply_theme_to_button(self, btn, is_selected):
        colors = self.theme_colors; is_dark = colors.get("bg", "#000000") < "#888888"
        container_bg_color = _adjust_color_brightness(colors["frame"], 1.1 if is_dark else 0.95)
        hover_color = _adjust_color_brightness(container_bg_color, 1.1 if is_dark else 0.9)
        if is_selected: btn.configure(fg_color=colors["accent"], text_color=colors["text_on_accent"], hover_color=colors["hover"])
        else: btn.configure(fg_color="transparent", text_color=colors["text"], hover_color=hover_color)
        btn.configure(text_color_disabled=colors["text_dim"])

    def update_playlist_list(self, categories):
        self.current_playlist_button = None
        for btn in self.playlist_buttons.values(): btn.destroy()
        self.playlist_buttons.clear()
        system_cats = ["Все треки", "Загруженное", FAVORITES_NAME]
        for cat_name in system_cats:
            if cat_name in categories: self._create_playlist_button(cat_name)
        for cat_name in sorted([c for c in categories if c not in system_cats]): self._create_playlist_button(cat_name)
        if self.current_playlist_button and self.current_playlist_button.winfo_exists(): self.apply_theme_to_button(self.current_playlist_button, is_selected=True)

    def _create_playlist_button(self, name):
        btn = ctk.CTkButton(self.playlists_scroll_frame, text=name, anchor="w", command=partial(self.select_playlist_button, name))
        btn.pack(fill="x", pady=2); self.playlist_buttons[name] = btn
        self.apply_theme_to_button(btn, is_selected=False)
        if name not in ["Все треки", "Загруженное", FAVORITES_NAME]:
            btn.bind("<Button-3>", lambda event, playlist_name=name: self._show_playlist_context_menu(event, playlist_name))

    def _show_playlist_context_menu(self, event, playlist_name):
        """Создает и показывает контекстное меню для удаления плейлиста."""
        colors = self.theme_colors
        context_menu = Menu(self, tearoff=0, background=colors['frame'], foreground=colors['text'],
                            activebackground=colors['accent'], activeforeground=colors['text_on_accent'],
                            relief="flat", borderwidth=0)

        context_menu.add_command(label="Удалить плейлист", 
                                 command=lambda: self.controller.delete_category(playlist_name))

        context_menu.tk_popup(event.x_root, event.y_root)
    
    def on_library_click(self):
        self._select_nav_button(self.library_button)
        if self.current_playlist_button: self.apply_theme_to_button(self.current_playlist_button, is_selected=False)
        self.select_playlist_button(self.controller.current_category)

    def on_search_click(self):
        self._select_nav_button(self.search_button)
        if self.current_playlist_button: self.apply_theme_to_button(self.current_playlist_button, is_selected=False)
        self.current_playlist_button = None; self.controller.show_search_view()

    def on_themes_click(self):
        self._select_nav_button(self.themes_button)
        if self.current_playlist_button: self.apply_theme_to_button(self.current_playlist_button, is_selected=False)
        self.current_playlist_button = None; self.controller.show_themes_view()

    def select_playlist_button(self, name):
        if name not in self.playlist_buttons: name = "Все треки"
        self._select_nav_button(self.library_button)
        if self.current_playlist_button: self.apply_theme_to_button(self.current_playlist_button, is_selected=False)
        btn_to_select = self.playlist_buttons.get(name)
        if btn_to_select: self.apply_theme_to_button(btn_to_select, is_selected=True); self.current_playlist_button = btn_to_select
        self.controller.show_library_view(name)

    def _select_nav_button(self, button_to_select):
        if self.current_nav_button: self.apply_theme_to_button(self.current_nav_button, is_selected=False)
        self.apply_theme_to_button(button_to_select, is_selected=True); self.current_nav_button = button_to_select

    def show_add_playlist_dialog(self):
        dialog = ctk.CTkInputDialog(text="Введите название нового плейлиста:", title="Создать плейлист")
        new_name = dialog.get_input()
        if new_name: self.controller.add_category(new_name.strip())

# =============================================================================
# КЛАСС CONTENTFRAME
# =============================================================================
class ContentFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        self.controller = kwargs.pop("controller")
        super().__init__(master, **kwargs)
        
        self.view_id = None
        self.current_sort_key = 'date_added'
        self.sort_reverse = True
        self.group_by_album = False # <-- Теперь это независимый флаг
        self.dynamic_column_key = 'date_added'
        self.selected_indices = set()
        self.last_clicked_index = -1
        
        self.track_widgets = []
        self.sorted_track_data = []
        self.rendered_widget_count = 0
        self._lazy_load_job = None
        self._is_rendering = False # <-- Флаг для предотвращения "рваной" прокрутки
        self.CHUNK_SIZE = 40
        
        self.image_cache = {}
        self.placeholder_img = None
        self.edit_icon = None
        
        self.search_entry = None
        self.search_results_frame = None
        self.search_status_label = None
        
        try:
            self.fonts = {
                'track_title': ctk.CTkFont(family="Calibri", size=15),
                'artist': ctk.CTkFont(family="Calibri", size=12),
                'column_header': ctk.CTkFont(family="Calibri", size=12, weight="bold"),
                'album_banner': ctk.CTkFont(family="Calibri", size=22, weight="bold")
            }
        except Exception:
            self.fonts = {
                'track_title': ctk.CTkFont(size=15), 'artist': ctk.CTkFont(size=12),
                'column_header': ctk.CTkFont(size=12, weight="bold"),
                'album_banner': ctk.CTkFont(size=22, weight="bold")
            }
        
    def _clear_view(self):
        if self._lazy_load_job: self.after_cancel(self._lazy_load_job)
        self._lazy_load_job = None
        for widget in self.winfo_children(): widget.destroy()
        self.track_widgets.clear()
        self.sorted_track_data.clear()
        self.rendered_widget_count = 0
        
    def clear_selection(self): self.selected_indices.clear(); self.last_clicked_index = -1
    def add_to_selection(self, index): self.selected_indices.add(index); self.last_clicked_index = index

    def refresh_current_view(self):
        colors = self.controller.THEMES[self.controller.theme_name]
        self.configure(fg_color=colors["bg"])
        if self.view_id and self.view_id.startswith("playlist_"):
            category_name = self.view_id.replace("playlist_", "")
            self.display_playlist_view(category_name, self.controller.playlist_data.get(category_name, []))
        elif self.view_id == "search": self.display_search_view(force_redraw=True)
        elif self.view_id == "themes": self.display_themes_view()

    def display_playlist_view(self, category_name, tracks):
        self._clear_view()
        self.view_id = f"playlist_{category_name}"
        colors = self.controller.THEMES[self.controller.theme_name]
        self.configure(fg_color=colors["bg"])

        self._create_playlist_headers(self)
        ctk.CTkFrame(self, height=1, fg_color=colors["frame_secondary"]).pack(fill="x", padx=10, pady=(0, 5))

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color=colors.get("accent"), scrollbar_button_hover_color=colors.get("hover"))
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(fill="x", padx=10, pady=10, side="bottom")
        footer_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(footer_frame, text="Добавить трек", command=self.controller.add_track, fg_color=colors["accent"], hover_color=colors["hover"], text_color=colors["text_on_accent"]).grid(row=0, column=0, sticky="ew")

        if not tracks:
            ctk.CTkLabel(self.scroll_frame, text="В этом плейлисте пока нет треков", font=ctk.CTkFont(size=14), text_color=colors["text_dim"]).pack(expand=True, pady=50)
            return

        key_func = lambda t: (t.get(self.current_sort_key) or 0) if isinstance(t.get(self.current_sort_key, 0), (int, float)) else (t.get(self.current_sort_key) or "").lower()
        self.sorted_track_data = sorted(tracks, key=key_func, reverse=self.sort_reverse)
        
        self.scroll_frame._scrollbar.configure(command=self._on_scroll)
        
        if self.group_by_album:
            self._render_album_grouped(tracks)
        else:
            self._render_chunk(tracks)
        
        self.update_active_track_highlight()


    def _on_scroll(self, *args):
        self.scroll_frame._parent_canvas.yview(*args)

        # ИЗМЕНЕНИЕ: Отменяем предыдущий запланированный вызов, чтобы избежать их наложения
        if self._lazy_load_job:
            self.after_cancel(self._lazy_load_job)
            self._lazy_load_job = None

        # Запускаем новый вызов только если докрутили до конца и рендеринг не идет прямо сейчас
        if self.scroll_frame._scrollbar.get()[1] > 0.95 and not self.group_by_album and not self._is_rendering:
            self._lazy_load_job = self.after(50, self._render_chunk, self.controller.playlist_data[self.controller.current_category])

    def _render_chunk(self, original_tracks):
        if self._is_rendering or not self.scroll_frame.winfo_exists():
            return

        self._is_rendering = True

        start, end = self.rendered_widget_count, min(self.rendered_widget_count + self.CHUNK_SIZE, len(self.sorted_track_data))

        if start >= end:
            self._is_rendering = False
            return

        for i in range(start, end):
            track_data = self.sorted_track_data[i]
            try:
                original_index = original_tracks.index(track_data)
                widget = self._create_track_widget(self.scroll_frame, track_data, original_index, display_index=i + 1)
                widget.pack(fill="x", pady=1, padx=5)
                self.track_widgets.append({'widget': widget, 'original_index': original_index})
            except (ValueError, IndexError):
                # Пропускаем трек, если его по какой-то причине нет в оригинальном списке
                # (может случиться при очень быстрых операциях с плейлистом)
                continue
        
        self.rendered_widget_count = end

        # ИЗМЕНЕНИЕ: Принудительно обновляем UI и снимаем блокировку с небольшой задержкой,
        # чтобы дать event loop время на обработку.
        self.update()
        self.after(10, lambda: setattr(self, '_is_rendering', False))

    def _render_album_grouped(self, original_tracks):
        if self._is_rendering or not self.scroll_frame.winfo_exists(): return
        self._is_rendering = True
        album_key = lambda t: t.get('album', 'Неизвестный альбом')
        
        # Сортируем по альбому и исполнителю для логичного порядка
        sorted_for_grouping = sorted(self.sorted_track_data, key=lambda t: (t.get('album', '').lower(), t.get('artist', '').lower()))

        for album_name, track_group in itertools.groupby(sorted_for_grouping, key=album_key):
            track_list_for_album = list(track_group)
            banner = self._create_album_banner_widget(self.scroll_frame, track_list_for_album[0], track_list_for_album)
            banner.pack(fill="x", pady=(15, 5), padx=5)
            self.track_widgets.append({'widget': banner, 'original_index': -1, 'is_banner': True})
            
            for track_data in track_list_for_album:
                original_index = original_tracks.index(track_data)
                widget = self._create_track_widget(self.scroll_frame, track_data, original_index)
                widget.pack(fill="x", pady=1, padx=5)
                self.track_widgets.append({'widget': widget, 'original_index': original_index})
        
        self.update()
        self._is_rendering = False

    def _create_playlist_headers(self, parent):
        colors = self.controller.THEMES[self.controller.theme_name]
        header_frame = ctk.CTkFrame(parent, fg_color="transparent", height=30)
        header_frame.pack(fill="x", padx=15, pady=(10, 5))
        
        header_frame.grid_columnconfigure(0, weight=4, uniform="group1")
        header_frame.grid_columnconfigure(1, weight=50, uniform="group1")
        header_frame.grid_columnconfigure(2, weight=30, uniform="group1")
        header_frame.grid_columnconfigure(3, weight=20, uniform="group1")
        header_frame.grid_columnconfigure(4, weight=8, uniform="group1")
        header_frame.grid_columnconfigure(5, weight=10, uniform="group1") # Место для переключателя и ...

        # --- Кнопки сортировки ---
        col_map = {'#': ('date_added', 0), 'Название': ('name', 1), 'Альбом': ('album', 2), '🕒': ('duration', 4)}
        for text, (sort_key, col) in col_map.items():
            is_active = self.current_sort_key == sort_key
            icon = " ▲" if is_active and not self.sort_reverse else " ▼" if is_active else ""
            anchor = "w" if text not in ['#', '🕒'] else "center"
            btn = ctk.CTkButton(header_frame, text=text + icon, height=28, font=self.fonts['column_header'], anchor=anchor, fg_color="transparent", text_color=colors['accent'] if is_active else colors['text_dim'], hover_color=colors['frame_secondary'], command=partial(self.sort_playlist, sort_key))
            btn.grid(row=0, column=col, sticky="ew", padx=10 if anchor=='w' else 0)

        # --- Динамическая колонка ---
        self.all_sort_options = {'date_added': 'Дата добавления', 'artist': 'Исполнитель', 'score': 'Рейтинг', 'play_count': 'Прослушивания'}
        btn_text = self.all_sort_options[self.dynamic_column_key]
        is_active_dyn = self.current_sort_key == self.dynamic_column_key
        icon_dyn = " ▲" if is_active_dyn and not self.sort_reverse else " ▼" if is_active_dyn else ""
        self.dynamic_header_btn = ctk.CTkButton(header_frame, text=btn_text + icon_dyn, height=28, font=self.fonts['column_header'], anchor="w", fg_color="transparent", text_color=colors['accent'] if is_active_dyn else colors['text_dim'], hover_color=colors['frame_secondary'], command=partial(self.sort_playlist, self.dynamic_column_key))
        self.dynamic_header_btn.grid(row=0, column=3, sticky="ew", padx=10)

        # --- Контейнер для правых кнопок ---
        right_buttons_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_buttons_frame.grid(row=0, column=5, sticky="e")

        # --- НОВАЯ КНОПКА: Переключатель вида ---
        self.view_toggle_button = ctk.CTkButton(right_buttons_frame, text="≡" if not self.group_by_album else "🖼️", height=28, width=30, font=self.fonts['column_header'], fg_color="transparent", hover_color=colors['frame_secondary'], command=self.toggle_view_mode)
        self.view_toggle_button.pack(side="left", padx=5)
        Tooltip(self.view_toggle_button, "Переключить вид: Список / Альбомы")

        more_button = ctk.CTkButton(right_buttons_frame, text="...", height=28, width=30, font=self.fonts['column_header'], fg_color="transparent", hover_color=colors['frame_secondary'], command=self._show_dynamic_column_menu)
        more_button.pack(side="left")
        Tooltip(more_button, "Выбрать колонку для сортировки")
    
    def toggle_view_mode(self):
        self.group_by_album = not self.group_by_album
        self.refresh_current_view()

    def _show_dynamic_column_menu(self):
        x = self.dynamic_header_btn.winfo_rootx()
        y = self.dynamic_header_btn.winfo_rooty() + self.dynamic_header_btn.winfo_height()
        menu = SortMenu(self, self.all_sort_options, self._change_dynamic_column)
        menu.geometry(f"+{x}+{y}")

    def _change_dynamic_column(self, new_key):
        self.dynamic_column_key = new_key
        self.refresh_current_view()

    def sort_playlist(self, sort_key):
        if sort_key == '#': sort_key = 'date_added' # Клик по # сортирует по дате
        if self.current_sort_key == sort_key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.current_sort_key = sort_key
            self.sort_reverse = sort_key in ['date_added', 'score', 'play_count']
        
        # --- УДАЛЕНО: Группировка больше не часть сортировки ---
        # self.group_by_album = (sort_key == 'album')
        self.refresh_current_view()

    def _on_track_click(self, event, index):
        shift_pressed = (event.state & 0x0001) != 0
        ctrl_pressed = (event.state & 0x0004) != 0

        if not ctrl_pressed and not shift_pressed:
            self.clear_selection()
            self.add_to_selection(index)
        elif ctrl_pressed:
            if index in self.selected_indices: self.selected_indices.remove(index)
            else: self.add_to_selection(index)
        elif shift_pressed and self.last_clicked_index != -1:
            try:
                current_list = self.sorted_track_data
                start_item = self.controller.playlist_data[self.controller.current_category][self.last_clicked_index]
                end_item = self.controller.playlist_data[self.controller.current_category][index]
                start_idx_in_sorted = current_list.index(start_item)
                end_idx_in_sorted = current_list.index(end_item)
                if start_idx_in_sorted > end_idx_in_sorted: start_idx_in_sorted, end_idx_in_sorted = end_idx_in_sorted, start_idx_in_sorted
                
                self.clear_selection()
                for i in range(start_idx_in_sorted, end_idx_in_sorted + 1):
                    track_to_select = current_list[i]
                    original_index = self.controller.playlist_data[self.controller.current_category].index(track_to_select)
                    self.add_to_selection(original_index)
            except (ValueError, IndexError): 
                self.clear_selection(); self.add_to_selection(index)

        self.update_active_track_highlight()


    def _show_context_menu(self, event, index):
        if index not in self.selected_indices:
            self.clear_selection(); self.add_to_selection(index)
            self.update_active_track_highlight()

        indices = list(self.selected_indices)
        if not indices: return

        colors = self.controller.THEMES[self.controller.theme_name]
        context_menu = Menu(self, tearoff=0, background=colors['frame'], foreground=colors['text'], activebackground=colors['accent'], activeforeground=colors['text_on_accent'], relief="flat", borderwidth=0)
        
        context_menu.add_command(label="Проиграть", command=lambda: self.controller.select_and_play(indices[0]))
        context_menu.add_separator()
        context_menu.add_command(label="Добавить в плейлист...", command=lambda: self.controller.add_tracks_to_playlist(indices))
        if len(indices) == 1:
            context_menu.add_command(label="Настроить громкость...", command=lambda: self.controller.set_track_volume(indices))
        
        context_menu.add_separator()
        context_menu.add_command(label=f"Удалить ({len(indices)})", command=lambda: self.controller.remove_tracks(indices))
        
        context_menu.tk_popup(event.x_root, event.y_root)

    def update_active_track_highlight(self):
        if not self.winfo_exists(): return
        colors = self.controller.THEMES[self.controller.theme_name]
        is_dark = colors.get("bg", "#000000") < "#888888"
        playing_index = self.controller.current_track_index
        
        for item in self.track_widgets:
            if item.get('is_banner', False): continue
            
            idx = item['original_index']
            widget = item['widget']
            if not widget.winfo_exists(): continue

            is_playing = idx == playing_index
            is_selected = idx in self.selected_indices
            
            fg_color = 'transparent'
            if is_playing: fg_color = colors['accent']
            elif is_selected: fg_color = _adjust_color_brightness(colors['frame_secondary'], 1.2 if is_dark else 0.95)
            widget.configure(fg_color=fg_color)
            
            title_color = colors['text_on_accent'] if is_playing else colors['text_bright']
            text_color = colors['text_on_accent'] if is_playing else colors['text_dim']

            # Обновляем цвета текста для всех дочерних виджетов
            for child in widget.winfo_children():
                # Находим фрейм с названием и артистом (самый надежный способ - по наличию 2х лейблов)
                if isinstance(child, ctk.CTkFrame) and len(child.winfo_children()) > 1 and isinstance(child.winfo_children()[1], ctk.CTkFrame):
                    info_container = child.winfo_children()[1]
                    if len(info_container.winfo_children()) >= 2:
                        title_widget = info_container.winfo_children()[0]
                        artist_widget = info_container.winfo_children()[1]
                        title_widget.configure(text_color=title_color)
                        artist_widget.configure(text_color=text_color)
                elif isinstance(child, ctk.CTkLabel):
                     child.configure(text_color=text_color)

    def _get_cached_image(self, path, size=(48, 48)):
        if not path or not os.path.exists(path): return self.placeholder_img
        
        cache_key = f"{path}_{size[0]}"
        if cache_key in self.image_cache: return self.image_cache[cache_key]
        
        try:
            img = Image.open(path)
            # --- ИСПРАВЛЕНИЕ: Гарантируем RGBA для совместимости с alpha_composite ---
            ctk_img = ctk.CTkImage(light_image=img.convert("RGBA"), size=size)
            self.image_cache[cache_key] = ctk_img
            return ctk_img
        except Exception:
            return self.placeholder_img

    def _truncate_text(self, text, font, max_width):
        if not isinstance(text, str): text = str(text)
        if font.measure(text) <= max_width: return text, None
        original_text = text
        while font.measure(text + "...") > max_width and len(text) > 0: text = text[:-1]
        return text + "...", original_text

    def _create_album_banner_widget(self, parent, track_data, album_tracks):
        colors = self.controller.THEMES[self.controller.theme_name]
        banner = ctk.CTkFrame(parent, fg_color="transparent", height=120, corner_radius=8)
        banner.grid_columnconfigure(1, weight=1)

        try:
            w, h = (parent.winfo_width() or 800, 120)
            cover_img_bg = self._get_cached_image(track_data.get('cover_path'), size=(w,h))
            if cover_img_bg and hasattr(cover_img_bg, '_light_image'):
                bg_label = ctk.CTkLabel(banner, text=""); bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                source_img = cover_img_bg._light_image.resize((w,h), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(7))
                enhancer = ImageEnhance.Brightness(source_img); source_img = enhancer.enhance(0.5)
                final_bg = ctk.CTkImage(light_image=source_img, size=(w,h))
                bg_label.configure(image=final_bg)
            else:
                 banner.configure(fg_color=_adjust_color_brightness(colors['frame'], 0.8))
        except Exception as e:
            print(f"Не удалось создать фон для баннера: {e}")
            banner.configure(fg_color=_adjust_color_brightness(colors['frame'], 0.8))

        def on_banner_click(event):
            self.clear_selection(); all_tracks = self.controller.playlist_data[self.controller.current_category]
            for track in album_tracks:
                try: self.add_to_selection(all_tracks.index(track))
                except ValueError: continue
            self.update_active_track_highlight()

        banner.bind("<Button-1>", on_banner_click)
        if 'bg_label' in locals(): bg_label.bind("<Button-1>", on_banner_click)

        cover_img_fg = self._get_cached_image(track_data.get('cover_path'), size=(100, 100))
        cover_label = ctk.CTkLabel(banner, text="", image=cover_img_fg, corner_radius=6, fg_color=_adjust_color_brightness(colors['frame'], 0.5)); cover_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        hover_color = _adjust_color_brightness(colors['frame_secondary'], 1.2)
        edit_button = ctk.CTkButton(cover_label, text="", image=self.edit_icon, width=28, height=28, 
                                    fg_color="transparent", # <-- Заменено "#00000080" на "transparent"
                                    hover_color=hover_color, # <-- Добавлен цвет при наведении
                                    corner_radius=14, 
                                    command=lambda: self.controller.change_album_art(track_data.get('album')))

        def show_edit(e): edit_button.place(relx=0.5, rely=0.5, anchor="center")
        def hide_edit(e): edit_button.place_forget()

        cover_label.bind("<Enter>", show_edit); cover_label.bind("<Leave>", hide_edit)

        info_frame = ctk.CTkFrame(banner, fg_color="transparent"); info_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=10, pady=10); info_frame.bind("<Button-1>", on_banner_click)
        ctk.CTkLabel(info_frame, text=track_data.get('album', ''), font=self.fonts['album_banner'], text_color="#FFFFFF", anchor="sw").pack(side="top", anchor="w", expand=True)
        ctk.CTkLabel(info_frame, text=track_data.get('artist', ''), font=self.fonts['track_title'], text_color="#DDDDDD", anchor="nw").pack(side="bottom", anchor="w", expand=True)
        return banner
        

    def _create_track_widget(self, parent, track_data, original_index, display_index=None):
        colors = self.controller.THEMES[self.controller.theme_name]
        row_frame = ctk.CTkFrame(parent, fg_color="transparent", height=56)
        
        row_frame.grid_columnconfigure(0, weight=4, uniform="group1")
        row_frame.grid_columnconfigure(1, weight=50, uniform="group1")
        row_frame.grid_columnconfigure(2, weight=30, uniform="group1")
        row_frame.grid_columnconfigure(3, weight=20, uniform="group1")
        row_frame.grid_columnconfigure(4, weight=8, uniform="group1")
        row_frame.grid_columnconfigure(5, weight=10, uniform="group1") 

        idx_text = str(display_index) if display_index is not None else '•'
        index_label = ctk.CTkLabel(row_frame, text=idx_text, font=self.fonts['artist'], text_color=colors['text_dim'])
        index_label.grid(row=0, column=0, rowspan=2, sticky="ew")

        cover_container = ctk.CTkFrame(row_frame, fg_color="transparent")
        cover_container.grid(row=0, column=1, rowspan=2, sticky="w", padx=10)
        cover_img = self._get_cached_image(track_data.get('cover_path'))
        cover_label = ctk.CTkLabel(cover_container, text="", image=cover_img, width=48); cover_label.pack(side="left")
        
        info_frame = ctk.CTkFrame(cover_container, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=10)
        
        truncated_title, full_title = self._truncate_text(track_data.get('name', ''), self.fonts['track_title'], 250)
        title_label = ctk.CTkLabel(info_frame, text=truncated_title, font=self.fonts['track_title'], text_color=colors['text_bright'], anchor="w")
        title_label.pack(anchor="w", fill="x")
        if full_title: Tooltip(title_label, full_title)
        
        truncated_artist, full_artist = self._truncate_text(track_data.get('artist', ''), self.fonts['artist'], 250)
        artist_label = ctk.CTkLabel(info_frame, text=truncated_artist, font=self.fonts['artist'], text_color=colors['text_dim'], anchor="w")
        artist_label.pack(anchor="w", fill="x")
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
        ctk.CTkLabel(row_frame, text=duration_str, text_color=colors['text_dim'], font=self.fonts['artist']).grid(row=0, column=4, rowspan=2, padx=10, sticky="ew")
        
        is_dark = colors.get("bg", "#000000") < "#888888"
        hover_color = _adjust_color_brightness(colors['frame_secondary'], 1.1 if is_dark else 0.95)
        def on_enter(e):
            if original_index not in self.selected_indices and original_index != self.controller.current_track_index: row_frame.configure(fg_color=hover_color)
        def on_leave(e):
            if original_index not in self.selected_indices and original_index != self.controller.current_track_index: row_frame.configure(fg_color='transparent')
        
        all_widgets_in_row = [row_frame, index_label, title_label, artist_label, album_label, dynamic_label, cover_container, cover_label, info_frame]
        for widget in all_widgets_in_row:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", lambda e, i=original_index: self._on_track_click(e, i))
            widget.bind("<Double-Button-1>", lambda e, i=original_index: self.controller.select_and_play(i))
            widget.bind("<Button-3>", lambda e, i=original_index: self._show_context_menu(e, i))
            
        return row_frame
    
    # В классе ContentFrame, в конце файла:

    def display_search_view(self, force_redraw=False):
        if self.view_id == "search" and not force_redraw:
            return
        self._clear_view()
        self.view_id = "search"
        colors = self.controller.THEMES[self.controller.theme_name]
        self.configure(fg_color=colors["bg"])

        # Контейнер для поиска
        search_bar_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_bar_frame.pack(fill="x", padx=20, pady=20)
        search_bar_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(search_bar_frame, placeholder_text="Что хотите послушать?", height=40)
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<Return>", lambda event: search.start_search_thread(self.controller))

        self.search_button = ctk.CTkButton(search_bar_frame, text="Найти", height=40, command=lambda: search.start_search_thread(self.controller))
        self.search_button.grid(row=0, column=1, padx=(10, 0))

        # Настройки скачивания
        download_options_frame = ctk.CTkFrame(self, fg_color="transparent")
        download_options_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        cover_checkbox = ctk.CTkCheckBox(download_options_frame, text="Скачивать обложки", variable=self.controller.download_covers_var, onvalue=True, offvalue=False)
        cover_checkbox.pack(side="left")

        # Статус и результаты
        self.search_status_label = ctk.CTkLabel(self, text="", text_color=colors["text_dim"])
        self.search_status_label.pack(fill="x", padx=20, pady=5)

        self.search_results_frame = ctk.CTkScrollableFrame(self, fg_color=colors["frame"])
        self.search_results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def display_search_results(self):
        self.search_status_label.configure(text=f"Найдено: {len(self.controller.search_results_cache)} треков.")
        self.search_button.configure(state="normal")
        for widget in self.search_results_frame.winfo_children():
            widget.destroy()
        
        for i, track_data in enumerate(self.controller.search_results_cache):
            self.create_result_widget(self.search_results_frame, track_data, i)

    def create_result_widget(self, parent, data, row):
        colors = self.controller.THEMES[self.controller.theme_name]

        widget_frame = ctk.CTkFrame(parent, fg_color="transparent")
        widget_frame.pack(fill="x", pady=5)

        cover_label = ctk.CTkLabel(widget_frame, text="")
        cover_label.pack(side="left", padx=10)

        thumbnail_url = data.get('thumbnail')
        if thumbnail_url:
            def update_image(img):
                if img and cover_label.winfo_exists():
                    cover_label.configure(image=img)
            search.start_image_load_thread(thumbnail_url, (64, 64), update_image)

        info_frame = ctk.CTkFrame(widget_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(info_frame, text=data.get('title', 'Без названия'), anchor="w").pack(fill="x")
        ctk.CTkLabel(info_frame, text=data.get('uploader', 'Неизвестный исполнитель'), text_color=colors["text_dim"], anchor="w").pack(fill="x")

        buttons_frame = ctk.CTkFrame(widget_frame, fg_color="transparent")
        buttons_frame.pack(side="right", padx=10)

        # --- ИЗМЕНЕНИЕ: Кнопка предпрослушивания и её логика полностью удалены ---
        download_btn = ctk.CTkButton(buttons_frame, text="⏬", width=40, 
                                     command=lambda: search.start_download_thread(self.controller, data, download_btn))
        download_btn.pack(side="left", padx=5)

    def display_themes_view(self):
        self._clear_view()
        self.view_id = "themes"
        colors = self.controller.THEMES[self.controller.theme_name]
        self.configure(fg_color=colors["bg"])

        ctk.CTkLabel(self, text="Темы оформления", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20, padx=20, anchor="w")

        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=0)

        default_themes = theme_manager.get_default_themes()

        for theme_name, theme_colors in self.controller.THEMES.items():
            border_color_inactive = colors["bg"] 
            theme_card = ctk.CTkFrame(scroll_frame, border_width=2, 
                                      border_color=theme_colors["accent"] if self.controller.theme_name == theme_name else border_color_inactive)
            theme_card.pack(fill="x", pady=10, padx=10)

            # --- ИЗМЕНЕНИЕ: Добавляем кнопку редактирования для кастомных тем ---
            if theme_name not in default_themes:
                edit_button = ctk.CTkButton(theme_card, text="✎", font=ctk.CTkFont(size=20), width=40,
                                            fg_color="transparent", hover_color=colors["frame_secondary"],
                                            command=partial(self.controller.open_theme_editor, theme_name))
                edit_button.pack(side="right", fill="y", padx=5, pady=5)

            card_button = ctk.CTkButton(theme_card, text=theme_name, height=60, 
                                        fg_color=theme_colors["frame"],
                                        hover_color=theme_colors["hover"],
                                        text_color=theme_colors["text_bright"],
                                        command=partial(self.controller.set_theme, theme_name))
            card_button.pack(fill="both", expand=True, padx=5, pady=5)

        add_theme_card = ctk.CTkFrame(scroll_frame, fg_color="transparent", border_width=2, border_color=colors["frame_secondary"], corner_radius=12)
        add_theme_card.pack(fill="x", pady=10, padx=10)

        # Вызываем редактор для создания НОВОЙ темы (без аргументов)
        add_theme_button = ctk.CTkButton(add_theme_card, text="+", height=60,
                                         font=ctk.CTkFont(size=30),
                                         fg_color="transparent",
                                         hover_color=colors["frame_secondary"],
                                         text_color=colors["text_dim"],
                                         command=self.controller.open_theme_editor)
        add_theme_button.pack(fill="both", expand=True, padx=5, pady=5)

class PlayerControlFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        self.controller = kwargs.pop("controller")
        super().__init__(master, **kwargs)
        
        self.theme_colors = self.controller.THEMES[self.controller.theme_name]
        self.placeholder_image = ctk.CTkImage(light_image=Image.new("RGB", (64, 64), self.theme_colors["frame"]), size=(64, 64))

        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        now_playing_frame = ctk.CTkFrame(self, fg_color="transparent")
        now_playing_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsw")
        
        self.now_playing_cover = ctk.CTkLabel(now_playing_frame, text="", image=self.placeholder_image)
        self.now_playing_cover.pack(side="left", padx=(0, 10))
        self.now_playing_label = ctk.CTkLabel(now_playing_frame, text="Выберите трек", font=("Arial", 14, "bold"), wraplength=180, justify="left", anchor="w")
        self.now_playing_label.pack(side="left", fill="both", expand=True)
        
        center_frame = ctk.CTkFrame(self, fg_color="transparent"); center_frame.grid(row=0, column=1, sticky="nsew", pady=5); center_frame.grid_columnconfigure((0, 2), weight=1); center_frame.grid_columnconfigure(1, weight=0)
        buttons_container = ctk.CTkFrame(center_frame, fg_color="transparent")
        buttons_container.grid(row=0, column=1, pady=(5,0))
        
        self.shuffle_button = ctk.CTkButton(buttons_container, text="🔀", font=("Arial", 20), command=self.controller.toggle_shuffle, width=40)
        self.prev_button = ctk.CTkButton(buttons_container, text="⏮", font=("Arial", 20), command=self.controller.prev_track, width=40)
        self.play_pause_button = ctk.CTkButton(buttons_container, text="▶", font=("Arial", 24, "bold"), command=self.controller.play_pause, width=60, height=40)
        self.next_button = ctk.CTkButton(buttons_container, text="⏭", font=("Arial", 20), command=self.controller.next_track, width=40)
        self.repeat_button = ctk.CTkButton(buttons_container, text="🔁", font=("Arial", 20), command=self.controller.toggle_repeat, width=40)
        
        self.shuffle_button.pack(side="left", padx=5); self.prev_button.pack(side="left", padx=5); self.play_pause_button.pack(side="left", padx=10); self.next_button.pack(side="left", padx=5); self.repeat_button.pack(side="left", padx=5)
        
        progress_frame = ctk.CTkFrame(center_frame, fg_color="transparent"); progress_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=20, pady=5); progress_frame.grid_columnconfigure(1, weight=1)
        self.current_time_label = ctk.CTkLabel(progress_frame, text="00:00", width=40)
        
        self.progress_slider = ctk.CTkSlider(progress_frame, from_=0, to=100, command=self.controller.on_slider_drag)
        self.progress_slider.bind("<ButtonPress-1>", self.controller.on_slider_press)
        self.progress_slider.bind("<ButtonRelease-1>", self.controller.on_slider_seek_release)
        
        self.total_time_label = ctk.CTkLabel(progress_frame, text="00:00", width=40)
        self.current_time_label.grid(row=0, column=0, padx=5); self.progress_slider.grid(row=0, column=1, sticky="ew"); self.total_time_label.grid(row=0, column=2, padx=5); self.progress_slider.set(0)
        
        right_controls_frame = ctk.CTkFrame(self, fg_color="transparent"); right_controls_frame.grid(row=0, column=2, padx=10, pady=5, sticky="nse")
        self.like_button = ctk.CTkButton(right_controls_frame, text="👍", font=("Arial", 20), command=self.controller.like_track, width=35)
        self.dislike_button = ctk.CTkButton(right_controls_frame, text="👎", font=("Arial", 20), command=self.controller.dislike_track, width=35)
        self.fav_button = ctk.CTkButton(right_controls_frame, text="♡", font=("Arial", 24), command=self.controller.toggle_favorite, width=35)
        self.recommend_button = ctk.CTkButton(right_controls_frame, text="⭐", font=("Arial", 20), command=self.controller.toggle_recommend_mode, width=35)
        self.mute_button = ctk.CTkButton(right_controls_frame, text="🔊", font=("Arial", 18), command=self.controller.toggle_mute, width=30)
        self.volume_slider = ctk.CTkSlider(right_controls_frame, from_=0, to=100, command=self.controller.set_volume, width=120)
        self.like_button.pack(side="left", padx=3); self.dislike_button.pack(side="left", padx=3); self.fav_button.pack(side="left", padx=3); self.recommend_button.pack(side="left", padx=(3, 10)); self.mute_button.pack(side="left", padx=3); self.volume_slider.pack(side="left", padx=3)
        self.volume_slider.set(self.controller.last_volume * 100)
        self.apply_theme(self.theme_colors)
    
    def apply_theme(self, colors):
        self.theme_colors = colors
        self.configure(fg_color=colors["frame"])
        is_dark = colors.get("bg", "#000000") < "#888888"
        border_color = _adjust_color_brightness(colors["frame"], 1.2 if is_dark else 0.9)
        self.configure(border_color=border_color)
        self.placeholder_image = ctk.CTkImage(light_image=Image.new("RGB", (64, 64), colors["frame"]), size=(64, 64))
        
        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        # Удалена проверка self.controller.is_previewing
        if self.controller.current_track_index == -1:
            self.now_playing_cover.configure(image=self.placeholder_image)
    
        text_color_on_accent = colors["text_on_accent"]
        self.now_playing_label.configure(text_color=colors["text_bright"])
        self.current_time_label.configure(text_color=colors["text_dim"])
        self.total_time_label.configure(text_color=colors["text_dim"])
        self.progress_slider.configure(button_color=colors["accent"], progress_color=colors["text_bright"], button_hover_color=colors["hover"])
        self.play_pause_button.configure(fg_color=colors["accent"], hover_color=colors["hover"], text_color=text_color_on_accent)
        buttons_with_hover = [self.prev_button, self.next_button, self.like_button, self.dislike_button, self.mute_button]
        hover_color = _adjust_color_brightness(colors["frame"], 1.2 if is_dark else 0.9)
        for btn in buttons_with_hover:
            btn.configure(fg_color="transparent", text_color=colors["text_dim"], hover_color=hover_color)
            _apply_text_hover_effect(btn, colors["text_dim"], colors["text_bright"])
        self.update_mode_buttons()
        self.update_fav_button_status()
        self.fav_button.configure(hover_color=hover_color)
        current_fav_color = colors["accent"] if "❤" in self.fav_button.cget("text") else colors["text_dim"]
        _apply_text_hover_effect(self.fav_button, current_fav_color, colors["accent"])
        self.volume_slider.configure(button_color=colors["accent"], progress_color=colors["text_bright"], button_hover_color=colors["hover"])

    def update_track_info_display(self, track_info):
        score = track_info.get('score', 0); play_count = track_info.get('play_count', 0)
        display_text = f"{track_info.get('name', '')}\nРейтинг: {score} | Прослушано: {play_count}"
        self.now_playing_label.configure(text=display_text)
        cover_path = track_info.get('cover_path')
        if cover_path and os.path.exists(cover_path):
            try:
                pil_image = Image.open(cover_path); ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(64, 64)); self.now_playing_cover.configure(image=ctk_image)
            except Exception as e: print(f"Ошибка загрузки локальной обложки: {e}"); self.now_playing_cover.configure(image=self.placeholder_image)
        else: self.now_playing_cover.configure(image=self.placeholder_image)

    def clear_track_info(self): self.now_playing_label.configure(text="Выберите трек"); self.now_playing_cover.configure(image=self.placeholder_image); self.update_fav_button_status()
    def update_play_pause_button(self, is_playing): self.play_pause_button.configure(text="⏸" if is_playing and not self.controller.is_paused else "▶")
    def reset_progress(self): self.progress_slider.set(0); self.current_time_label.configure(text="00:00"); self.total_time_label.configure(text="00:00")
    def update_progress_slider(self, current_pos, total_len):
        if self.controller.seeking: return
        if total_len > 0: self.progress_slider.set((current_pos / total_len) * 100)
        else: self.progress_slider.set(0)
        self.current_time_label.configure(text=time.strftime('%M:%S', time.gmtime(current_pos)))
        self.total_time_label.configure(text=time.strftime('%M:%S', time.gmtime(total_len)))
    def update_current_time_label(self, seek_time): self.current_time_label.configure(text=time.strftime('%M:%S', time.gmtime(seek_time)))
    def update_mode_buttons(self):
        colors = self.theme_colors; text_color_on_accent = colors["text_on_accent"]
        is_dark = colors.get("bg", "#000000") < "#888888"
        hover_color = _adjust_color_brightness(colors["frame"], 1.2 if is_dark else 0.9)
        buttons_to_update = {self.shuffle_button: self.controller.is_shuffle, self.repeat_button: self.controller.is_repeat, self.recommend_button: self.controller.is_recommend_mode}
        for button, is_active in buttons_to_update.items():
            if is_active: button.configure(fg_color=colors["accent"], text_color=text_color_on_accent, hover_color=colors["hover"])
            else: button.configure(fg_color="transparent", text_color=colors["text_dim"], hover_color=hover_color)
    def update_fav_button_status(self):
        if self.controller.current_track_index == -1: self.fav_button.configure(text="♡", state="disabled"); return
        self.fav_button.configure(state="normal")
        try:
            track_info = self.controller.playlist_data[self.controller.current_category][self.controller.current_track_index]
            fav_list = self.controller.playlist_data.get(FAVORITES_NAME, [])
            is_fav = any(t['path'] == track_info['path'] for t in fav_list)
            colors = self.theme_colors
            if is_fav: self.fav_button.configure(text="❤", text_color=colors["accent"])
            else: self.fav_button.configure(text="♡", text_color=colors["text_dim"])
        except IndexError:
            self.fav_button.configure(text="♡", state="disabled")

    def update_mute_button_status(self, is_unmuted): self.mute_button.configure(text="🔊" if is_unmuted else "🔇")