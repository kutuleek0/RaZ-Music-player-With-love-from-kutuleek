# --- ФАЙЛ: src/app/theme_editor.py (ИСПРАВЛЕННАЯ ВЕРСИЯ) ---

import customtkinter as ctk
from tkinter import messagebox
from tkinter.colorchooser import askcolor
from functools import partial
from . import theme_manager

class ThemeEditor(ctk.CTkToplevel):
    def __init__(self, master, callback, theme_name=None, theme_data=None):
        super().__init__(master)
        self.callback = callback
        self.original_name = theme_name
        
        self.title("Редактор Темы")
        self.geometry("650x650")
        self.transient(master)
        self.grab_set()

        default_theme = {
            "gradient_top": "#2a2a2a", "gradient_bottom": "#121212", "bg": "#121212",
            "frame": "#1c1c1c", "frame_secondary": "#121212", "accent": "#FFD600",
            "hover": "#f9e04a", "text": "#FFFFFF", "text_dim": "#b3b3b3",
            "text_bright": "#FFFFFF", "text_on_accent": "#000000"
        }
        
        self.current_theme_data = theme_data.copy() if theme_data else default_theme
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Переменные для хранения значений ---
        self.name_var = ctk.StringVar(value=theme_name or "Моя новая тема")
        self.color_vars = {key: ctk.StringVar(value=self.current_theme_data[key]) for key in default_theme}

        # --- Создание всех виджетов ---
        self._create_widgets()
        self._create_preview()
        self._update_preview()
        
        # Привязываем обновление превью к изменению любой переменной
        for var in self.color_vars.values():
            var.trace_add("write", self._on_color_change)
            
        self.wait_window(self)

    def _create_widgets(self):
        """Создает все виджеты управления темой."""
        # --- Левая панель: Настройки ---
        settings_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        settings_frame.grid(row=0, column=0, rowspan=2, padx=20, pady=20, sticky="nsew")
        settings_frame.grid_columnconfigure(1, weight=1)

        # Имя темы
        ctk.CTkLabel(settings_frame, text="Название темы:").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))
        name_entry = ctk.CTkEntry(settings_frame, textvariable=self.name_var)
        name_entry.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 20))

        # Цвета
        row_counter = 2
        for key, var in self.color_vars.items():
            label = ctk.CTkLabel(settings_frame, text=f"{key}:")
            label.grid(row=row_counter, column=0, sticky="w", padx=(0, 10))
            
            entry = ctk.CTkEntry(settings_frame, textvariable=var)
            entry.grid(row=row_counter, column=1, sticky="ew", pady=3)
            
            color_button = ctk.CTkButton(settings_frame, text="", width=28, height=28, 
                                         fg_color=var.get(), hover=False, border_width=1, border_color="gray50",
                                         command=partial(self._pick_color, key))
            color_button.grid(row=row_counter, column=2, padx=(5, 0))
            
            var.trace_add("write", lambda *args, btn=color_button, v=var: self._update_button_color(btn, v.get()))
            row_counter += 1

        # --- Кнопки управления ---
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="e")
        
        save_button = ctk.CTkButton(button_frame, text="Сохранить", command=self._on_save)
        save_button.pack(side="left", padx=(0, 10))
        
        cancel_button = ctk.CTkButton(button_frame, text="Отмена", fg_color="transparent", border_width=1, command=self.destroy)
        cancel_button.pack(side="left")

    def _create_preview(self):
        """Создает виджеты для предпросмотра темы."""
        preview_container = ctk.CTkFrame(self)
        preview_container.grid(row=1, column=1, padx=(0, 20), pady=(0, 20), sticky="nsew")
        preview_container.grid_rowconfigure(0, weight=1)
        preview_container.grid_columnconfigure(0, weight=1)
        
        self.preview_frame = ctk.CTkFrame(preview_container)
        self.preview_frame.grid(row=0, column=0, sticky="nsew")

        self.preview_title = ctk.CTkLabel(self.preview_frame, text="Заголовок", font=ctk.CTkFont(size=16, weight="bold"))
        self.preview_title.pack(pady=10, padx=20, anchor="w")
        
        self.preview_text = ctk.CTkLabel(self.preview_frame, text="Обычный текст для примера.")
        self.preview_text.pack(pady=5, padx=20, anchor="w")
        
        self.preview_button = ctk.CTkButton(self.preview_frame, text="Акцентная кнопка", height=40)
        self.preview_button.pack(pady=10, padx=20, fill="x")

        self.preview_secondary_frame = ctk.CTkFrame(self.preview_frame, height=50)
        self.preview_secondary_frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(self.preview_secondary_frame, text="Вторичный фрейм").pack(expand=True)

    def _update_preview(self):
        """Обновляет цвета всех элементов предпросмотра."""
        try:
            data = {key: var.get() for key, var in self.color_vars.items()}
            self.preview_frame.configure(fg_color=data["bg"])
            self.preview_title.configure(text_color=data["text_bright"])
            self.preview_text.configure(text_color=data["text"])
            self.preview_button.configure(fg_color=data["accent"], hover_color=data["hover"], text_color=data["text_on_accent"])
            self.preview_secondary_frame.configure(fg_color=data["frame_secondary"])
            self.preview_secondary_frame.winfo_children()[0].configure(text_color=data["text_dim"])
        except Exception:
            # Игнорируем ошибки, которые могут возникнуть при вводе некорректного цвета
            pass
        
    def _on_color_change(self, *args):
        self._update_preview()

    def _update_button_color(self, button, color_string):
        """Безопасно обновляет цвет кнопки предпросмотра."""
        try:
            button.configure(fg_color=color_string)
        except Exception:
            pass # Игнорируем, если пользователь ввел некорректный цвет

    def _pick_color(self, key):
        var = self.color_vars[key]
        current_color = var.get()
        new_color = askcolor(color=current_color, title=f"Выберите цвет для '{key}'")
        if new_color and new_color[1]:
            var.set(new_color[1])

    def _on_save(self):
        theme_name = self.name_var.get().strip()
        if not theme_name:
            messagebox.showerror("Ошибка", "Название темы не может быть пустым.", parent=self)
            return
            
        default_themes = theme_manager.get_default_themes()
        if theme_name in default_themes and theme_name != self.original_name:
            messagebox.showerror("Ошибка", "Нельзя использовать имя системной темы.", parent=self)
            return
            
        final_data = {key: var.get() for key, var in self.color_vars.items()}
        self.callback(self.original_name, theme_name, final_data)
        self.destroy()