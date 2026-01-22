
https://github.com/livekit/livekit-cli

https://github.com/livekit/python-sdks
https://docs.livekit.io/reference/python/v1/livekit/api/

https://github.com/livekit/client-sdk-flutter
https://docs.livekit.io/client-sdk-flutter/
https://hub.docker.com/r/livekit/livekit-server

wget https://raw.githubusercontent.com/livekit/sip/main/docker-compose.yaml
docker compose up

Получить контейнер
$ docker pull livekit/livekit-server

$ mkdir livekitdocker
$ cd livekitdocker

Создать конфигурационный файл livekit.yaml
$ denis@agent0:~/livekit/livekitdocker$ sudo docker run --rm -v $PWD:/output livekit/generate --local

sudo docker run --rm \
    -p 7880:7880 \
    -p 7881:7881 \
    -p 7882:7882/udp \
    -v /home/denis/livekit/livekitdocker/livekit.yaml:/livekit.yaml \
    livekit/livekit-server \
    --config /livekit.yaml \
    --node-ip=158.160.2.82

Запустить сревер указав IP
ifconfig

sudo docker rm -f redis
sudo docker rm -f livekit
sudo docker rm -f sip
sudo docker compose down --remove-orphans
sudo docker compose up -d

sudo docker run -d \
    --name redis \
    --restart always \
    --net=host \
    -v /home/denis/livekit/redis_data:/data \
    redis:7-alpine


sudo docker run -d \
    --name livekit \
    --restart always \
    --net=host \
    -v /home/denis/livekit/livekitdocker/livekit.yaml:/livekit.yaml \
    livekit/livekit-server:latest \
    --config /livekit.yaml \
    --node-ip=158.160.2.82

sudo docker run -d \
    --name sip \
    --net=host \
    --restart always \
    -v /home/denis/livekit/sip/sip.yaml:/sip.yaml \
    livekit/sip:latest \
    --config /sip.yaml

sudo docker ps -a
sudo docker logs -f redis

Только свежие логи
sudo docker compose logs -f --tail 0



Для генерации токена пользователю:
python3 /home/denis/livekit/livekitdocker/tokengenerator.py

Для подключения введите ws://158.160.2.82:7880

Для увеличения размера буфера UDP пакетов:
sudo sysctl -w net.core.rmem_max=5000000
sudo sysctl -w net.core.wmem_max=5000000



## Настройка транка mango

### Создание окружения
Выполнить в каталоге agent
python3 -m venv venv

### Активация окружения
source venv/bin/activate

### Установка зависимостей
pip install livekit-api

### Запуск агента
sudo pkill -9 python
python3 setup_mango.py 

## Запуск агента

### Создание окружения
Выполнить в каталоге agent
python3 -m venv venv

### Активация окружения
source venv/bin/activate

### Установка зависимостей
pip install livekit

### Запуск агента
sudo pkill -9 python
python3 minimal_agent.py

lk sip inbound create \
  --url ws://158.160.2.82:7880 \
  --api-key APImmvWFZNCYdk6 \
  --api-secret uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a \
  mango_inbound.json

lk sip inbound list \
  --url ws://158.160.2.82:7880 \
  --api-key APImmvWFZNCYdk6 \
  --api-secret uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a

lk sip outbound create \
  --url ws://158.160.2.82:7880 \
  --api-key APImmvWFZNCYdk6 \
  --api-secret uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a \
  ./sip/mango_outbound.json

lk sip outbound list \
  --url ws://158.160.2.82:7880 \
  --api-key APImmvWFZNCYdk6 \
  --api-secret uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a

lk sip dispatch-rule list \
  --url ws://158.160.2.82:7880 \
  --api-key APImmvWFZNCYdk6 \
  --api-secret uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a

lk sip dispatch-rule delete SDR_BjX9cNJbBjhV \
  --url ws://158.160.2.82:7880 \
  --api-key APImmvWFZNCYdk6 \
  --api-secret uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a

lk sip dispatch create ./sip/mango_dispatch.json \
  --url ws://158.160.2.82:7880 \
  --api-key APImmvWFZNCYdk6 \
  --api-secret uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a

lk room list \
  --url ws://158.160.2.82:7880 \
  --api-key APImmvWFZNCYdk6 \
  --api-secret uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a

lk sip call \
  --url ws://158.160.2.82:7880 \
  --api-key APImmvWFZNCYdk6 \
  --api-secret uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a \
  --trunk ST_J9tXsUizgffb \
  --to +73833830067 \
  --from +73833830067

