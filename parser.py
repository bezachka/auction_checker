from requests import get, post
from dotenv import load_dotenv
import os
from pathlib import Path
from datetime import datetime
import json


BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / "keys.env")

CLIENT_SECRET = os.getenv("CLIENT_SECRET")
CLIENT_ID = os.getenv("CLIENT_ID")


def get_auth_token():
    url = "https://exbo.net/oauth/token"

    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "",
    }

    response = post(url=url, data=params)
    return response.json()


TOKEN = None


def get_token():
    # Получает токен авторизации (с кэшированием)
    global TOKEN
    if TOKEN is None:
        TOKEN = "Bearer " + get_auth_token()["access_token"]
    return TOKEN


def get_auction_history(region, item_id):
    # Возвращает историю цен по дням для указанного предмета
    history_by_date = {}
    url = f"https://eapi.stalcraft.net/{region}/auction/{item_id}/history"
    headers = {"Authorization": get_token()}
    response = get(url=url, headers=headers)

    for entry in response.json().get("prices", []):
        time_str = entry["time"]
        dt_object = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        date_key = dt_object.strftime("%d.%m.%Y")
        price = entry["price"]

        if date_key not in history_by_date:
            history_by_date[date_key] = [price]
        else:
            history_by_date[date_key].append(price)

    return history_by_date


def get_auction_active_lots(item_id, region):
    # Возвращает активные лоты по предмету
    headers = {"Authorization": get_token()}
    url = f"https://eapi.stalcraft.net/{region}/auction/{item_id}/lots"
    response1 = get(url, headers=headers)
    return response1.json()


_armor_data = None
_weapon_data = None


def load_items_data():
    # Загружает данные из JSON файлов
    global _armor_data, _weapon_data

    if _armor_data is None:
        armor_file = BASE_DIR / "armor.json"
        weapon_file = BASE_DIR / "weapon.json"

        with open(armor_file, "r", encoding="utf-8") as f:
            _armor_data = json.load(f)

        with open(weapon_file, "r", encoding="utf-8") as f:
            _weapon_data = json.load(f)

    return _armor_data, _weapon_data


def find_item_id_by_name(item_name, search_in="both"):
    # Возвращает ID предмета по названию
    result = find_item_by_name(item_name, search_in)
    return result["id"] if result else None


def find_item_by_name(item_name, search_in="both"):
    # Возвращает словарь с 'name' и 'id' предмета по названию
    armor_data, weapon_data = load_items_data()
    item_name_lower = item_name.lower().strip()

    if search_in in ("armor", "both"):
        for name, item_id in armor_data.items():
            if name.lower() == item_name_lower:
                return {"name": name, "id": item_id}

    if search_in in ("weapon", "both"):
        for name, item_id in weapon_data.items():
            if name.lower() == item_name_lower:
                return {"name": name, "id": item_id}

    if search_in in ("armor", "both"):
        for name, item_id in armor_data.items():
            if item_name_lower in name.lower():
                return {"name": name, "id": item_id}

    if search_in in ("weapon", "both"):
        for name, item_id in weapon_data.items():
            if item_name_lower in name.lower():
                return {"name": name, "id": item_id}

    return None
