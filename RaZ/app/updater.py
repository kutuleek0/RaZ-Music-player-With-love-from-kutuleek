# app/updater.py
import requests
import sys
import os
import subprocess
from tkinter import messagebox
from packaging import version

# --- ИСПРАВЛЕНИЕ: URL указывает на "raw" (сырую) версию файла на GitHub ---
# Это гарантирует, что мы получаем JSON, а не HTML страницу
VERSION_URL = "https://raw.githubusercontent.com/kutuleek0/RaZ-Music-player-With-love-from-kutuleek/refs/heads/main/version.json"

def check_for_updates(current_version_str):
    try:
        response = requests.get(VERSION_URL, timeout=5) # Добавлен таймаут для надежности
        response.raise_for_status()
        
        data = response.json()
        latest_version_str = data.get("latest_version")
        download_url = data.get("download_url")
        changelog_items = data.get("changelog", ["Нет информации об изменениях."])

        current_version = version.parse(current_version_str)
        latest_version = version.parse(latest_version_str)

        if latest_version > current_version:
            print(f"Доступно обновление: {latest_version}")
            
            # --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Формируем красивое сообщение с изменениями ---
            changelog_text = "\nЧто нового:\n"
            for item in changelog_items:
                changelog_text += f"- {item}\n"

            message = (
                f"Доступна новая версия RaZ Player ({latest_version}).\n"
                f"Ваша версия: {current_version}.\n\n"
                f"{changelog_text}\n"
                f"Хотите обновиться сейчас?"
            )
            
            if messagebox.askyesno("Доступно обновление", message):
                download_and_install(download_url)
        else:
            print("У вас последняя версия программы.")

    except requests.exceptions.RequestException as e:
        print(f"Ошибка проверки обновлений: не удалось подключиться к серверу. {e}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка при проверке обновлений: {e}")

def download_and_install(url):
    try:
        current_exe = os.path.basename(sys.executable)
        new_exe_temp_name = f"{current_exe}.new"
        
        print(f"Начало загрузки с {url}...")
        
        # Показываем информационное окно о начале загрузки
        messagebox.showinfo("Загрузка обновления", "Начинается загрузка обновления. Приложение закроется и перезапустится автоматически.")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(new_exe_temp_name, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Загрузка завершена.")

        script_content = f"""
@echo off
echo Ожидание закрытия RaZ Player...
timeout /t 2 /nobreak > NUL
echo Замена файла...
move /Y "{new_exe_temp_name}" "{current_exe}" > NUL
echo Запуск обновленного RaZ Player...
start "" "{current_exe}"
echo Удаление временного файла...
(goto) 2>nul & del "%~f0"
"""
        script_path = "update_installer.bat"
        with open(script_path, "w", encoding="cp866") as f: # Используем кодировку для .bat
            f.write(script_content)

        subprocess.Popen([script_path])
        sys.exit(0)

    except Exception as e:
        messagebox.showerror("Ошибка обновления", f"Не удалось завершить обновление: {e}")
        if os.path.exists(new_exe_temp_name):

            os.remove(new_exe_temp_name)
