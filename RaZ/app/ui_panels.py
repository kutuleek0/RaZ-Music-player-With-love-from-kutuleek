# app/ui_panels.py
import customtkinter as ctk
from tkinter import messagebox
from functools import partial
import os
import time
from PIL import Image, ImageDraw
from . import search, theme_manager
from .data_manager import FAVORITES_NAME
from tkinter.colorchooser import askcolor
import copy

HUMAN_READABLE_NAMES = {
    "bg": "Основной фон (Градиент)", "frame": "Цвет панелей", "accent": "Акцентный цвет",
    "hover": "Цвет при наведении", "text": "Основной текст", "text_dim": "Приглушенный текст",
    "text_bright": "Яркий текст", "text_on_accent": "Текст на акценте"
}
def _adjust_color_brightness(hex_color, factor):
    if hex_color.startswith('#'): hex_color = hex_color[1:]
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r, g, b = min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor))
    return f"#{r:02x}{g:02x}{b:02x}"

def _apply_text_hover_effect(button, dim_color, bright_color):
    button.bind("<Enter>", lambda e: button.configure(text_color=bright_color), add="+")
    button.bind("<Leave>", lambda e: button.configure(text_color=dim_color), add="+")

class SidebarFrame(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, width=240, corner_radius=0)
        self.controller = controller
        self.theme_colors = self.controller.THEMES[self.controller.theme_name]
        
        self.configure(fg_color=self.theme_colors["frame"])
        
        self.playlist_buttons = {}
        self.current_nav_button = None
        self.current_playlist_button = None
        self.grid_rowconfigure(2, weight=1)
        
        self.logo_label = ctk.CTkLabel(self, text="RaZ Player", font=ctk.CTkFont(size=20, weight="bold"), text_color=self.theme_colors["text_bright"])
        self.logo_label.grid(row=0, column=0, padx=20, pady=20)
        
        self.nav_container = ctk.CTkFrame(self, corner_radius=8, fg_color=self.theme_colors["frame_secondary"])
        self.nav_container.grid(row=1, column=0, sticky="nsew", padx=10)
        
        self.library_button = ctk.CTkButton(self.nav_container, text="Моя медиатека", anchor="w", command=self.on_library_click)
        self.library_button.pack(fill="x", pady=5, padx=5)
        self.search_button = ctk.CTkButton(self.nav_container, text="Поиск", anchor="w", command=self.on_search_click)
        self.search_button.pack(fill="x", pady=(0,5), padx=5)
        self.themes_button = ctk.CTkButton(self.nav_container, text="Темы", anchor="w", command=self.on_themes_click)
        self.themes_button.pack(fill="x", pady=(0,5), padx=5)
        
        self.playlist_container = ctk.CTkFrame(self, corner_radius=8, fg_color=self.theme_colors["frame_secondary"])
        self.playlist_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.playlist_container.grid_rowconfigure(0, weight=1)
        
        self.playlists_scroll_frame = ctk.CTkScrollableFrame(self.playlist_container, label_text="ПЛЕЙЛИСТЫ", label_text_color=self.theme_colors["text_bright"], fg_color="transparent", scrollbar_button_color=self.theme_colors.get("accent"), scrollbar_button_hover_color=self.theme_colors.get("hover"))
        self.playlists_scroll_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.add_playlist_button = ctk.CTkButton(self.playlist_container, text="Создать плейлист", command=self.show_add_playlist_dialog)
        self.add_playlist_button.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        self.apply_theme(self.theme_colors)
        self.on_library_click()
        
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

    def update_playlist_list(self, categories):
        for btn in self.playlist_buttons.values(): btn.destroy()
        self.playlist_buttons.clear()
        system_cats = ["Все треки", "Загруженное", FAVORITES_NAME]
        for cat_name in system_cats:
            if cat_name in categories: self._create_playlist_button(cat_name)
        for cat_name in sorted([c for c in categories if c not in system_cats]): self._create_playlist_button(cat_name)
        self.apply_theme(self.theme_colors)

    def _create_playlist_button(self, name):
        btn = ctk.CTkButton(self.playlists_scroll_frame, text=name, anchor="w", fg_color="transparent", command=partial(self.select_playlist_button, name))
        btn.pack(fill="x", pady=2); self.playlist_buttons[name] = btn;

    def select_playlist_button(self, name):
        if name not in self.playlist_buttons: return
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

    def apply_theme(self, colors):
        self.theme_colors = colors; self.configure(fg_color=colors["frame"]); self.logo_label.configure(text_color=colors["text_bright"])
        self.nav_container.configure(fg_color=colors["frame_secondary"]); self.playlist_container.configure(fg_color=colors["frame_secondary"])
        self.playlists_scroll_frame.configure(label_text_color=colors["text_bright"])
        if hasattr(self.playlists_scroll_frame, "_scrollbar"):
            self.playlists_scroll_frame._scrollbar.configure(button_color=colors.get("accent"), button_hover_color=colors.get("hover"))
        self.add_playlist_button.configure(fg_color=colors["accent"], hover_color=colors["hover"], text_color=colors["text_on_accent"])
        
        all_buttons = list(self.playlist_buttons.values()) + [self.library_button, self.search_button, self.themes_button]
        for btn in all_buttons:
             is_nav_selected = (self.current_nav_button == btn)
             is_playlist_selected = (self.current_playlist_button == btn)
             self.apply_theme_to_button(btn, is_selected=(is_nav_selected or is_playlist_selected))

    def apply_theme_to_button(self, btn, is_selected):
        colors = self.theme_colors
        is_dark = colors["bg"] < "#888888"
        hover_color = _adjust_color_brightness(colors["frame_secondary"], 1.1 if is_dark else 0.95)
        
        if is_selected:
            btn.configure(fg_color=colors["accent"], text_color=colors["text_on_accent"], hover_color=colors["hover"])
        else:
            btn.configure(fg_color="transparent", text_color=colors["text"], hover_color=hover_color)
        btn.configure(text_color_disabled=colors["text_dim"])

