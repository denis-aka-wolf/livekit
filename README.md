
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