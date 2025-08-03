# --- ФАЙЛ: app/ui_components.py ---
import customtkinter as ctk
from PIL import Image, ImageDraw
from tkinter import TclError

class GradientFrame(ctk.CTkFrame):
    """
    A frame with a vertical gradient background.
    Uses a debounced after-callback to prevent recursive <Configure> loops.
    """
    def __init__(self, master, color1, color2, **kwargs):
        super().__init__(master, **kwargs)
        self._color1 = color1
        self._color2 = color2
        self._gradient_image = None
        
        self.bg_label = ctk.CTkLabel(self, text="", image=self._gradient_image)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # --- ИЗМЕНЕНО: Используем дебаунсинг для предотвращения зависания ---
        self._after_id = None
        self.bind("<Configure>", self._on_configure_debounced)
        # --- КОНЕЦ ИЗМЕНЕНИЙ ---

    # --- ДОБАВЛЕНО: Новый метод-обертка для дебаунсинга ---
    def _on_configure_debounced(self, event=None):
        # Если есть запланированный вызов, отменяем его
        if self._after_id:
            self.after_cancel(self._after_id)
        # Планируем новый вызов через 20 мс
        self._after_id = self.after(20, self._draw_gradient)

    def _draw_gradient(self):
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1: 
            return

        # Сбрасываем ID, так как вызов состоялся
        self._after_id = None

        image = Image.new("RGB", (width, height), self._color2)
        draw = ImageDraw.Draw(image)

        try:
            (r1, g1, b1) = self.winfo_rgb(self._color1)
            (r2, g2, b2) = self.winfo_rgb(self._color2)
        except TclError:
             # Это может произойти при закрытии окна
             return
             
        r_ratio = float(r2 - r1) / height
        g_ratio = float(g2 - g1) / height
        b_ratio = float(b2 - b1) / height

        for i in range(height):
            nr = int(r1 + (r_ratio * i))
            ng = int(g1 + (g_ratio * i))
            nb = int(b1 + (b_ratio * i))
            draw.line([(0, i), (width, i)], fill=(nr//256, ng//256, nb//256))

        self._gradient_image = ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))
        self.bg_label.configure(image=self._gradient_image)
        self.bg_label.lower()

    def update_gradient(self, color1, color2):
        self._color1 = color1
        self._color2 = color2
        # Просто вызываем обработчик, он сам разберется с планированием
        self._on_configure_debounced()