class ContentFrame(ctk.CTkFrame):
    def __init__(self, master, controller, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.current_view = None
        self.track_widgets = []
        self.selected_track_index = -1
        self.search_entry = None
        self.search_results_frame = None
        self.search_status_label = None

    def _clear_view(self):
        for widget in self.winfo_children(): widget.destroy()
        self.track_widgets = []; self.selected_track_index = -1

    def refresh_current_view(self):
        if self.current_view == "playlist": self.display_playlist_view(self.controller.current_category, self.controller.playlist_data.get(self.controller.current_category, []))
        elif self.current_view == "search": self.display_search_view(True)
        elif self.current_view == "themes": self.display_themes_view()

    def display_playlist_view(self, category_name, tracks):
        self._clear_view(); self.current_view = "playlist"
        colors = self.controller.THEMES[self.controller.theme_name]
        self.configure(fg_color=colors["bg"])
        
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20,10)); header_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(header_frame, text=category_name, font=ctk.CTkFont(size=24, weight="bold"), text_color=colors["text_bright"])
        title_label.grid(row=0, column=0, sticky="w")
        if category_name not in ["Все треки", "Загруженное", FAVORITES_NAME]:
            ctk.CTkButton(header_frame, text="Удалить плейлист", command=lambda: self.controller.delete_category(category_name), fg_color="#DB3E3E", hover_color="#B32B2B").grid(row=0, column=1, sticky="e")

        list_container = ctk.CTkFrame(self, corner_radius=8, fg_color=colors["frame"])
        list_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        list_container.grid_rowconfigure(0, weight=1); list_container.grid_columnconfigure(0, weight=1)

        scroll_frame = ctk.CTkScrollableFrame(list_container, fg_color="transparent", scrollbar_button_color=colors.get("accent"), scrollbar_button_hover_color=colors.get("hover"))
        scroll_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        footer_frame.grid_columnconfigure((0, 1), weight=1)
        
        text_color_on_accent = colors["text_on_accent"]
        add_button = ctk.CTkButton(footer_frame, text="Добавить трек", command=self.controller.add_track, text_color=text_color_on_accent, fg_color=colors["accent"], hover_color=colors["hover"])
        add_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        remove_button = ctk.CTkButton(footer_frame, text="Удалить трек", command=lambda: self.controller.remove_track(self.selected_track_index), text_color=text_color_on_accent, fg_color=colors["accent"], hover_color=colors["hover"])
        remove_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        
        if not tracks:
            no_tracks_label = ctk.CTkLabel(scroll_frame, text="В этом плейлисте пока нет треков", font=ctk.CTkFont(size=14), text_color=colors["text_dim"])
            no_tracks_label.pack(expand=True, pady=50)
        else:
            for i, track in enumerate(tracks):
                track_frame = ctk.CTkButton(scroll_frame, text=f"{i+1}. {track['name']}", anchor="w", command=partial(self.controller.select_and_play, i), fg_color="transparent", text_color=colors["text_dim"])
                _apply_text_hover_effect(track_frame, colors["text_dim"], colors["text_bright"])
                track_frame.pack(fill="x", pady=2)
                self.track_widgets.append(track_frame)

    def update_active_track_highlight(self, index):
        self.selected_track_index = index; colors = self.controller.THEMES[self.controller.theme_name]
        text_color_on_accent = colors["text_on_accent"]
        for i, btn in enumerate(self.track_widgets):
            if i == self.selected_track_index: btn.configure(fg_color=colors["accent"], text_color=text_color_on_accent)
            else: btn.configure(fg_color="transparent", text_color=colors["text_dim"])

    def display_search_view(self, force_redraw=False):
        if self.current_view != "search" or force_redraw:
            self._clear_view(); self.current_view = "search"; colors = self.controller.THEMES[self.controller.theme_name]
            self.configure(fg_color=colors["bg"])
            
            self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(2, weight=1)
            search_bar_frame = ctk.CTkFrame(self, fg_color="transparent"); search_bar_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew"); search_bar_frame.grid_columnconfigure(0, weight=1)
            
            self.search_entry = ctk.CTkEntry(search_bar_frame, placeholder_text="Введите название трека или исполнителя...", border_color=colors["accent"], text_color=colors["text"], fg_color=colors["frame"])
            self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
            
            self.search_button = ctk.CTkButton(search_bar_frame, text="Найти", command=lambda: search.start_search_thread(self.controller), fg_color=colors["accent"], hover_color=colors["hover"], text_color=colors["text_on_accent"])
            self.search_button.grid(row=0, column=1)
            
            self.search_status_label = ctk.CTkLabel(self, text="", text_color=colors["text_dim"]); self.search_status_label.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="ew")
            
            self.search_results_frame = ctk.CTkScrollableFrame(self, label_text="Результаты поиска", label_text_color=colors["text_bright"], fg_color=colors["frame"], scrollbar_button_color=colors.get("accent"), scrollbar_button_hover_color=colors.get("hover"))
            self.search_results_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
            
            if hasattr(self.controller, 'search_results_cache') and self.controller.search_results_cache: self.display_search_results()

    def display_search_results(self):
        if not self.search_results_frame: return
        self.search_button.configure(state="normal")
        for widget in self.search_results_frame.winfo_children(): widget.destroy()
        results_to_show = self.controller.search_results_cache
        if not results_to_show: self.search_status_label.configure(text="Ничего не найдено."); return
        self.search_status_label.configure(text=f"Найдено: {len(results_to_show)}")
        for result_data in results_to_show: self.create_result_widget(self.search_results_frame, result_data)

    def create_result_widget(self, parent, data):
        colors = self.controller.THEMES[self.controller.theme_name]
        is_dark = colors["bg"] < "#888888"
        frame = ctk.CTkFrame(parent, fg_color=_adjust_color_brightness(colors["frame"], 1.1 if is_dark else 0.95), corner_radius=5)
        frame.pack(fill="x", padx=5, pady=5); frame.grid_columnconfigure(1, weight=1)
        cover_label = ctk.CTkLabel(frame, text="", image=self.controller.player_bar.placeholder_image); cover_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        thumbnail_url = data.get('thumbnail')
        if thumbnail_url: search.start_image_load_thread(thumbnail_url, (48, 48), lambda img: cover_label.configure(image=img) if img else None)
        label_text = f"{data.get('title', '')}\n{data.get('uploader', '')}"
        label = ctk.CTkLabel(frame, text=label_text, anchor="w", justify="left", text_color=colors["text"]); label.grid(row=0, column=1, padx=10, pady=(10, 0), sticky="ew")
        btns_frame = ctk.CTkFrame(frame, fg_color="transparent"); btns_frame.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="w")
        p_btn = ctk.CTkButton(btns_frame, text="▶", width=30, command=lambda d=data, b=p_btn: search.start_preview_thread(self.controller, d, b), fg_color=colors["bg"], hover_color=colors["accent"])
        d_btn = ctk.CTkButton(btns_frame, text="⏬", width=30, command=lambda d=data, db=d_btn, pb=p_btn: search.start_download_thread(self.controller, d, db, pb), fg_color=colors["bg"], hover_color=colors["hover"])
        duration_label = ctk.CTkLabel(btns_frame, text=f"({time.strftime('%M:%S', time.gmtime(data.get('duration', 0)))})", text_color=colors["text_dim"])
        p_btn.pack(side="left", padx=(0, 5)); d_btn.pack(side="left"); duration_label.pack(side="left", padx=(10, 0))

    def display_themes_view(self):
        self._clear_view(); self.current_view = "themes"
        colors = self.controller.THEMES[self.controller.theme_name]
        self.configure(fg_color=colors["bg"])
        
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        
        header_frame = ctk.CTkFrame(self, fg_color="transparent"); header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20,10)); header_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(header_frame, text="Выбор темы", font=ctk.CTkFont(size=24, weight="bold"), text_color=colors["text_bright"])
        title_label.grid(row=0, column=0, sticky="w")
        
        add_theme_button = ctk.CTkButton(header_frame, text="+ Добавить тему", command=self.open_theme_editor, fg_color=colors["accent"], hover_color=colors["hover"], text_color=colors["text_on_accent"])
        add_theme_button.grid(row=0, column=1, sticky="e")
        
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color=colors.get("accent"), scrollbar_button_hover_color=colors.get("hover"))
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10); scroll_frame.grid_columnconfigure((0, 1), weight=1)

        for i, (theme_name, theme_colors) in enumerate(self.controller.THEMES.items()):
            row, col = i // 2, i % 2; is_active = self.controller.theme_name == theme_name
            
            theme_card = ctk.CTkFrame(scroll_frame, border_width=3 if is_active else 1, border_color=colors["accent"] if is_active else theme_colors["frame"], fg_color=theme_colors["frame"])
            theme_card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew"); theme_card.grid_columnconfigure(0, weight=1)
            
            card_buttons_frame = ctk.CTkFrame(theme_card, fg_color="transparent"); card_buttons_frame.place(relx=1.0, rely=0, anchor="ne", x=-5, y=5)
            edit_button = ctk.CTkButton(card_buttons_frame, text="✎", width=25, height=25, command=partial(self.open_theme_editor, theme_name=theme_name), fg_color="transparent", hover_color=theme_colors["hover"], text_color=theme_colors["text_dim"]); edit_button.pack(side="left")
            if theme_name not in theme_manager.get_default_themes():
                delete_button = ctk.CTkButton(card_buttons_frame, text="🗑️", width=25, height=25, command=partial(self._delete_theme, theme_name), fg_color="transparent", hover_color="#E53935", text_color=theme_colors["text_dim"]); delete_button.pack(side="left")
            
            card_label = ctk.CTkLabel(theme_card, text=theme_name, font=ctk.CTkFont(size=18, weight="bold"), text_color=theme_colors["text_bright"]); card_label.grid(row=0, column=0, pady=(20,5), padx=20)
            
            if is_active:
                active_label = ctk.CTkLabel(theme_card, text="✓ Активна", text_color=colors["accent"], font=ctk.CTkFont(size=12, weight="bold")); active_label.grid(row=1, column=0, pady=(0, 10))
            
            preview_container = ctk.CTkFrame(theme_card, fg_color=theme_colors.get("bg", "#000000"), height=80, corner_radius=8); preview_container.grid(row=2, column=0, sticky="ew", padx=15, pady=10); preview_container.pack_propagate(False)
            
            sidebar_mock = ctk.CTkFrame(preview_container, width=50, fg_color=theme_colors.get("frame", "#1c1c1c"), corner_radius=0); sidebar_mock.pack(side="left", fill="y")
            player_bar_mock = ctk.CTkFrame(preview_container, height=20, fg_color=theme_colors.get("frame", "#1c1c1c"), corner_radius=0); player_bar_mock.pack(side="bottom", fill="x")
            ctk.CTkFrame(player_bar_mock, width=15, height=10, fg_color=theme_colors.get("accent", "#ffff00"), corner_radius=3).pack(pady=5)

            def on_card_click(name): return lambda e, n=name: self.controller.set_theme(n)
            clickable_widgets = [theme_card, card_label, preview_container, sidebar_mock, player_bar_mock]
            if is_active: clickable_widgets.append(active_label)
            for widget in clickable_widgets: widget.bind("<Button-1>", on_card_click(theme_name))

    def _delete_theme(self, theme_name):
        # --- ИСПРАВЛЕНО: Добавлен pass ---
        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить тему '{theme_name}'? \nЭто действие необратимо."):
            all_themes = self.controller.THEMES
            if self.controller.theme_name == theme_name: self.controller.set_theme("Яндекс.Ночь")
            del all_themes[theme_name]
            theme_manager.save_themes(all_themes); self.display_themes_view()

    def open_theme_editor(self, theme_name=None):
        # --- ИСПРАВЛЕНО: Добавлен pass ---
        pass

    def apply_theme(self, colors):
        pass

