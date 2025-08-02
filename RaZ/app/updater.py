# app/updater.py
import requests
import sys
import os
import subprocess
from tkinter import messagebox
from packaging import version

# URL к файлу version.json в вашем GitHub репозитории.
# ЗАМЕНИТЕ 'ВАШ_ЛОГИН' и 'ВАШ_РЕПОЗИТОРИЙ' на свои.
VERSION_URL = "https://raw.githubusercontent.com/ВАШ_ЛОГИН/ВАШ_РЕПОЗИТОРИЙ/main/version.json"

def check_for_updates(current_version_str):
    try:
        response = requests.get(VERSION_URL)
        response.raise_for_status() # Проверка на ошибки HTTP
        
        data = response.json()
        latest_version_str = data.get("latest_version")
        download_url = data.get("download_url")

        current_version = version.parse(current_version_str)
        latest_version = version.parse(latest_version_str)

        if latest_version > current_version:
            print(f"Доступно обновление: {latest_version}")
            if messagebox.askyesno("Доступно обновление", f"Доступна новая версия RaZ Player ({latest_version}).\nВаша версия: {current_version}.\n\nХотите обновиться сейчас?"):
                download_and_install(download_url)
        else:
            print("У вас последняя версия программы.")

    except requests.exceptions.RequestException as e:
        print(f"Ошибка проверки обновлений: не удалось подключиться к серверу. {e}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка при проверке обновлений: {e}")

def download_and_install(url):
    try:
        # Имя текущего исполняемого файла
        current_exe = os.path.basename(sys.executable) # например, 'RaZPlayer.exe'
        
        # Скачиваем новый файл с временным именем
        new_exe_temp_name = f"{current_exe}.new"
        
        print(f"Начало загрузки с {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(new_exe_temp_name, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Загрузка завершена.")

        # Создаем .bat скрипт для замены файла и перезапуска
        script_content = f"""
@echo off
echo Ожидание закрытия RaZ Player...
timeout /t 2 /nobreak > NUL
echo Замена файла...
move /Y "{new_exe_temp_name}" "{current_exe}" > NUL
echo Запуск обновленного RaZ Player...
start "" "{current_exe}"
echo Удаление временного файла...
del "%~f0"
"""
        script_path = "update_installer.bat"
        with open(script_path, "w") as f:
            f.write(script_content)

        # Запускаем скрипт и выходим из основного приложения
        subprocess.Popen([script_path])
        sys.exit(0)

    except Exception as e:
        messagebox.showerror("Ошибка обновления", f"Не удалось завершить обновление: {e}")
        # Удаляем временный файл, если он был создан
        if os.path.exists(new_exe_temp_name):
            os.remove(new_exe_temp_name)