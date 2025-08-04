import sys
from tkinterdnd2 import DND_FILES, TkinterDnD

from app.main_window import RaZPlayer

if __name__ == "__main__":
    try:
        # --- ИЗМЕНЕНИЕ АРХИТЕКТУРЫ ---
        # 1. Создаем корневое окно, поддерживающее Drag-and-Drop
        root = TkinterDnD.Tk()
        
        # 2. Настраиваем корневое окно
        root.title("RaZ Music Player")
        root.geometry("1200x750")
        root.minsize(1000, 700)
        
        # 3. Создаем экземпляр нашего приложения как фрейм внутри этого окна
        app = RaZPlayer(master=root)
        app.pack(fill="both", expand=True) # Приложение-фрейм заполняет все окно

        # 4. Настраиваем закрытие окна и привязываем событие DND
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.drop_target_register(DND_FILES)
        root.dnd_bind('<<Drop>>', app.handle_drop)

        # 5. Запускаем главный цикл корневого окна
        root.mainloop()
        
    except KeyboardInterrupt:
        print("\nПрограмма была прервана пользователем.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Попытаемся показать ошибку в GUI, если это возможно
        try:
            from tkinter import messagebox
            messagebox.showerror("Критическая ошибка", f"Произошла непредвиденная ошибка:\n\n{e}\n\nПриложение будет закрыто.")
        except:
            print(f"Произошла критическая ошибка: {e}")
        sys.exit(1)