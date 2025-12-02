# -*- coding: utf-8 -*-
# Модуль для работы с профилями пользователей

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
PROFILES_FILE = BASE_DIR / "user_profiles.json"


def load_profiles():
    # Загружает профили пользователей из файла
    if not PROFILES_FILE.exists():
        return {}
    
    try:
        with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def save_profiles(profiles):
    # Сохраняет профили пользователей в файл
    with open(PROFILES_FILE, 'w', encoding='utf-8') as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)


def get_user_profile(user_id):
    # Получает профиль пользователя
    profiles = load_profiles()
    user_id_str = str(user_id)
    
    if user_id_str not in profiles:
        # Создаем новый профиль
        profiles[user_id_str] = {
            "favorites": [],
            "created_at": None
        }
        save_profiles(profiles)
    
    return profiles[user_id_str]


def add_to_favorites(user_id, item_name, item_id):
    # Добавляет предмет в избранное
    profiles = load_profiles()
    user_id_str = str(user_id)
    
    if user_id_str not in profiles:
        profiles[user_id_str] = {"favorites": []}
    
    # Проверяем, нет ли уже этого предмета
    favorites = profiles[user_id_str].get("favorites", [])
    for fav in favorites:
        if fav.get("id") == item_id:
            return False  # Уже есть в избранном
    
    # Добавляем предмет
    favorites.append({
        "name": item_name,
        "id": item_id
    })
    profiles[user_id_str]["favorites"] = favorites
    save_profiles(profiles)
    return True


def remove_from_favorites(user_id, item_id):
    # Удаляет предмет из избранного
    profiles = load_profiles()
    user_id_str = str(user_id)
    
    if user_id_str not in profiles:
        return False
    
    favorites = profiles[user_id_str].get("favorites", [])
    new_favorites = [f for f in favorites if f.get("id") != item_id]
    
    if len(new_favorites) == len(favorites):
        return False  # Предмет не найден в избранном
    
    profiles[user_id_str]["favorites"] = new_favorites
    save_profiles(profiles)
    return True


def get_favorites(user_id):
    # Получает список избранных предметов пользователя
    profile = get_user_profile(user_id)
    return profile.get("favorites", [])

