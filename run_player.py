# run_player.py
# Этот файл - единственная точка входа в приложение. Запускать нужно его.

from app.main_window import RaZPlayer

if __name__ == "__main__":
    try:
        app = RaZPlayer()
        app.mainloop()
    except KeyboardInterrupt:
        print("\nПрограмма была прервана пользователем.")
    except Exception as e:
        print(f"Произошла критическая ошибка: {e}")