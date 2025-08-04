# --- ФАЙЛ: app/ui_components.py ---
import customtkinter as ctk
from PIL import Image, ImageDraw
from tkinter import TclError

def _adjust_color_brightness(hex_color, factor):
    if not hex_color or not hex_color.startswith('#'): return "#000000"
    hex_color = hex_color[1:]
    if len(hex_color) != 6: return "#000000"
    try:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r, g, b = min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    except ValueError:
        return "#000000"

class GradientFrame(ctk.CTkFrame):
    def __init__(self, master, color1, color2, **kwargs):
        super().__init__(master, **kwargs)
        self._color1 = color1
        self._color2 = color2
        self._gradient_image = None
        self.bg_label = ctk.CTkLabel(self, text="", image=self._gradient_image)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._after_id = None
        self.bind("<Configure>", self._on_configure_debounced)

    def _on_configure_debounced(self, event=None):
        if self._after_id: self.after_cancel(self._after_id)
        self._after_id = self.after(20, self._draw_gradient)

    def _draw_gradient(self):
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 1 or height <= 1: return
        self._after_id = None
        image = Image.new("RGB", (width, height), self._color2)
        draw = ImageDraw.Draw(image)
        try:
            (r1, g1, b1), (r2, g2, b2) = self.winfo_rgb(self._color1), self.winfo_rgb(self._color2)
        except TclError: return
        r_ratio, g_ratio, b_ratio = float(r2 - r1) / height, float(g2 - g1) / height, float(b2 - b1) / height
        for i in range(height):
            nr, ng, nb = int(r1 + (r_ratio * i)), int(g1 + (g_ratio * i)), int(b1 + (b_ratio * i))
            draw.line([(0, i), (width, i)], fill=(nr//256, ng//256, nb//256))
        self._gradient_image = ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))
        self.bg_label.configure(image=self._gradient_image)
        self.bg_label.lower()

    def update_gradient(self, color1, color2):
        self._color1, self._color2 = color1, color2
        self._on_configure_debounced()

class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text = widget, text
        self.tooltip_window, self.id = None, None
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<ButtonPress>", self.hide_tooltip)

    def schedule_tooltip(self, event=None):
        self.hide_tooltip()
        self.id = self.widget.after(700, self.show_tooltip)

    def show_tooltip(self):
        if self.tooltip_window or not self.text: return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 20
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = ctk.CTkLabel(self.tooltip_window, text=self.text, corner_radius=4, fg_color=("#303030", "#404040"), text_color="white", wraplength=300, justify="left", padx=8, pady=4, font=ctk.CTkFont(size=12))
        label.pack()

    def hide_tooltip(self, event=None):
        if self.id: self.widget.after_cancel(self.id); self.id = None
        if self.tooltip_window: self.tooltip_window.destroy(); self.tooltip_window = None

class VolumeDialog(ctk.CTkToplevel):
    def __init__(self, master, current_multiplier):
        super().__init__(master)
        self.title("Громкость трека")
        self.geometry("300x150")
        self.transient(master)
        self.grab_set()
        self.result = None
        self.value_var = ctk.DoubleVar(value=current_multiplier)
        self.label = ctk.CTkLabel(self, text=f"{int(current_multiplier * 100)}%")
        self.label.pack(pady=10)
        self.slider = ctk.CTkSlider(self, from_=0.5, to=1.5, variable=self.value_var, command=self._update_label)
        self.slider.pack(pady=10, padx=20, fill="x")
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=10)
        ctk.CTkButton(button_frame, text="OK", command=self._on_ok).pack(side="left", padx=10)
        ctk.CTkButton(button_frame, text="Отмена", command=self.destroy, fg_color="transparent", border_width=1).pack(side="left", padx=10)
        self.wait_window(self)

    def _update_label(self, value): self.label.configure(text=f"{int(value * 100)}%")
    def _on_ok(self): self.result = self.value_var.get(); self.destroy()
class SelectPlaylistDialog(ctk.CTkToplevel):
    def __init__(self, master, title, playlist_names):
        super().__init__(master)
        self.title(title)
        self.transient(master)
        self.grab_set()
        
        self.result = None
        
        if not playlist_names:
            label = ctk.CTkLabel(self, text="Сначала создайте плейлист.")
            label.pack(padx=20, pady=20)
            self.after(2000, self.destroy)
            return

        scroll_frame = ctk.CTkScrollableFrame(self, label_text="Выберите плейлист:")
        scroll_frame.pack(padx=15, pady=15, fill="both", expand=True)

        for name in playlist_names:
            btn = ctk.CTkButton(scroll_frame, text=name, command=lambda n=name: self._on_select(n))
            btn.pack(fill="x", padx=10, pady=5)
            
        cancel_button = ctk.CTkButton(self, text="Отмена", fg_color="transparent", border_width=1, command=self.destroy)
        cancel_button.pack(padx=15, pady=(0, 15), side="bottom", fill="x")

        self.wait_window(self)

    def _on_select(self, name):
        self.result = name
        self.destroy()