class PlayerControlFrame(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, height=80, corner_radius=10, border_width=1)
        self.controller = controller
        self.theme_colors = self.controller.THEMES[self.controller.theme_name]
        
        self.placeholder_image = ctk.CTkImage(light_image=Image.new("RGB", (64, 64), self.theme_colors["frame"]), size=(64, 64))

        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        now_playing_frame = ctk.CTkFrame(self, fg_color="transparent")
        now_playing_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsw")
        
        self.now_playing_cover = ctk.CTkLabel(now_playing_frame, text="", image=self.placeholder_image)
        self.now_playing_cover.pack(side="left", padx=(0, 10))
        self.now_playing_label = ctk.CTkLabel(now_playing_frame, text="Выберите трек", font=("Arial", 14, "bold"), wraplength=180, justify="left", anchor="w")
        self.now_playing_label.pack(side="left", fill="both", expand=True)
        
        center_frame = ctk.CTkFrame(self, fg_color="transparent"); center_frame.grid(row=0, column=1, sticky="nsew", pady=5); center_frame.grid_columnconfigure(0, weight=1)
        buttons_grid = ctk.CTkFrame(center_frame, fg_color="transparent"); buttons_grid.pack(pady=(5,0))
        
        self.shuffle_button = ctk.CTkButton(buttons_grid, text="🔀", font=("Arial", 20), command=self.controller.toggle_shuffle, width=40)
        self.prev_button = ctk.CTkButton(buttons_grid, text="⏮", font=("Arial", 20), command=self.controller.prev_track, width=40)
        self.play_pause_button = ctk.CTkButton(buttons_grid, text="▶", font=("Arial", 24, "bold"), command=self.controller.play_pause, width=60, height=40)
        self.next_button = ctk.CTkButton(buttons_grid, text="⏭", font=("Arial", 20), command=self.controller.next_track, width=40)
        self.repeat_button = ctk.CTkButton(buttons_grid, text="🔁", font=("Arial", 20), command=self.controller.toggle_repeat, width=40)
        self.shuffle_button.pack(side="left", padx=5); self.prev_button.pack(side="left", padx=5); self.play_pause_button.pack(side="left", padx=10); self.next_button.pack(side="left", padx=5); self.repeat_button.pack(side="left", padx=5)
        
        progress_frame = ctk.CTkFrame(center_frame, fg_color="transparent"); progress_frame.pack(fill="x", padx=20, pady=5); progress_frame.grid_columnconfigure(1, weight=1)
        self.current_time_label = ctk.CTkLabel(progress_frame, text="00:00", width=40)
        self.progress_slider = ctk.CTkSlider(progress_frame, from_=0, to=100, command=self.controller.on_slider_release); self.progress_slider.bind("<Button-1>", self.controller.on_slider_press)
        self.total_time_label = ctk.CTkLabel(progress_frame, text="00:00", width=40)
        self.current_time_label.grid(row=0, column=0, padx=5); self.progress_slider.grid(row=0, column=1, sticky="ew"); self.total_time_label.grid(row=0, column=2, padx=5); self.progress_slider.set(0)
        
        right_controls_frame = ctk.CTkFrame(self, fg_color="transparent"); right_controls_frame.grid(row=0, column=2, padx=10, pady=5, sticky="nse")
        self.like_button = ctk.CTkButton(right_controls_frame, text="👍", font=("Arial", 20), command=self.controller.like_track, width=35)
        self.dislike_button = ctk.CTkButton(right_controls_frame, text="👎", font=("Arial", 20), command=self.controller.dislike_track, width=35)
        self.fav_button = ctk.CTkButton(right_controls_frame, text="♡", font=("Arial", 24), command=self.controller.toggle_favorite, width=35)
        self.recommend_button = ctk.CTkButton(right_controls_frame, text="⭐", command=self.controller.toggle_recommend_mode, width=35)
        self.mute_button = ctk.CTkButton(right_controls_frame, text="🔊", font=("Arial", 18), command=self.controller.toggle_mute, width=30)
        self.volume_slider = ctk.CTkSlider(right_controls_frame, from_=0, to=100, command=self.controller.set_volume, width=120)
        self.like_button.pack(side="left", padx=3); self.dislike_button.pack(side="left", padx=3); self.fav_button.pack(side="left", padx=3); self.recommend_button.pack(side="left", padx=(3, 10)); self.mute_button.pack(side="left", padx=3); self.volume_slider.pack(side="left", padx=3)
        self.volume_slider.set(self.controller.last_volume * 100)

        # --- КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Вызов apply_theme ПЕРЕМЕЩЕН в конец ---
        self.apply_theme(self.theme_colors)
    
    def update_track_info_display(self, track_info):
        score = track_info.get('score', 0); display_text = f"{track_info['name']}\n[Рейтинг: {score}]"; self.now_playing_label.configure(text=display_text)
        cover_path = track_info.get('cover_path')
        if cover_path and os.path.exists(cover_path):
            try:
                pil_image = Image.open(cover_path); ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(64, 64)); self.now_playing_cover.configure(image=ctk_image)
            except Exception as e: print(f"Ошибка загрузки локальной обложки: {e}"); self.now_playing_cover.configure(image=self.placeholder_image)
        else: self.now_playing_cover.configure(image=self.placeholder_image)
    def clear_track_info(self): self.now_playing_label.configure(text="Выберите трек"); self.now_playing_cover.configure(image=self.placeholder_image); self.update_fav_button_status()
    def update_play_pause_button(self, is_playing): self.play_pause_button.configure(text="⏸" if is_playing else "▶")
    def reset_progress(self): self.progress_slider.set(0); self.current_time_label.configure(text="00:00"); self.total_time_label.configure(text="00:00")
    def update_progress_slider(self, current_pos, total_len):
        if self.controller.seeking: return
        self.progress_slider.set((current_pos / total_len) * 100)
        self.current_time_label.configure(text=time.strftime('%M:%S', time.gmtime(current_pos)))
        self.total_time_label.configure(text=time.strftime('%M:%S', time.gmtime(total_len)))
    def update_current_time_label(self, seek_time): self.current_time_label.configure(text=time.strftime('%M:%S', time.gmtime(seek_time)))
    def update_mode_buttons(self):
        colors = self.theme_colors; text_color_on_accent = colors["text_on_accent"]
        is_dark = colors["bg"] < "#888888"
        hover_color = _adjust_color_brightness(colors["frame"], 1.2 if is_dark else 0.9)
        buttons_to_update = {self.shuffle_button: self.controller.is_shuffle, self.repeat_button: self.controller.is_repeat, self.recommend_button: self.controller.is_recommend_mode}
        for button, is_active in buttons_to_update.items():
            if is_active: button.configure(fg_color=colors["accent"], text_color=text_color_on_accent, hover_color=colors["hover"])
            else: button.configure(fg_color="transparent", text_color=colors["text_dim"], hover_color=hover_color)
    def update_fav_button_status(self):
        if self.controller.current_track_index == -1: self.fav_button.configure(text="♡", state="disabled"); return
        self.fav_button.configure(state="normal")
        track_info = self.controller.playlist_data[self.controller.current_category][self.controller.current_track_index]
        fav_list = self.controller.playlist_data.get(FAVORITES_NAME, [])
        is_fav = any(t['path'] == track_info['path'] for t in fav_list)
        colors = self.theme_colors
        if is_fav: self.fav_button.configure(text="❤", text_color=colors["accent"])
        else: self.fav_button.configure(text="♡", text_color=colors["text_dim"])
    def update_mute_button_status(self, is_unmuted): self.mute_button.configure(text="🔊" if is_unmuted else "🔇")
    def apply_theme(self, colors):
        self.theme_colors = colors; self.configure(fg_color=colors["frame"])
        is_dark = colors["bg"] < "#888888"
        border_color = _adjust_color_brightness(colors["frame"], 1.2 if is_dark else 0.9)
        self.configure(border_color=border_color)
        self.placeholder_image = ctk.CTkImage(light_image=Image.new("RGB", (64, 64), colors["frame"]), size=(64, 64))
        if self.controller.current_track_index == -1 and not self.controller.is_previewing: 
            self.now_playing_cover.configure(image=self.placeholder_image)
        text_color_on_accent = colors["text_on_accent"]
        self.now_playing_label.configure(text_color=colors["text_bright"]); self.current_time_label.configure(text_color=colors["text_dim"]); self.total_time_label.configure(text_color=colors["text_dim"])
        self.progress_slider.configure(button_color=colors["accent"], progress_color=colors["text_bright"], button_hover_color=colors["hover"])
        self.play_pause_button.configure(fg_color=colors["accent"], hover_color=colors["hover"], text_color=text_color_on_accent)
        buttons_with_hover = [self.prev_button, self.next_button, self.like_button, self.dislike_button, self.mute_button]
        hover_color = _adjust_color_brightness(colors["frame"], 1.2 if is_dark else 0.9)
        for btn in buttons_with_hover: btn.configure(fg_color="transparent", text_color=colors["text_dim"], hover_color=hover_color); _apply_text_hover_effect(btn, colors["text_dim"], colors["text_bright"])
        self.update_mode_buttons(); self.update_fav_button_status(); self.fav_button.configure(hover_color=hover_color)
        current_fav_color = colors["accent"] if "❤" in self.fav_button.cget("text") else colors["text_dim"]
        _apply_text_hover_effect(self.fav_button, current_fav_color, colors["accent"])
        self.volume_slider.configure(button_color=colors["accent"], progress_color=colors["text_bright"], button_hover_color=colors["hover"])