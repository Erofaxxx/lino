# Инструкция по запуску Owen Cloud Synchronizer + Web Interface на Ubuntu

Эта инструкция поможет настроить автоматический сбор данных с Owen Cloud и веб-интерфейс для их просмотра и скачивания.

## 1. Подготовка сервера

Подключитесь к серверу по SSH.

### Обновление системы и установка Python
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip -y
```

## 2. Размещение файлов

1. Создайте папку:
   ```bash
   sudo mkdir -p /opt/owen_synchronizer
   ```

2. Загрузите файлы в эту папку (например, через WinSCP):
   - `owen_cloud_synchronizer.py` (скрипт сбора данных)
   - `web_app.py` (скрипт веб-интерфейса)
   - `owen_config.json` (конфигурация)
   - `requirements.txt` (список зависимостей)
   - Папку `templates` с файлом `index.html` внутри.
     *Убедитесь, что структура такая: `/opt/owen_synchronizer/templates/index.html`*

## 3. Установка зависимостей

```bash
cd /opt/owen_synchronizer
sudo pip3 install -r requirements.txt
```
*Если возникают ошибки с pip на новых Ubuntu, используйте `apt`:*
```bash
sudo apt install python3-requests python3-flask python3-pandas -y
```

## 4. Настройка автозапуска (Systemd)

Настроим две службы: одну для сбора данных, другую для веб-сайта.

### Служба сбора данных

1. Скопируйте файл службы (или создайте его):
   ```bash
   sudo cp /opt/owen_synchronizer/owen_synchronizer.service /etc/systemd/system/
   ```
   *Если файла нет, создайте его вручную (см. содержимое ниже).*

### Служба веб-интерфейса

2. Скопируйте файл службы веб-интерфейса:
   ```bash
   sudo cp /opt/owen_synchronizer/owen_web.service /etc/systemd/system/
   ```
   *Если файла нет, создайте его вручную (см. содержимое ниже).*

3. Активируйте и запустите обе службы:
   ```bash
   sudo systemctl daemon-reload
   
   # Сборщик данных
   sudo systemctl enable owen_synchronizer
   sudo systemctl start owen_synchronizer
   
   # Веб-интерфейс
   sudo systemctl enable owen_web
   sudo systemctl start owen_web
   ```

## 5. Доступ к веб-интерфейсу

Теперь веб-интерфейс должен быть доступен по адресу:
`http://ВАШ_IP:5000`
Например: http://167.71.7.134:5000

Если сайт не открывается, возможно закрыт порт 5000 брандмауэром. Откройте его:
```bash
sudo ufw allow 5000
```

## Полезные команды

**Проверить статус:**
```bash
sudo systemctl status owen_synchronizer
sudo systemctl status owen_web
```

**Перезапустить:**
```bash
sudo systemctl restart owen_synchronizer
sudo systemctl restart owen_web
```

---

### Содержимое файлов служб (для справки)

**owen_synchronizer.service**
```ini
[Unit]
Description=Owen Cloud Synchronizer Service
After=network.target

[Service]
User=root
WorkingDirectory=/opt/owen_synchronizer
ExecStart=/usr/bin/python3 /opt/owen_synchronizer/owen_cloud_synchronizer.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

**owen_web.service**
```ini
[Unit]
Description=Owen Cloud Web Interface
After=network.target owen_synchronizer.service

[Service]
User=root
WorkingDirectory=/opt/owen_synchronizer
ExecStart=/usr/bin/python3 /opt/owen_synchronizer/web_app.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```