lk agent create --config ./sip/elaina_agent.yaml \
  --url ws://158.160.2.82:7880 \
  --api-key APImmvWFZNCYdk6 \
  --api-secret uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a

lk agent list \
  --url ws://158.160.2.82:7880 \
  --api-key APImmvWFZNCYdk6 \
  --api-secret uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a

lk agent list --url ws://158.160.2.82:7880 --api-key APImmvWFZNCYdk6

## Создание токена
lk token create \
    --url ws://158.160.2.82:7880 \
    --api-key APImmvWFZNCYdk6 \
    --api-secret uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a \
    --identity "Admin_User" \
    --all-rooms \
    --admin \
    --agent elaina \
    --valid-for 24h

## Блок для флудеров

```shell
sudo iptables -A INPUT -s 172.86.66.201 -j DROP
```
Разрешить только для манго
sudo ufw insert 1 deny from 81.88.86.55 to any port 5060 proto udp


## Настройка балансировщика

**Установите Nginx** на ваш сервер:
```shell
sudo apt update
sudo apt install nginx -y
```

**Создайте файл конфигурации** для вашего домена (elaina.adrian-vpn.host):
```shell
sudo nano /etc/nginx/sites-available/elaina.adrian-vpn.host
```

Встатьте туда следующую конфигурацию
```config
server {
    listen 80;
    server_name elaina.adrian-vpn.host www.elaina.adrian-vpn.host;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Также нужно проксировать WebSockets для LiveKit сервера на порту 7880
    location /ws {
        proxy_pass http://localhost:7880;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Активируем и запускаем** балансировщик:
```shell
sudo ln -s /etc/nginx/sites-available/elaina.adrian-vpn.host /etc/nginx/sites-enabled/
sudo nginx -t # Проверить синтаксис
sudo systemctl restart nginx
```
## **Получение и автоматическое обновление сертификатов с Certbot**:

**Установите Certbot**:
```shell
sudo certbot --nginx
```

## Использование переменных окружения в Docker Compose

### Общая информация

В этом проекте используется система управления переменными окружения через файл `.env`. Этот подход позволяет легко управлять конфигурацией приложения без изменения кода.

### Файл .env

Файл `.env` содержит переменные окружения, которые будут использоваться в Docker Compose. Пример содержания:

```
# LiveKit API Credentials
LIVEKIT_API_KEY=YOUR_API_KEY_HERE
LIVEKIT_API_SECRET=YOUR_API_SECRET_HERE
LIVEKIT_KEYS="YOUR_API_KEY_HERE: YOUR_API_SECRET_HERE"

# SIP Trunk Configuration
SIP_OUTBOUND_TRUNK_TEST_ID=YOUR_TRUNK_ID_HERE

