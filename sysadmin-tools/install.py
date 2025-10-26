#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
import getpass
import platform
import json
import requests
import base64
import random
import string

# --- Helper Functions ---

def command_exists(command):
    """Function to check if a command exists"""
    return shutil.which(command) is not None

def print_separator():
    """Function to print a separator line"""
    print("----------------------------------------------------")

def print_header(title):
    """Function to print a header for a section"""
    print_separator()
    print(title)
    print_separator()

def run_command(command, check=True, input_data=None):
    """Runs a command in the shell and returns its output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=True,
            text=True,
            encoding='utf-8',
            input=input_data
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Ошибка выполнения команды: {e.cmd}")
        print(f"Код возврата: {e.returncode}")
        print(f"Вывод: {e.stdout}")
        print(f"Ошибка: {e.stderr}")
        raise

def main():
    # --- Welcome Message ---
    print_header("Добро пожаловать в скрипт автоматической установки!")
    print("Этот скрипт поможет вам настроить и запустить")
    print("FPTN-сервер, Telegram-бота и Grafana для мониторинга.\n")

    # --- Dependency Checks ---
    print_header("Проверка зависимостей...")
    deps = ["docker", "curl", "jq", "openssl", "git"]
    for dep in deps:
        if not command_exists(dep):
            print(f"Ошибка: '{dep}' не найден. Пожалуйста, установите его.")
            if dep in ["docker"]:
                print("Инструкция по установке Docker: https://docs.docker.com/engine/install/ubuntu/")
            elif dep == "jq":
                print("Вы можете установить его командой: sudo apt-get install jq")
            exit(1)
    print("Все необходимые зависимости найдены.\n")

    # --- Gather User Input ---
    print_header("Сбор необходимых данных")
    install_fptn_server = input("Хотите установить FPTN-сервер на этой машине? (y/n): ").lower() == 'y'
    public_ip = input("Введите публичный IP-адрес этого сервера: ")
    telegram_api_token = getpass.getpass("Введите API-токен вашего Telegram-бота: ")

    if install_fptn_server:
        out_network_interface = input("Введите имя исходящего сетевого интерфейса (например, eth0): ")
        fptn_user = input("Введите имя нового пользователя FPTN: ")
        fptn_password = getpass.getpass("Введите пароль для нового пользователя: ")
        fptn_bandwidth = input("Введите ограничение скорости для пользователя (в Мбит/с): ")

    docker_username = input("Введите ваш логин от Docker Hub (оставьте пустым, если не хотите логиниться): ")
    if docker_username:
        docker_password = getpass.getpass("Введите ваш пароль от Docker Hub: ")
        run_command(f"echo '{docker_password}' | sudo docker login --username '{docker_username}' --password-stdin")

    prometheus_secret_key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    print(f"Секретный ключ для Prometheus сгенерирован: {prometheus_secret_key}")
    print("Он будет использован для настройки FPTN-сервера и Grafana.\n")


    # --- FPTN Server Installation ---
    if install_fptn_server:
        print_header("Установка FPTN-сервера")
        # 1. Determine architecture and latest version
        arch = platform.machine()
        if arch == "x86_64":
            arch = "amd64"
        elif arch == "aarch64":
            arch = "arm64"
        else:
            print(f"Ошибка: неподдерживаемая архитектура '{arch}'.")
            exit(1)
        print(f"Определена архитектура: {arch}")

        # 1b. Get repository URL from git and set fallback
        original_repo = "batchar2/fptn"
        try:
            git_url = run_command("git config --get remote.origin.url")
            repo_path = git_url.split('github.com/')[-1].replace('.git', '')
            print(f"Репозиторий определен как: {repo_path}")
        except Exception:
            print(f"Предупреждение: не удалось определить репозиторий GitHub из 'git remote'. Используется репозиторий по умолчанию: {original_repo}")
            repo_path = original_repo

        def fetch_latest_tag(repo):
            api_url = f"https://api.github.com/repos/{repo}/tags"
            try:
                response = requests.get(api_url)
                response.raise_for_status()
                tags = response.json()
                if tags:
                    return tags[0]['name']
                else:
                    print(f"Ошибка: не удалось получить последний тег из '{repo}'.")
                    print(f"Ответ от GitHub API: {response.text}")
                    return None
            except requests.exceptions.RequestException as e:
                print(f"Ошибка при запросе к GitHub API: {e}")
                return None

        latest_tag = fetch_latest_tag(repo_path)
        if not latest_tag:
            print(f"В репозитории '{repo_path}' не найдены релизы.")
            print(f"Попытка получить релиз из основного репозитория: {original_repo}")
            repo_path = original_repo
            latest_tag = fetch_latest_tag(repo_path)
            if not latest_tag:
                print(f"Ошибка: не удалось найти релизы и в основном репозитории '{repo_path}'.")
                exit(1)
        print(f"Последняя версия FPTN: {latest_tag}")

        # 2. Download and install .deb package
        deb_name = f"fptn-server-{latest_tag}-ubuntu22.04-{arch}.deb"
        download_url = f"https://github.com/{repo_path}/releases/download/{latest_tag}/{deb_name}"
        print(f"Загрузка пакета: {download_url}")
        run_command(f"curl -L -o {deb_name} {download_url}")
        print("Установка пакета...")
        run_command(f"sudo apt-get update && sudo apt-get install -y -f ./{deb_name}")
        os.remove(deb_name)
        print("Пакет FPTN-сервера успешно установлен.")

        # 3. Generate certificates
        print("Генерация SSL-сертификатов...")
        run_command("sudo mkdir -p /etc/fptn")
        run_command(f"sudo openssl genrsa -out /etc/fptn/server.key 2048")
        run_command(f"sudo openssl req -new -x509 -key /etc/fptn/server.key -out /etc/fptn/server.crt -days 365 -subj '/CN={public_ip}'")
        run_command(f"sudo openssl rsa -in /etc/fptn/server.key -pubout -out /etc/fptn/server.pub")
        print("Сертификаты успешно сгенерированы.")

        # 4. Configure server
        print("Настройка /etc/fptn/server.conf...")
        run_command(f"sudo sed -i 's/OUT_NETWORK_INTERFACE=.*/OUT_NETWORK_INTERFACE={out_network_interface}/' /etc/fptn/server.conf")
        run_command(f"sudo sed -i 's|SERVER_KEY=.*|SERVER_KEY=/etc/fptn/server.key|' /etc/fptn/server.conf")
        run_command(f"sudo sed -i 's|SERVER_CRT=.*|SERVER_CRT=/etc/fptn/server.crt|' /etc/fptn/server.conf")
        run_command(f"sudo sed -i 's|SERVER_PUB=.*|SERVER_PUB=/etc/fptn/server.pub|' /etc/fptn/server.conf")
        run_command(f"sudo sed -i 's/PROMETHEUS_SECRET_ACCESS_KEY=.*/PROMETHEUS_SECRET_ACCESS_KEY={prometheus_secret_key}/' /etc/fptn/server.conf")
        print("Конфигурация сервера обновлена.")

        # 5. Add user
        print_header("Создание пользователя FPTN")
        run_command(f"sudo fptn-passwd --add-user '{fptn_user}' --bandwidth '{fptn_bandwidth}'", input_data=f"{fptn_password}\n{fptn_password}\n")
        print(f"Пользователь '{fptn_user}' успешно создан.")

        # 6. Configure dnsmasq
        print("Установка и настройка dnsmasq...")
        run_command("sudo DEBIAN_FRONTEND=noninteractive apt-get install -y dnsmasq 2>&1")
        run_command("echo 'server=8.8.8.8' | sudo tee -a /etc/dnsmasq.conf")
        run_command("echo 'server=8.8.4.4' | sudo tee -a /etc/dnsmasq.conf")
        # Handle systemd-resolved conflict
        if "systemd-resolved" in run_command("sudo systemctl is-active systemd-resolved", check=False):
            run_command("sudo sed -i 's/#DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf")
            run_command("sudo systemctl restart systemd-resolved")
        run_command("sudo systemctl enable dnsmasq")
        run_command("sudo systemctl restart dnsmasq")
        print("dnsmasq настроен.")

        # 7. Start FPTN server
        print("Запуск FPTN-сервера...")
        run_command("sudo systemctl enable fptn-server")
        run_command("sudo systemctl start fptn-server")
        run_command("sudo systemctl status fptn-server")

    # --- Configure Telegram Bot ---
    print_header("Настройка Telegram-бота")
    os.chdir("telegram-bot")
    shutil.copy(".env.demo", ".env")
    run_command(f"sed -i 's/API_TOKEN=.*/API_TOKEN={telegram_api_token}/' .env")
    run_command(f"sed -i 's/FPTN_SERVER_HOST=.*/FPTN_SERVER_HOST={public_ip}/' .env")
    run_command(f"sed -i 's/FPTN_SERVER_PORT=.*/FPTN_SERVER_PORT=443/' .env")
    print(".env файл для бота успешно настроен.")
    shutil.copy("servers.json.demo", "servers.json")
    shutil.copy("servers_censored_zone.json.demo", "servers_censored_zone.json")
    print("Важно: не забудьте отредактировать 'servers.json' и 'servers_censored_zone.json'!")
    run_command("sudo docker compose build > /dev/null 2>&1")
    run_command("sudo docker compose up -d > /dev/null 2>&1")
    print("Telegram-бот успешно запущен!\n")
    os.chdir("..")

    # --- Configure Grafana ---
    print_header("Настройка Grafana")
    os.chdir("grafana")
    shutil.copy(".env.demo", ".env")
    run_command(f"sed -i 's/FPTN_HOST=.*/FPTN_HOST={public_ip}/' .env")
    run_command(f"sed -i 's/FPTN_PORT=.*/FPTN_PORT=443/' .env")
    run_command(f"sed -i 's/PROMETHEUS_SECRET_ACCESS_KEY=.*/PROMETHEUS_SECRET_ACCESS_KEY={prometheus_secret_key}/' .env")
    print(".env файл для Grafana успешно настроен.")
    run_command("sudo docker compose down && sudo docker compose up -d 2>&1")
    print("Grafana успешно запущена!\n")
    os.chdir("..")

    # --- Final Instructions ---
    print_header("Установка завершена!")
    print("- Telegram-бот запущен в фоновом режиме.")
    print(f"- Grafana доступна по адресу: http://{public_ip}:3000")
    print("  Логин/пароль по умолчанию: admin / admin (обязательно смените пароль!).")

    if install_fptn_server:
        print("- FPTN-сервер запущен и работает.")

        # Generate and display user token
        fingerprint = run_command("sudo openssl x509 -noout -fingerprint -md5 -in /etc/fptn/server.crt | cut -d'=' -f2 | tr -d ':' | tr 'A-F' 'a-f'")
        json_config = {
            "version": 1,
            "service_name": "MyFptnServer",
            "username": fptn_user,
            "password": fptn_password,
            "servers": [{
                "name": "MyFptnServer",
                "host": public_ip,
                "md5_fingerprint": fingerprint,
                "port": 443
            }]
        }
        base64_token = base64.b64encode(json.dumps(json_config).encode()).decode().rstrip("=")
        final_token = f"fptn:{base64_token}"

        print_separator()
        print("ВАШ ТОКЕН ДОСТУПА К FPTN-СЕРВЕРУ:")
        print(final_token)
        print_separator()

    print("\nДля остановки сервисов используйте 'docker-compose down' в директориях 'telegram-bot' и 'grafana'.")
    print_separator()

if __name__ == "__main__":
    main()
