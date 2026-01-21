import jwt
import time

def generate_access_token(api_key, api_secret, user_name, room_name):
    payload = {
        "iss": api_key,
        "nbf": int(time.time()),
        "exp": int(time.time()) + 3600,  # Токен действителен в течение часа
        "sub": user_name,
        "video": {
            "room": room_name,
            "roomJoin": True
        }
    }

    token = jwt.encode(payload, api_secret, algorithm="HS256")
    return token

user_name = input("Введите имя гостя: ")
room_name = input("Введите название комнаты: ")

api_key = ""
api_secret = ""

token = generate_access_token(api_key, api_secret, user_name, room_name)
print("Токен для пользователя " + user_name + ":\n" + token)

