# src/run_player.py
from app.main_window import RaZPlayer # Теперь это правильный относительный импорт внутри src

if __name__ == "__main__":
    try:
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(project_root)

        app = RaZPlayer()
        app.mainloop()
    except KeyboardInterrupt:
        print("\nПрограмма была прервана пользователем.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Произошла критическая ошибка: {e}")