#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Программа для синхронизации данных с OWEN Cloud API.
Отслеживает обновления данных в облаке и записывает их в CSV файл.
"""

import requests
import json
import time
import csv
import os
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple


# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================

API_URL = "https://api.owencloud.ru/v1"
LOGIN = "erofeyivanov@gmail.com"  # Замените на ваш логин
PASSWORD = "Security_532"  # Замените на ваш пароль

# ID параметров (будут определены автоматически при первом запуске)
SYNCHRONIZATION_PARAM_ID = None  # ID параметра synchronization
INDICATOR_PARAM_ID = None  # ID параметра indicator_of_new_cycle
DEVICE_ID = None  # ID прибора

# Настройки синхронизации
POLL_INTERVAL_ACTIVE = 0.3  # Интервал опроса в активном окне (секунды)
POLL_INTERVAL_IDLE = 5  # Интервал опроса вне активного окна (секунды)
SYNC_CYCLE_MIN = 50  # Минимальное время цикла (секунды)
SYNC_CYCLE_MAX = 70  # Максимальное время цикла (секунды)
ACTIVE_WINDOW_START = 48  # Начало активного окна относительно последнего обновления (сек)
ACTIVE_WINDOW_END = 72  # Конец активного окна (сек)

# Файл для сохранения данных
CSV_FILENAME = "owen_cloud_data.csv"
CONFIG_FILENAME = "owen_config.json"

# Глобальные переменные для хранения состояния
token_data = {
    "token": None,
    "timestamp": 0
}

device_config = {
    "device_id": None,
    "synchronization_param_id": None,
    "indicator_param_id": None,
    "parameter_ids": [],
    "parameter_names": {}
}


# =============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С КОНФИГУРАЦИЕЙ
# =============================================================================

def load_config() -> bool:
    """
    Загрузить конфигурацию из файла.
    
    Возвращает:
        bool: True если конфигурация успешно загружена
    """
    global device_config
    
    if not os.path.exists(CONFIG_FILENAME):
        return False
    
    try:
        with open(CONFIG_FILENAME, 'r', encoding='utf-8') as f:
            device_config = json.load(f)
        print(f"[+] Конфигурация загружена из {CONFIG_FILENAME}")
        return True
    except Exception as e:
        print(f"[!] Ошибка загрузки конфигурации: {e}")
        return False


def save_config():
    """Сохранить конфигурацию в файл."""
    try:
        with open(CONFIG_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(device_config, f, indent=2, ensure_ascii=False)
        print(f"[+] Конфигурация сохранена в {CONFIG_FILENAME}")
    except Exception as e:
        print(f"[!] Ошибка сохранения конфигурации: {e}")


# =============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С API
# =============================================================================

def get_auth_token(login: str, password: str, force_refresh: bool = False) -> Optional[str]:
    """
    Получить токен авторизации от OWEN Cloud API.
    Использует кэшированный токен, если он еще действителен.
    
    Аргументы:
        login (str): Логин пользователя
        password (str): Пароль пользователя
        force_refresh (bool): Принудительно обновить токен
    
    Возвращает:
        str: Токен авторизации или None в случае ошибки
    """
    global token_data
    
    # Проверяем, есть ли действительный токен (действителен 18 минут)
    current_time = time.time()
    if not force_refresh and token_data["token"] and (current_time - token_data["timestamp"]) < 1080:
        return token_data["token"]
    
    auth_endpoint = f"{API_URL}/auth/open"
    
    auth_data = {
        "login": login,
        "password": password
    }
    
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json"
    }
    
    try:
        print("[*] Получение нового токена авторизации...")
        
        response = requests.post(
            auth_endpoint,
            json=auth_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            token = response.json().get("token")
            if token:
                token_data["token"] = token
                token_data["timestamp"] = current_time
                print(f"[+] Токен успешно получен!")
                return token
            else:
                print("[!] Ошибка: токен не найден в ответе сервера")
                return None
        else:
            print(f"[!] Ошибка авторизации: HTTP {response.status_code}")
            print(f"    Ответ сервера: {response.text}")
            return None
            
    except Exception as e:
        print(f"[!] Ошибка при получении токена: {e}")
        return None


def get_devices(token: str) -> Optional[List[Dict[str, Any]]]:
    """
    Получить список подключенных приборов.
    
    Аргументы:
        token (str): Токен авторизации
    
    Возвращает:
        list: Список приборов или None в случае ошибки
    """
    devices_endpoint = f"{API_URL}/device/index"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "*/*",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            devices_endpoint,
            json={},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            print("[!] Токен истек, требуется обновление")
            return None
        else:
            print(f"[!] Ошибка получения списка приборов: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[!] Ошибка при получении списка приборов: {e}")
        return None


def get_device_parameters(token: str, device_id: int) -> Optional[Dict[str, Any]]:
    """
    Получить параметры конкретного прибора.
    
    Аргументы:
        token (str): Токен авторизации
        device_id (int): ID прибора
    
    Возвращает:
        dict: Информация о приборе и его параметрах или None в случае ошибки
    """
    parameters_endpoint = f"{API_URL}/device/{device_id}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "*/*",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            parameters_endpoint,
            json=[],
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            print("[!] Токен истек, требуется обновление")
            return None
        else:
            print(f"[!] Ошибка получения параметров: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[!] Ошибка при получении параметров: {e}")
        return None


def write_parameter(token: str, param_id: int, value: str, timeout: int = 60) -> bool:
    """
    Записать значение в параметр прибора.
    
    Аргументы:
        token (str): Токен авторизации
        param_id (int): ID параметра
        value (str): Новое значение
        timeout (int): Таймаут записи в секундах
    
    Возвращает:
        bool: True если запись успешна
    """
    write_endpoint = f"{API_URL}/parameters/write-data"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "*/*",
        "Content-Type": "application/json"
    }
    
    data = {
        "timeout": timeout,
        "sync": True,
        "data": [
            {"id": param_id, "value": str(value)}
        ]
    }
    
    try:
        response = requests.post(
            write_endpoint,
            json=data,
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            if "writeGroupId" in result:
                return True
            else:
                print(f"[!] Неожиданный ответ при записи: {result}")
                return False
        elif response.status_code == 401:
            print("[!] Токен истек при записи")
            return False
        else:
            print(f"[!] Ошибка записи параметра: HTTP {response.status_code}")
            print(f"    Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"[!] Ошибка при записи параметра: {e}")
        return False


# =============================================================================
# ФУНКЦИИ ДЛЯ ИНИЦИАЛИЗАЦИИ
# =============================================================================

def refresh_device_config(token: str) -> bool:
    """
    Обновить конфигурацию устройства (получить свежие ID всех параметров).
    
    Аргументы:
        token (str): Токен авторизации
    
    Возвращает:
        bool: True если обновление успешно
    """
    global device_config
    
    print("\n[*] Обновление конфигурации устройства...")
    
    # Получаем список приборов
    devices = get_devices(token)
    if not devices or len(devices) == 0:
        print("[!] Не удалось получить список приборов")
        return False
    
    # -------------------------------------------------------------------------
    # ЛОГИКА ВЫБОРА ПРИБОРА
    # -------------------------------------------------------------------------
    # Если у нас уже был device_id, пробуем найти прибор с этим ID
    # Если нет, или прибор не найден - берем первый
    
    target_device = None
    current_device_id = device_config.get("device_id")
    
    # Если у нас вообще нет конфига, берем первый прибор
    if not current_device_id:
         if isinstance(devices, list):
            target_device = devices[0]
         else:
            target_device = devices
    else:
        # Пытаемся найти наш прибор в списке
        if isinstance(devices, list):
            for d in devices:
                if d.get("id") == current_device_id:
                    target_device = d
                    break
            # Если не нашли старый прибор - берем первый? 
            # Лучше взять первый, так как пользователь мог заменить прибор
            if not target_device:
                print(f"[*] Старый прибор ID {current_device_id} не найден, берем первый доступный")
                target_device = devices[0]
        else:
            target_device = devices

    if not target_device: 
         print("[!] Не удалось определить целевой прибор")
         return False

    device_id = target_device.get("id")
    if not device_id:
        print("[!] Не удалось получить ID прибора")
        return False
    
    print(f"[+] Прибор: {target_device.get('name', 'Без названия')} (ID: {device_id})")
    device_config["device_id"] = device_id
    
    # Получаем параметры прибора
    device_info = get_device_parameters(token, device_id)
    if not device_info:
        print("[!] Не удалось получить параметры прибора")
        return False
    
    parameters = device_info.get("parameters", [])
    if not parameters:
        print("[!] Параметры прибора не найдены")
        return False
    
    print(f"[+] Найдено параметров: {len(parameters)}")
    
    # Очищаем списки перед обновлением
    device_config["parameter_ids"] = []
    device_config["parameter_names"] = {}
    
    # Ищем параметры synchronization и indicator_of_new_cycle
    sync_param_id = None
    indicator_param_id = None
    
    for param in parameters:
        param_name = param.get("name", "").lower()
        param_id = param.get("id")
        
        # Обновленный поиск: ищем по имени или коду
        # "synchronization"
        if ("synchronization" in param_name) or (param.get("code", "").lower() == "synchronization"):
            sync_param_id = param_id
            print(f"[+] Найден параметр synchronization: ID {param_id}")
        
        # "indicator_of_new_cycle"
        if ("indicator" in param_name and "cycle" in param_name) or (param.get("code", "").lower() == "indicator_of_new_cycle"):
            indicator_param_id = param_id
            print(f"[+] Найден параметр indicator_of_new_cycle: ID {param_id}")
        
        # Сохраняем все параметры
        device_config["parameter_ids"].append(param_id)
        device_config["parameter_names"][param_id] = param.get("name", f"Param_{param_id}")
    
    if not sync_param_id:
        print("[!] ВНИМАНИЕ: Параметр 'synchronization' не найден автоматически!")
        # Если не нашли, и это не интерактивный режим, то это проблема.
        # Но мы не будем прерывать, просто будем надеяться что пользователь поправит конфиг или это сбой
    
    if not indicator_param_id:
        print("[!] ВНИМАНИЕ: Параметр 'indicator_of_new_cycle' не найден автоматически!")
    
    # Обновляем конфиг только если нашли параметры (или если их не было совсем)
    if sync_param_id:
        device_config["synchronization_param_id"] = sync_param_id
    if indicator_param_id:
        device_config["indicator_param_id"] = indicator_param_id
    
    # Сохраняем конфигурацию
    save_config()
    
    # Если поменялись параметры, нужно переинициализировать CSV (добавить новые колонки)
    # Но мы не можем просто так менять заголовки в существующем файле.
    # Поэтому просто уведомим, что состав параметров изменился.
    print("[+] Конфигурация обновлена.")
    return True

def initialize_device_config(token: str) -> bool:
    """Wrapper for backward compatibility calling refresh_device_config"""
    return refresh_device_config(token)


def get_initial_indicator_value(token: str) -> int:
    """
    Получить текущее значение indicator_of_new_cycle из облака.
    
    Аргументы:
        token (str): Токен авторизации
    
    Возвращает:
        int: Текущее значение индикатора (0 или 1)
    """
    parameters = get_current_parameters(token)
    if parameters:
        indicator_value = parameters.get(device_config["indicator_param_id"])
        if indicator_value is not None:
            try:
                return int(float(indicator_value))
            except:
                pass
    return 0


# =============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С CSV
# =============================================================================

def initialize_csv():
    """Инициализировать CSV файл с заголовками."""
    if os.path.exists(CSV_FILENAME):
        print(f"[*] CSV файл {CSV_FILENAME} уже существует")
        return
    
    headers = ["timestamp", "datetime"]
    
    # Добавляем названия параметров
    for param_id in device_config["parameter_ids"]:
        param_name = device_config["parameter_names"].get(param_id, f"Param_{param_id}")
        headers.append(f"{param_name} (ID:{param_id})")
    
    try:
        with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        print(f"[+] CSV файл {CSV_FILENAME} создан с заголовками")
    except Exception as e:
        print(f"[!] Ошибка создания CSV файла: {e}")


def save_to_csv(parameters_data: Dict[int, Any]):
    """
    Сохранить данные параметров в CSV файл.
    
    Аргументы:
        parameters_data (dict): Словарь {param_id: value}
    """
    current_time = time.time()
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    row = [current_time, current_datetime]
    
    # Добавляем значения параметров в том же порядке, что и в заголовках
    for param_id in device_config["parameter_ids"]:
        value = parameters_data.get(param_id, "N/A")
        row.append(value)
    
    try:
        with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)
        print(f"[+] Данные записаны в CSV: {current_datetime}")
    except Exception as e:
        print(f"[!] Ошибка записи в CSV: {e}")


# =============================================================================
# ОСНОВНАЯ ЛОГИКА СИНХРОНИЗАЦИИ
# =============================================================================

def get_current_parameters(token: str) -> Optional[Dict[int, Any]]:
    """
    Получить текущие значения всех параметров.
    
    Аргументы:
        token (str): Токен авторизации
    
    Возвращает:
        dict: Словарь {param_id: value} или None в случае ошибки
    """
    device_info = get_device_parameters(token, device_config["device_id"])
    if not device_info:
        return None
    
    parameters = device_info.get("parameters", [])
    result = {}
    
    for param in parameters:
        param_id = param.get("id")
        value = param.get("value", "N/A")
        result[param_id] = value
    
    return result


def synchronization_loop():
    """
    Основной цикл синхронизации.
    Отслеживает изменения параметра synchronization и записывает данные при обновлении.
    """
    print("\n" + "=" * 80)
    print(">>> ЗАПУСК ЦИКЛА СИНХРОНИЗАЦИИ <<<")
    print("=" * 80)
    
    # Получаем токен
    token = get_auth_token(LOGIN, PASSWORD)
    if not token:
        print("[!] Не удалось получить токен. Завершение.")
        return
    
    # Загружаем конфигурацию
    # Если загрузка не удалась, или конфиг пустой, или пользователь попросил - обновляем
    config_loaded = load_config()
    
    # Принудительно проверяем/обновляем конфиг при старте
    # Это решает проблему устаревших ID при следующем запуске
    print("[*] Проверка актуальности конфигурации...")
    try:
        # Пробный запрос параметров
        test_params = get_current_parameters(token)
        # Если параметры не получены или в них нет нашего sync параметра -> обновляем
        if not test_params or (device_config.get("synchronization_param_id") not in test_params):
             print("[!] Конфигурация устарела или невалидна. Запуск обновления...")
             if not refresh_device_config(token):
                print("[!] Не удалось обновить конфигурацию. Продолжаем со старой...")
        else:
             print("[+] Конфигурация выглядит актуальной.")
             
    except Exception as e:
        print(f"[!] Ошибка при проверке конфига: {e}")
        refresh_device_config(token)
    
    # Инициализируем CSV файл
    initialize_csv()
    
    # Получаем текущее значение indicator_of_new_cycle из облака
    current_indicator_value = get_initial_indicator_value(token)
    print(f"[*] Текущее значение indicator_of_new_cycle в облаке: {current_indicator_value}")
    
    # Переменные для отслеживания синхронизации
    last_sync_value = None
    last_update_time = None
    cycle_times = []
    
    print(f"\n[*] Начинаем мониторинг параметра synchronization (ID: {device_config['synchronization_param_id']})")
    print(f"[*] Параметр indicator_of_new_cycle (ID: {device_config['indicator_param_id']})")
    print(f"[*] Активное окно опроса: {ACTIVE_WINDOW_START}-{ACTIVE_WINDOW_END} сек после обновления")
    print(f"[*] Интервал опроса: активный={POLL_INTERVAL_ACTIVE}с, пассивный={POLL_INTERVAL_IDLE}с")
    print(f"[*] Нажмите Ctrl+C для остановки\n")
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while True:
        try:
            # Определяем интервал опроса в зависимости от времени с последнего обновления
            if last_update_time:
                time_since_update = time.time() - last_update_time
                
                # Если находимся в активном окне ожидания обновления, опрашиваем часто
                if ACTIVE_WINDOW_START <= time_since_update <= ACTIVE_WINDOW_END:
                    poll_interval = POLL_INTERVAL_ACTIVE
                else:
                    poll_interval = POLL_INTERVAL_IDLE
            else:
                # Первоначально опрашиваем часто до первого обновления
                poll_interval = POLL_INTERVAL_ACTIVE
            
            # Получаем текущие параметры
            parameters = get_current_parameters(token)
            
            if not parameters:
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print("[!] Слишком много ошибок подряд, обновляем токен...")
                    token = get_auth_token(LOGIN, PASSWORD, force_refresh=True)
                    if not token:
                        print("[!] Не удалось обновить токен. Завершение.")
                        break
                    consecutive_errors = 0
                time.sleep(poll_interval)
                continue
            
            consecutive_errors = 0
            
            # Получаем значение synchronization
            sync_value = parameters.get(device_config["synchronization_param_id"])
            
            if sync_value is None:
                print(f"[!] Не удалось получить значение synchronization (ID: {device_config['synchronization_param_id']})")
                consecutive_errors += 1
                
                # Если параметр не найден несколько раз подряд -> возможно IDs поменялись
                if consecutive_errors >= 3:
                     print("[!] Возможно изменилась конфигурация устройства. Запускаем авто-обновление...")
                     if refresh_device_config(token):
                         consecutive_errors = 0
                         # Пробуем сразу получить данные с новым конфигом
                         print("[*] Повторная попытка чтения данных с новой конфигурацией...")
                         continue
                     else:
                         print("[!] Не удалось обновить конфигурацию.")
                
                time.sleep(poll_interval)
                continue
            
            # Преобразуем в число для сравнения
            try:
                sync_value_num = float(sync_value)
            except (ValueError, TypeError):
                print(f"[!] Некорректное значение synchronization: {sync_value}")
                time.sleep(poll_interval)
                continue
            
            # Проверяем, изменилось ли значение
            if last_sync_value is not None and sync_value_num != last_sync_value:
                current_time = time.time()
                
                print(f"\n[!] ОБНОВЛЕНИЕ ДАННЫХ ОБНАРУЖЕНО!")
                print(f"    Значение synchronization: {last_sync_value} → {sync_value_num}")
                
                 # ---------------------------------------------------------------------
                # ФИЛЬТРАЦИЯ "ДРЕБЕЗГА" / ЧАСТЫХ ОБНОВЛЕНИЙ
                # ---------------------------------------------------------------------
                # Если прошло меньше минимального времени цикла, игнорируем это обновление
                if last_update_time:
                    time_since_update_check = current_time - last_update_time
                    if time_since_update_check < SYNC_CYCLE_MIN:
                         print(f"    [i] Игнорирование частого обновления ({time_since_update_check:.1f} сек < {SYNC_CYCLE_MIN} сек)")
                         # Не обновляем last_sync_value, чтобы в следующем цикле снова сравнить с ним
                         # Но если это реальное изменение, sync_value_num будет другим. 
                         # Чтобы не застрять, обновляем last_sync_value? 
                         # Нет, если мы считаем это шумом, мы должны ждать пока не пройдет время.
                         # Но если значение реально поменялось и стоит, мы должны его принять, но только если прошло время.
                         # Так что просто пропускаем иттерацию
                         time.sleep(poll_interval)
                         continue
                
                # Рассчитываем время цикла
                if last_update_time:
                    cycle_time = current_time - last_update_time
                    cycle_times.append(cycle_time)
                    
                    # Оставляем только последние 10 измерений для расчета среднего
                    if len(cycle_times) > 10:
                        cycle_times.pop(0)
                    
                    estimated_cycle_time = sum(cycle_times) / len(cycle_times)
                    print(f"    Время цикла: {cycle_time:.2f} сек (среднее: {estimated_cycle_time:.2f} сек)")
                    print(f"    Разброс циклов: {min(cycle_times):.2f} - {max(cycle_times):.2f} сек")
                
                last_update_time = current_time
                
                # ВАЖНО: Сначала записываем indicator_of_new_cycle в прибор
                # ЖЕСТКОЕ ЧЕРЕДОВАНИЕ: 0 -> 1 -> 0 -> 1
                # Не доверяем значению из облака, так как оно может быть устаревшим,
                # а используем наше внутреннее состояние current_indicator_value, которое мы обновляем после успешной записи.
                
                new_indicator_value = 1 if current_indicator_value == 0 else 0
                
                print(f"[*] Записываем indicator_of_new_cycle: {current_indicator_value} → {new_indicator_value}")
                
                write_success = write_parameter(token, device_config["indicator_param_id"], new_indicator_value)
                
                if write_success:
                    print(f"[+] Параметр indicator_of_new_cycle успешно записан!")
                    
                    # Рассчитываем задержку записи
                    write_time = time.time()
                    delay = write_time - current_time
                    print(f"[+] Задержка записи: {delay:.3f} сек")
                    
                    # Обновляем значение индикатора в словаре параметров
                    parameters[device_config["indicator_param_id"]] = new_indicator_value
                    
                    # Обновляем наше локальное состояние ТОЛЬКО после успеха
                    current_indicator_value = new_indicator_value
                else:
                    print(f"[!] Ошибка записи параметра indicator_of_new_cycle")
                    print(f"[!] В CSV будет записано старое значение из облака")
                
                # Сохраняем данные в CSV (с обновленным значением индикатора если запись успешна)
                save_to_csv(parameters)
                
                # Вычисляем и выводим информацию о следующем ожидаемом обновлении
                if cycle_times:
                    avg_cycle = sum(cycle_times) / len(cycle_times)
                    next_update_time = avg_cycle
                    print(f"[*] Ожидание следующего обновления (примерно {avg_cycle:.0f}±{max(cycle_times)-min(cycle_times):.0f} сек)...\n")
                else:
                    print(f"[*] Ожидание следующего обновления...\n")
            
            last_sync_value = sync_value_num
            
            # Выводим статус (не слишком часто)
            if last_update_time:
                time_since_update = time.time() - last_update_time
                # Выводим статус каждые 10 секунд, если находимся в пассивном режиме
                if int(time_since_update) % 10 == 0 and poll_interval == POLL_INTERVAL_IDLE:
                    in_active_window = ACTIVE_WINDOW_START <= time_since_update <= ACTIVE_WINDOW_END
                    status = "АКТИВНОЕ ОКНО" if in_active_window else "пассивный режим"
                    print(f"[*] Ожидание ({status}): {time_since_update:.0f} сек с последнего обновления, sync={sync_value_num}")
            else:
                print(f"[*] Инициализация... (sync={sync_value_num})")
            
            time.sleep(poll_interval)
            
        except KeyboardInterrupt:
            print("\n\n[*] Получен сигнал остановки (Ctrl+C)")
            print("[*] Завершение программы...")
            break
        except Exception as e:
            print(f"\n[!] Неожиданная ошибка: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)
    
    print("\n" + "=" * 80)
    print("[+] ПРОГРАММА ЗАВЕРШЕНА")
    print("=" * 80)


# =============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# =============================================================================

def main():
    """Главная функция программы."""
    # Настройка кодировки вывода для Windows
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    
    synchronization_loop()


# =============================================================================
# ТОЧКА ВХОДА В ПРОГРАММУ
# =============================================================================

if __name__ == "__main__":
    main()
