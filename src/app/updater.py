# app/updater.py
import requests
import sys
import os
import subprocess
import json
from tkinter import messagebox
from packaging import version

VERSION_URL = "https://raw.githubusercontent.com/kutuleek0/RaZ-Music-player-With-love-from-kutuleek/main/version.json"

def check_for_updates(current_version_str):
    try:
        response = requests.get(VERSION_URL, timeout=5)
        response.raise_for_status()
        
        # Более надежная проверка на JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}. Ответ сервера:\n{response.text[:200]}...")
            return

        latest_version_str = data.get("latest_version")
        download_url = data.get("download_url")
        changelog_items = data.get("changelog", ["Нет информации об изменениях."])

        if not latest_version_str or not download_url:
            print("Ошибка: в version.json отсутствуют ключи 'latest_version' или 'download_url'.")
            return

        current_version = version.parse(current_version_str)
        latest_version = version.parse(latest_version_str)

        if latest_version > current_version:
            changelog_text = "\nЧто нового:\n" + "\n".join(f"- {item}" for item in changelog_items)
            message = (f"Доступна новая версия RaZ Player ({latest_version}).\n"
                       f"Ваша версия: {current_version}.\n\n"
                       f"{changelog_text}\n\n"
                       f"Хотите обновиться сейчас?")
            
            if messagebox.askyesno("Доступно обновление", message):
                download_and_install(download_url)
        else:
            print("У вас последняя версия программы.")

    except requests.exceptions.RequestException as e:
        print(f"Ошибка проверки обновлений: не удалось подключиться к серверу. {e}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка при проверке обновлений: {e}")

def download_and_install(url):
    # (Этот метод остается без изменений)
    try:
        current_exe = os.path.basename(sys.executable)
        new_exe_temp_name = f"{current_exe}.new"
        messagebox.showinfo("Загрузка обновления", "Начинается загрузка обновления. Приложение закроется и перезапустится автоматически.")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(new_exe_temp_name, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        script_content = f"""@echo off\necho Ожидание закрытия RaZ Player...\ntimeout /t 2 /nobreak > NUL\necho Замена файла...\nmove /Y "{new_exe_temp_name}" "{current_exe}" > NUL\necho Запуск обновленного RaZ Player...\nstart "" "{current_exe}"\necho Удаление временного файла...\n(goto) 2>nul & del "%~f0" """.strip()
        script_path = "update_installer.bat"
        with open(script_path, "w", encoding="cp866") as f: f.write(script_content)
        subprocess.Popen([script_path])
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("Ошибка обновления", f"Не удалось завершить обновление: {e}")
        if os.path.exists(new_exe_temp_name): os.remove(new_exe_temp_name)