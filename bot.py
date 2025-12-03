# -*- coding: utf-8 -*-
# Telegram бот для поиска предметов Stalcraft

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from parser import find_item_id_by_name, find_item_by_name, get_auction_history, get_auction_active_lots
from user_profiles import get_user_profile, add_to_favorites, remove_from_favorites, get_favorites
import os
from dotenv import load_dotenv
from pathlib import Path

# Загрузка переменных окружения
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / "keys.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик команды /start
    user_id = update.effective_user.id
    get_user_profile(user_id)

    welcome_message = (
        "👋 Привет. Это бот для отслеживания цен и активности предметов на аукционе Stalcraft.\n\n"
        "🔎 Можно просто написать название предмета, и бот покажет его ID.\n\n"
        "Также доступны кнопки ниже."
    )

    keyboard = [
        [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
         InlineKeyboardButton("⭐ Избранное", callback_data="favorites")],
        [InlineKeyboardButton("ℹ️ Справка", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик команды /help
    help_text = (
        "ℹ️ Справка по использованию бота:\n\n"
        "🔎 Поиск предметов:\n"
        "- можно искать по полному или частичному названию;\n"
        "- примеры: 'штрих', 'HK417', 'костюм'.\n\n"
        "📋 Команды:\n"
        "- /profile — профиль;\n"
        "- /favorites — избранные предметы;\n"
        "- /add <название> — добавить в избранное;\n"
        "- /remove <название> — удалить из избранного;\n"
        "- /history <название> — история цен на аукционе;\n"
        "- /lots <название> — активные лоты;\n"
        "- /search <название> — найти ID предмета.\n\n"
        "Можно просто написать название предмета в чат. 💬"
    )
    await update.message.reply_text(help_text)


async def search_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик команды /search
    if not context.args:
        await update.message.reply_text("ℹ️ Нужно указать название предмета. Пример: /search штрих")
        return

    item_name = " ".join(context.args)
    item = find_item_by_name(item_name)

    if item:
        message = f"✅ Найден предмет:\n📦 Название: {item['name']}\n🆔 ID: `{item['id']}`"
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ Предмет '{item_name}' не найден. Попробуйте другое название.")


async def get_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик команды /history
    if not context.args:
        await update.message.reply_text("ℹ️ Нужно указать название предмета. Пример: /history штрих")
        return

    item_name = " ".join(context.args)
    item = find_item_by_name(item_name)

    if not item:
        await update.message.reply_text(f"❌ Предмет '{item_name}' не найден.")
        return

    try:
        await update.message.reply_text("⏳ Загружаю историю цен...")
        history = get_auction_history("ru", item['id'])

        if not history:
            await update.message.reply_text("❌ История цен не найдена.")
            return

        message = f"📈 История цен для предмета:\n📦 {item['name']}\n\n"
        for date, prices in sorted(history.items()):
            avg_price = sum(prices) / len(prices) if prices else 0
            min_price = min(prices) if prices else 0
            max_price = max(prices) if prices else 0
            message += f"📅 {date}:\n"
            message += f"  Средняя: {avg_price:,.0f} ₽\n"
            message += f"  Мин: {min_price:,.0f} ₽ | Макс: {max_price:,.0f} ₽\n"
            message += f"  Лотов: {len(prices)}\n\n"

        if len(message) > 4000:
            parts = [message[i:i + 4000] for i in range(0, len(message), 4000)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"Ошибка при получении истории: {str(e)}")


async def get_lots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик команды /lots
    if not context.args:
        await update.message.reply_text("ℹ️ Нужно указать название предмета. Пример: /lots штрих")
        return

    item_name = " ".join(context.args)
    item = find_item_by_name(item_name)

    if not item:
        await update.message.reply_text(f"❌ Предмет '{item_name}' не найден.")
        return

    try:
        await update.message.reply_text("⏳ Загружаю активные лоты...")
        lots_data = get_auction_active_lots(item['id'], "ru")

        if not lots_data or "lots" not in lots_data:
            await update.message.reply_text("❌ Активные лоты не найдены.")
            return

        lots = lots_data.get("lots", [])

        if not lots:
            await update.message.reply_text("📭 Активных лотов нет.")
            return

        message = f"🛒 Активные лоты для предмета:\n📦 {item['name']}\n\n"
        message += f"Всего лотов: {len(lots)}\n\n"

        for i, lot in enumerate(lots[:10], 1):
            bid_price = lot.get("price", 0)
            buyout_price = lot.get("buyoutPrice")
            amount = lot.get("amount", 0)

            if buyout_price is not None:
                message += f"{i}. 💰 Ставка: {bid_price:,.0f} ₽ | 🏷️ Выкуп: {buyout_price:,.0f} ₽ | Кол-во: {amount}\n"
            else:
                message += f"{i}. 💰 Ставка: {bid_price:,.0f} ₽ | Кол-во: {amount}\n"

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"Ошибка при получении лотов: {str(e)}")


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик команды /profile
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    favorites = profile.get("favorites", [])

    message = (
        f"👤 Профиль\n\n"
        f"⭐ Избранных предметов: {len(favorites)}"
    )

    keyboard = [
        [InlineKeyboardButton("Избранное", callback_data="favorites")],
        [InlineKeyboardButton("Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(message, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)


async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик команды /favorites
    user_id = update.effective_user.id
    favorites = get_favorites(user_id)

    if not favorites:
        message = (
            "📭 У вас пока нет избранных предметов.\n\n"
            "Напишите название предмета и используйте /add, чтобы добавить его."
        )
        keyboard = [[InlineKeyboardButton("Назад", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        return

    message = "⭐ Избранные предметы:\n\n"
    keyboard = []

    for i, fav in enumerate(favorites[:10], 1):
        message += f"{i}. {fav['name']}\n"
        keyboard.append([
            InlineKeyboardButton(f"История: {fav['name'][:20]}", callback_data=f"history_{fav['id']}"),
            InlineKeyboardButton("Лоты", callback_data=f"lots_{fav['id']}")
        ])

    if len(favorites) > 10:
        message += f"\n... и еще {len(favorites) - 10} предметов"

    keyboard.append([InlineKeyboardButton("Назад", callback_data="profile")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        if len(message) > 4000:
            await update.message.reply_text(message[:4000])
            await update.message.reply_text("Используйте кнопки для быстрого доступа.", reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)


async def add_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик команды /add
    if not context.args:
        await update.message.reply_text("ℹ️ Нужно указать название предмета. Пример: /add штрих")
        return

    user_id = update.effective_user.id
    item_name = " ".join(context.args)
    item = find_item_by_name(item_name)

    if not item:
        await update.message.reply_text(f"❌ Предмет '{item_name}' не найден.")
        return

    if add_to_favorites(user_id, item['name'], item['id']):
        await update.message.reply_text(
            f"⭐ Предмет добавлен в избранное.\n\n"
            f"📦 {item['name']}\n\n"
            f"Используйте /favorites, чтобы посмотреть список."
        )
    else:
        await update.message.reply_text(
            f"⚠️ Предмет '{item['name']}' уже есть в избранном."
        )


async def remove_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик команды /remove
    if not context.args:
        await update.message.reply_text("ℹ️ Нужно указать название предмета. Пример: /remove штрих")
        return

    user_id = update.effective_user.id
    item_name = " ".join(context.args)
    item = find_item_by_name(item_name)

    if not item:
        await update.message.reply_text(f"❌ Предмет '{item_name}' не найден.")
        return

    if remove_from_favorites(user_id, item['id']):
        await update.message.reply_text(
            f"🗑️ Предмет удален из избранного.\n\n"
            f"📦 {item['name']}"
        )
    else:
        await update.message.reply_text(
            f"⚠️ Предмет '{item['name']}' не найден в избранном."
        )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик нажатий на кнопки
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    if data == "main_menu":
        welcome_message = (
            "📋 Главное меню.\n\n"
            "🔎 Можно просто написать название предмета, и бот покажет его ID."
        )
        keyboard = [
            [InlineKeyboardButton("Мой профиль", callback_data="profile"),
             InlineKeyboardButton("Избранное", callback_data="favorites")],
            [InlineKeyboardButton("Справка", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(welcome_message, reply_markup=reply_markup)

    elif data == "profile":
        profile = get_user_profile(user_id)
        favorites = profile.get("favorites", [])
        message = f"👤 Профиль\n\n⭐ Избранных предметов: {len(favorites)}"
        keyboard = [
            [InlineKeyboardButton("Избранное", callback_data="favorites")],
            [InlineKeyboardButton("Назад", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif data == "favorites":
        favorites = get_favorites(user_id)
        if not favorites:
            message = "📭 У вас пока нет избранных предметов."
            keyboard = [[InlineKeyboardButton("Назад", callback_data="profile")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            message = "Избранные предметы:\n\n"
            keyboard = []
            for i, fav in enumerate(favorites[:10], 1):
                message += f"{i}. {fav['name']}\n"
                keyboard.append([
                    InlineKeyboardButton(f"История: {fav['name'][:20]}", callback_data=f"history_{fav['id']}"),
                    InlineKeyboardButton("Лоты", callback_data=f"lots_{fav['id']}")
                ])
            keyboard.append([InlineKeyboardButton("Назад", callback_data="profile")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)

    elif data == "help":
        help_text = (
            "ℹ️ Справка по использованию бота:\n\n"
            "🔎 Поиск предметов:\n"
            "- можно искать по полному или частичному названию;\n"
            "- примеры: 'штрих', 'HK417', 'костюм'.\n\n"
            "📋 Команды:\n"
            "- /profile — профиль;\n"
            "- /favorites — избранные предметы;\n"
            "- /add <название> — добавить в избранное;\n"
            "- /remove <название> — удалить из избранного;\n"
            "- /history <название> — показать историю цен;\n"
            "- /lots <название> — показать активные лоты.\n\n"
            "Можно просто написать название предмета в чат. 💬"
        )
        keyboard = [[InlineKeyboardButton("Назад", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(help_text, reply_markup=reply_markup)

    elif data.startswith("history_"):
        item_id = data.replace("history_", "")
        from parser import load_items_data
        armor_data, weapon_data = load_items_data()
        item_name = None
        for name, id_val in {**armor_data, **weapon_data}.items():
            if id_val == item_id:
                item_name = name
                break

        if not item_name:
            await query.answer("Предмет не найден", show_alert=True)
            return

        await query.answer("⏳ Загружаю историю...")
        try:
            history = get_auction_history("ru", item_id)
            if not history:
                await query.answer("История не найдена", show_alert=True)
                return

            message = f"📈 История цен:\n📦 {item_name}\n\n"
            for date, prices in sorted(history.items()):
                avg_price = sum(prices) / len(prices) if prices else 0
                min_price = min(prices) if prices else 0
                max_price = max(prices) if prices else 0
                message += f"📅 {date}:\n"
                message += f"  Средняя: {avg_price:,.0f} ₽\n"
                message += f"  Мин: {min_price:,.0f} ₽ | Макс: {max_price:,.0f} ₽\n"
                message += f"  Лотов: {len(prices)}\n\n"

            keyboard = [[InlineKeyboardButton("Назад", callback_data="favorites")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message[:4000], reply_markup=reply_markup)
        except Exception as e:
            await query.answer(f"Ошибка: {str(e)}", show_alert=True)

    elif data.startswith("lots_"):
        item_id = data.replace("lots_", "")
        from parser import load_items_data
        armor_data, weapon_data = load_items_data()
        item_name = None
        for name, id_val in {**armor_data, **weapon_data}.items():
            if id_val == item_id:
                item_name = name
                break

        if not item_name:
            await query.answer("Предмет не найден", show_alert=True)
            return

        await query.answer("⏳ Загружаю лоты...")
        try:
            lots_data = get_auction_active_lots(item_id, "ru")
            lots = lots_data.get("lots", []) if lots_data else []

            if not lots:
                await query.answer("Активных лотов нет", show_alert=True)
                return

            message = f"🛒 Активные лоты:\n📦 {item_name}\n\nВсего: {len(lots)}\n\n"
            for i, lot in enumerate(lots[:10], 1):
                bid_price = lot.get("price", 0)
                buyout_price = lot.get("buyoutPrice")
                amount = lot.get("amount", 0)

                if buyout_price is not None:
                    message += f"{i}. Ставка: {bid_price:,.0f} ₽ | Выкуп: {buyout_price:,.0f} ₽ | Кол-во: {amount}\n"
                else:
                    message += f"{i}. Ставка: {bid_price:,.0f} ₽ | Кол-во: {amount}\n"

            keyboard = [[InlineKeyboardButton("Назад", callback_data="favorites")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
        except Exception as e:
            await query.answer(f"Ошибка: {str(e)}", show_alert=True)

    elif data.startswith("add_"):
        item_id = data.replace("add_", "")
        from parser import load_items_data
        armor_data, weapon_data = load_items_data()
        item_name = None
        for name, id_val in {**armor_data, **weapon_data}.items():
            if id_val == item_id:
                item_name = name
                break

        if item_name and add_to_favorites(user_id, item_name, item_id):
            await query.answer("Добавлено в избранное.")
            message = f"Найден предмет.\n\nНазвание: {item_name}\nID: `{item_id}`"
            keyboard = [
                [
                    InlineKeyboardButton("История цен", callback_data=f"history_{item_id}"),
                    InlineKeyboardButton("Лоты", callback_data=f"lots_{item_id}")
                ],
                [InlineKeyboardButton("Удалить из избранного", callback_data=f"remove_{item_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await query.answer("Уже в избранном.", show_alert=True)

    elif data.startswith("remove_"):
        item_id = data.replace("remove_", "")
        from parser import load_items_data
        armor_data, weapon_data = load_items_data()
        item_name = None
        for name, id_val in {**armor_data, **weapon_data}.items():
            if id_val == item_id:
                item_name = name
                break

        if item_name and remove_from_favorites(user_id, item_id):
            await query.answer("Удалено из избранного.")
            message = f"Найден предмет.\n\nНазвание: {item_name}\nID: `{item_id}`"
            keyboard = [
                [
                    InlineKeyboardButton("История цен", callback_data=f"history_{item_id}"),
                    InlineKeyboardButton("Лоты", callback_data=f"lots_{item_id}")
                ],
                [InlineKeyboardButton("Добавить в избранное", callback_data=f"add_{item_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await query.answer("Нет в избранном.", show_alert=True)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик обычных сообщений (поиск по названию)
    item_name = update.message.text.strip()

    if not item_name:
        return

    item = find_item_by_name(item_name)

    if item:
        user_id = update.effective_user.id
        favorites = get_favorites(user_id)
        is_favorite = any(f.get("id") == item['id'] for f in favorites)
        star = "⭐" if is_favorite else ""

        message = (
            f"✅ Найден предмет. {star}\n\n"
            f"📦 Название: {item['name']}\n"
            f"🆔 ID: `{item['id']}`"
        )

        keyboard = [
            [
                InlineKeyboardButton("История цен", callback_data=f"history_{item['id']}"),
                InlineKeyboardButton("Лоты", callback_data=f"lots_{item['id']}")
            ]
        ]

        if not is_favorite:
            keyboard.append([InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f"add_{item['id']}")])
        else:
            keyboard.append([InlineKeyboardButton("🗑️ Удалить из избранного", callback_data=f"remove_{item['id']}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(
            f"❌ Предмет '{item_name}' не найден.\n\n"
            f"Попробуйте:\n"
            f"- использовать частичное название;\n"
            f"- проверить написание;\n"
            f"- использовать команду /help."
        )


def main():
    # Запуск бота
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profile", show_profile))
    application.add_handler(CommandHandler("favorites", show_favorites))
    application.add_handler(CommandHandler("add", add_favorite))
    application.add_handler(CommandHandler("remove", remove_favorite))
    application.add_handler(CommandHandler("search", search_item))
    application.add_handler(CommandHandler("history", get_history))
    application.add_handler(CommandHandler("lots", get_lots))

    application.add_handler(CallbackQueryHandler(button_callback))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
