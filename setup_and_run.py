# setup_and_run.py

import sys
import subprocess
import os
import webbrowser
from tkinter import messagebox, Tk

# --- Конфигурация ---
REQUIRED_PACKAGES = {
    "customtkinter": "customtkinter",
    "pygame": "pygame",
    "yt_dlp": "yt-dlp",
    "requests": "requests",
    "Pillow": "Pillow",
    "tkcolorpicker": "tkcolorpicker",
    "packaging": "packaging"  # Добавлено для системы автообновления
}
FFMPEG_DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
MAIN_SCRIPT = "run_player.py"

# --- Функции ---

def check_and_install_packages():
    """Проверяет и предлагает установить недостающие Python-пакеты."""
    print("Проверка необходимых Python-пакетов...")
    missing_packages = []
    for package_name, import_name in REQUIRED_PACKAGES.items():
        try:
            # Для Pillow импорт отличается от имени пакета
            if import_name == "Pillow":
                __import__("PIL")
            else:
                __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)

    if not missing_packages:
        print("Все пакеты на месте.")
        return True

    # Скрываем главное окно Tkinter, чтобы было видно только messagebox
    root = Tk()
    root.withdraw()
    
    msg = (f"Для работы программы не хватает следующих модулей:\n"
           f"{', '.join(missing_packages)}\n\n"
           f"Установить их сейчас? (потребуется интернет)")

    if messagebox.askyesno("Требуется установка", msg):
        for package in missing_packages:
            print(f"Установка {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"{package} успешно установлен.")
            except subprocess.CalledProcessError:
                messagebox.showerror("Ошибка установки", f"Не удалось установить {package}. Пожалуйста, установите его вручную, выполнив в командной строке: pip install {package}")
                return False
        return True
    else:
        messagebox.showinfo("Отмена", "Установка отменена. Программа не может быть запущена.")
        return False

def check_ffmpeg():
    """Проверяет наличие ffmpeg в системном PATH или в папке со скриптом."""
    print("Проверка наличия ffmpeg...")
    try:
        # Флаг для Windows, чтобы не мигало черное окно консоли
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True, creationflags=creation_flags)
        print("ffmpeg найден в системе.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ffmpeg не найден в системе. Проверяем локальную папку...")

    if os.path.exists("ffmpeg.exe"):
        print("ffmpeg.exe найден в папке со скриптом.")
        return True

    root = Tk()
    root.withdraw()
    msg = ("Для скачивания музыки программе необходим компонент 'ffmpeg'.\n\n"
           "Нажмите 'ОК', чтобы открыть страницу для скачивания в браузере.\n\n"
           "Инструкция:\n"
           "1. На странице скачайте архив 'ffmpeg-release-essentials.zip'.\n"
           "2. Распакуйте архив.\n"
           "3. Из папки 'bin' скопируйте файл 'ffmpeg.exe' и положите его в ту же папку, где находится этот плеер.")
    
    if messagebox.askokcancel("Компонент не найден", msg):
        webbrowser.open(FFMPEG_DOWNLOAD_URL)
    
    return False

# --- Основной процесс запуска ---

if __name__ == "__main__":
    if check_and_install_packages():
        if check_ffmpeg():
            print("Все проверки пройдены. Запускаем основной плеер...")
            # Запускаем основной скрипт плеера
            subprocess.run([sys.executable, MAIN_SCRIPT])
        else:
            print("Запуск невозможен: отсутствует ffmpeg.")
    else:
        print("Запуск невозможен: отсутствуют необходимые Python-пакеты.")