# LiveKit Server URL
LIVEKIT_URL=ws://localhost:7880
```

### Запуск контейнеров с переменными окружения

#### Подготовка

1. Создайте файл `.env` в корне проекта, основываясь на примере или на файле `.env.example`
2. Установите значения переменных в соответствии с вашей средой

#### Запуск

Для запуска контейнеров с использованием переменных окружения выполните команду:

```bash
docker-compose up
```

или

```bash
docker compose up
```

(в зависимости от вашей версии Docker Compose)

#### Запуск в фоновом режиме

Для запуска контейнеров в фоновом режиме используйте флаг `-d`:

```bash
docker-compose up -d
```

### Переменные по умолчанию

В файле `docker-compose.yaml` используются переменные с умолчаниями в формате `${VARIABLE_NAME:-default_value}`. Это означает, что если переменная не установлена в файле `.env`, будет использовано значение по умолчанию.

Например:
- `${LIVEKIT_API_KEY:-YOUR_API_KEY_HERE}` - если переменная `LIVEKIT_API_KEY` не установлена, будет использовано значение `YOUR_API_KEY_HERE`

### Проверка переменных окружения

Для проверки установленных переменных окружения в работающем контейнере можно использовать команду:

```bash
docker-compose exec service_name env
```

Где `service_name` - это имя сервиса (например, `livekit`, `sip`, `my-agent`).

## Логи контейнеров

Для просмотра логов контейнера в Docker, вы можете использовать команду `docker logs`. Вот несколько способов, как это можно сделать:

**Просмотр логов определенного контейнера**:
   - Сначала нужно получить список запущенных контейнеров с помощью команды:
     ```bash
     sudo docker compose ps
     ```
   - Затем, зная ID или имя контейнера, вы можете посмотреть его логи:
     ```bash
     sudo docker compose logs <container_id_or_name>
     ```
**Просмотр логов с опцией follow (как tail -f)**:
   - Для непрерывного отслеживания новых записей в логах:
     ```bash
     sudo docker compose logs -f <container_id_or_name>
     ```

**Просмотр последних N строк лога**:
   - Чтобы увидеть только последние 10 строк лога:
     ```bash
     sudo docker compose logs --tail 10 <container_id_or_name>
     ```

**Просмотр логов с фильтрацией по времени**:
    - Для просмотра логов за определенный период:
      ```bash
      sudo docker compose logs --since "2023-01-01T00:00:00" --until "2023-01-02T00:00" <container_id_or_name>
      ```

## Восстановление SIP конфигураций после перезагрузки

После перезагрузки виртуальной машины SIP-транки и правила диспетчеризации могут исчезнуть, так как они не сохраняются автоматически между перезапусками контейнеров. Для восстановления конфигураций используется скрипт инициализации.

### Использование скрипта инициализации

Создан скрипт `scripts/init_sip_config.py`, который автоматически восстанавливает:
- Входящие и исходящие SIP-транки
- Правила диспетcherизации вызовов

### Запуск скрипта инициализации

После запуска всех контейнеров выполните:

```bash
cd /home/denis/livekit
source ./venv/bin/activate  # Активировать виртуальное окружение
python3 scripts/init_sip_config.py
```

Скрипт автоматически:
- Подключится к LiveKit серверу
- Создаст входящий SIP-транк из конфига `sip/mango_inbound.json` (если он не существует)
- Создаст исходящий SIP-транк из конфига `sip/mango_outbound.json` (если он не существует)
- Создаст правило диспетчеризации из конфига `sip/mango_dispatch.json`, используя ID актуального входящего транка
- Проверит, существуют ли уже такие конфигурации, чтобы избежать дубликатов

### Стандартная процедура после перезагрузки

1. Запустить контейнеры:
   ```bash
   cd /home/denis/livekit
   docker compose up -d
   ```

2. Дождаться полной загрузки сервисов (около 30 секунд)

3. Активировать виртуальное окружение и запустить скрипт инициализации:
   ```bash
   cd /home/denis/livekit
   source agent/venv/bin/activate
   python3 scripts/init_sip_config.py
   ```

4. Проверить результат:
   ```bash
   lk sip inbound list --url ws://158.160.2.82:7880 --api-key <your_api_key> --api-secret <your_api_secret>
   lk sip outbound list --url ws://158.160.2.82:7880 --api-key <your_api_key> --api-secret <your_api_secret>
   lk sip dispatch-rule list --url ws://158.160.2.82:7880 --api-key <your_api_key> --api-secret <your_api_secret>
   ```

### Настройка конфигурационных файлов

Скрипт использует следующие конфигурационные файлы:

- `sip/mango_inbound.json` - для настройки входящего транка
- `sip/mango_outbound.json` - для настройки исходящего транка
- `sip/mango_dispatch.json` - для настройки правила диспетчеризации

При создании правила диспетчеризации скрипт использует ID актуального входящего транка, а не ID из конфигурационного файла, что обеспечивает корректную работу после перезагрузки системы, когда ID транков могут измениться.

Вы можете изменить эти файлы перед запуском скрипта, чтобы настроить свои собственные транки и правила.

### Автоматический запуск при старте системы (опционально)

Для автоматического восстановления конфигураций после перезагрузки можно создать systemd-сервис:

Создайте файл `/etc/systemd/system/livekit-init.service`:

```ini
[Unit]
Description=LiveKit SIP Configuration Initialization
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/docker compose -f /home/denis/livekit/docker-compose.yaml up -d
ExecStartPost=/bin/sleep 30
ExecStartPost=/usr/bin/bash -c 'cd /home/denis/livekit && source agent/venv/bin/activate && python3 scripts/init_sip_config.py'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Затем включите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable livekit-init.service
```

### Проверка восстановленных конфигураций

Для проверки созданных транков и правил используйте команды:

```bash
lk sip inbound list --url ws://158.160.2.82:7880 --api-key <your_api_key> --api-secret <your_api_secret>
lk sip outbound list --url ws://158.160.2.82:7880 --api-key <your_api_key> --api-secret <your_api_secret>
lk sip dispatch-rule list --url ws://158.160.2.82:7880 --api-key <your_api_key> --api-secret <your_api_secret>
```

