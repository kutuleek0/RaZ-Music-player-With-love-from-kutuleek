# src/run_player.py
from app.main_window import RaZPlayer

if __name__ == "__main__":
    try:
        app = RaZPlayer()
        app.mainloop()
    except KeyboardInterrupt:
        print("\nПрограмма была прервана пользователем.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Произошла критическая ошибка: {e}")