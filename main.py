import os
import sqlite3
import logging
import json
from logging.handlers import RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

TOKEN = os.getenv('TOKEN')
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# Создание структуры папок
log_dir = "Log"
archive_bot_dir = os.path.join(log_dir, "archive_bot_log")
archive_critical_dir = os.path.join(log_dir, "archive_critical_errors")

os.makedirs(log_dir, exist_ok=True)
os.makedirs(archive_bot_dir, exist_ok=True)
os.makedirs(archive_critical_dir, exist_ok=True)
os.makedirs('data/guides', exist_ok=True)  # Гарантируем наличие директории для файлов

# Настройка основного логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Формат логов
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Обработчик для консоли
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Обработчик для bot.log с ротацией по дням
bot_log_file = os.path.join(log_dir, "bot.log")
bot_handler = TimedRotatingFileHandler(
    bot_log_file, when='midnight', interval=1, backupCount=30, encoding='utf-8'
)
bot_handler.setFormatter(formatter)
logger.addHandler(bot_handler)

# Обработчик для critical_errors.log с ротацией по дням
critical_log_file = os.path.join(log_dir, "critical_errors.log")
critical_handler = TimedRotatingFileHandler(
    critical_log_file, when='midnight', interval=1, backupCount=30, encoding='utf-8'
)
critical_handler.setFormatter(formatter)

# Настройка логгера для критических ошибок
critical_logger = logging.getLogger('critical_logger')
critical_logger.setLevel(logging.CRITICAL)
critical_logger.addHandler(critical_handler)

# Создание экземпляра приложения
application = Application.builder().token(TOKEN).build()

def get_db_connection():
    """Создание соединения с базой данных."""
    try:
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           user_id INTEGER UNIQUE)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS guides
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           title TEXT UNIQUE,
                           content TEXT)''')
        conn.commit()
        logger.info("Соединение с базой данных успешно установлено.")
        return conn, cursor
    except Exception as e:
        logger.error(f"Ошибка при подключении к базе данных: {e}")
        critical_logger.critical(f"Критическая ошибка при подключении к базе данных: {e}", exc_info=True)
        raise

def load_text(file_path):
    """Загрузка текста из файла с обработкой ошибок."""
    try:
        absolute_path = os.path.abspath(file_path)  # Используем абсолютный путь
        logger.info(f"Попытка загрузить файл: {absolute_path}")
        if os.path.exists(absolute_path):
            with open(absolute_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                logger.info(f"Файл {absolute_path} успешно загружен. Содержимое: {content[:50]}...")
                return content
        logger.warning(f"Файл {absolute_path} не найден.")
        return "Файл не найден."
    except Exception as e:
        logger.error(f"Ошибка при чтении файла {absolute_path}: {e}")
        critical_logger.critical(f"Критическая ошибка при чтении файла {absolute_path}: {e}", exc_info=True)
        return "Произошла ошибка при чтении файла."

def save_user_id(user_id, cursor, conn):
    """Сохранение ID пользователя в базу данных."""
    try:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        logger.info(f"ID пользователя {user_id} сохранен.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении ID пользователя {user_id}: {e}")

def create_reply_markup(keyboard):
    """Создание клавиатуры."""
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, selective=False)

# Оптимизация клавиатур для постоянного отображения
main_keyboard = [["ATS", "ETS 2"]]
game_keyboard = [["Гайды", "Моды"], ["Обзор актуального патча", "Социальные сети"], ["Назад"]]
ets_game_keyboard = [["Гайды", "Моды"], ["Обзор актуального патча", "Социальные сети"], ["Сборки карт"], ["Назад"]]
map_packs_keyboard = [["Золотая сборка Русских карт"], ["Назад"]]
admin_keyboard = [["Статистика", "Выгрузить ID пользователей", "Рассылка"], ["Главное меню"]]
guides_keyboard = [
    ["Гайд для новичка"],
    ["Включить консоль и свободную камеру"],
    ["Консольные команды"],
    ["Конвой на 8+ человек"],
    ["Своё радио для ETS2 и ATS"],
    ["Настройка OCULUS QUEST 2/3 для ATS и ETS2"],
    ["Назад"]
]
mods_keyboard = [["Таблица модов", "Талисман 'Шмилфа' в кабину"], ["Назад"]]
back_keyboard = [["Назад"]]

async def main_menu(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        conn, cursor = get_db_connection()
        save_user_id(user.id, cursor, conn)
        conn.close()
        logger.info(f"Отображение главного меню для пользователя {user.id}")
        keyboard = main_keyboard.copy()
        if user.id in ADMIN_IDS:
            keyboard.append(["Админ"])
        reply_markup = create_reply_markup(keyboard)
        await update.message.reply_text("Выберите игру :", reply_markup=reply_markup)
        context.user_data['previous_menu'] = 'start_menu'
        context.user_data['current_menu'] = 'main_menu'
    else:
        logger.info(f"Бот {user.id} пытается получить доступ к главному меню.")
        await update.message.reply_text("Извините, боты не могут использовать этот бот.")

async def admin_menu(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id in ADMIN_IDS:
        reply_markup = create_reply_markup(admin_keyboard)
        await update.message.reply_text("Административное меню:", reply_markup=reply_markup)
        context.user_data['previous_menu'] = 'main_menu'
        context.user_data['current_menu'] = 'admin_menu'
    else:
        await update.message.reply_text("У вас нет доступа к этой функции.")
        await go_back(update, context)

async def show_mods(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        reply_markup = create_reply_markup(mods_keyboard)
        await update.message.reply_text("Выберите опцию:", reply_markup=reply_markup)
        context.user_data['previous_menu'] = context.user_data.get('current_menu', 'game_menu')
        context.user_data['current_menu'] = 'mods'
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def show_mods_table(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        mods_table_text = load_text('data/mods/mods_table.md')
        await update.message.reply_text(mods_table_text, parse_mode='Markdown')
        context.user_data['previous_menu'] = 'mods'
        context.user_data['current_menu'] = 'mods_table'
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def show_schmilfa_in_cabin(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        selected_game = context.user_data.get('selected_game', 'ATS')  # По умолчанию ATS
        schmilfa_file = f'data/mods/schmilfa_in_cabin_{selected_game.lower()}.md'  # Изменяем расширение на .md
        schmilfa_text = load_text(schmilfa_file)
        reply_markup = create_reply_markup(back_keyboard)
        await update.message.reply_text(schmilfa_text, reply_markup=reply_markup, parse_mode='Markdown')  # Указываем parse_mode
        context.user_data['previous_menu'] = 'mods'
        context.user_data['current_menu'] = 'schmilfa_in_cabin'
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def show_guides(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        reply_markup = create_reply_markup(guides_keyboard)
        await update.message.reply_text("Выберите гайд:", reply_markup=reply_markup)
        context.user_data['previous_menu'] = context.user_data.get('current_menu', 'game_menu')
        context.user_data['current_menu'] = 'guides'
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def show_social(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        social_text = "Добро пожаловать в наши социальные сети! 📱\n\nОставайтесь на связи и следите за всеми важными обновлениями:"
        social_buttons = [
            [InlineKeyboardButton("✈️ Подписаться в Telegram", url="https://t.me/banka_alivok")],
            [InlineKeyboardButton("📺 Подписаться на YouTube", url="https://www.youtube.com/user/TheAlive55?sub_confirmation=1")],
            [InlineKeyboardButton("📺 Подписаться на Дзен", url="https://dzen.ru/thealive55")]
        ]
        reply_keyboard = back_keyboard
        reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(social_text, reply_markup=InlineKeyboardMarkup(social_buttons))
        await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
        context.user_data['previous_menu'] = context.user_data.get('current_menu', 'game_menu')
        context.user_data['current_menu'] = 'social'
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def show_patch(update: Update, context: CallbackContext, game: str) -> None:
    user = update.message.from_user
    if not user.is_bot:
        patch_file = f'data/patches/patch_{game.lower()}.md'
        patch_text = load_text(patch_file)
        if "Файл не найден." in patch_text or "Произошла ошибка" in patch_text:
            patch_text = f"Обзор актуального патча для {game} не найден."
        reply_markup = create_reply_markup(back_keyboard)
        await update.message.reply_text(patch_text, reply_markup=reply_markup, parse_mode='Markdown')  # Используем Markdown
        context.user_data['previous_menu'] = context.user_data.get('current_menu', 'game_menu')
        context.user_data['current_menu'] = f'{game.lower()}_patch'
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def game_menu(update: Update, context: CallbackContext, game: str) -> None:
    user = update.message.from_user
    if not user.is_bot:
        if game == "ETS 2":
            reply_markup = create_reply_markup(ets_game_keyboard)
        else:
            reply_markup = create_reply_markup(game_keyboard)
        await update.message.reply_text(f"Выберите опцию для {game}:", reply_markup=reply_markup)
        context.user_data['previous_menu'] = 'main_menu'
        context.user_data['current_menu'] = f'{game.lower()}_menu'
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def handle_guide_selection(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        topic = update.message.text
        logger.info(f"Пользователь {user.id} выбрал гайд: {topic}")
        try:
            # Словарь для сопоставления названий гайдов с файлами
            guide_files = {
                "Гайд для новичка": "guide.md",
                "Включить консоль и свободную камеру": "console_on.md",
                "Консольные команды": "console_commands.md",
                "Конвой на 8+ человек": "convoy_8plus.md",
                "Своё радио для ETS2 и ATS": "radio.md",
                "Настройка OCULUS QUEST 2/3 для ATS и ETS2": "oculus.md"
            }
            guide_filename = guide_files.get(topic, "guide.md")  # По умолчанию "guide.md"
            guide_file = f'data/guides/{guide_filename}'
            guide_text = load_text(guide_file)
            if "Файл не найден." in guide_text or "Произошла ошибка" in guide_text:
                guide_text = f"Гайд '{topic}' не найден."
            reply_markup = create_reply_markup(back_keyboard)
            await update.message.reply_text(guide_text, reply_markup=reply_markup, parse_mode='Markdown')
            context.user_data['previous_menu'] = 'guides'
            context.user_data['current_menu'] = guide_filename.split('.')[0]  # Например, 'convoy_8plus'
        except Exception as e:
            logger.error(f"Ошибка в handle_guide_selection: {e}")
            await update.message.reply_text("Произошла ошибка, попробуйте позже.")
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def show_map_pack(update: Update, context: CallbackContext, map_pack: str) -> None:
    user = update.message.from_user
    if not user.is_bot:
        # Словарь для сопоставления названий сборок с файлами
        map_files = {
            "Золотая сборка Русских карт": "gold_rus.md",
            # Добавьте другие сборки здесь, если нужно
        }
        map_filename = map_files.get(map_pack, "unknown_map.md")
        map_file = f'data/maps/{map_filename}'
        map_text = load_text(map_file)
        if "Файл не найден." in map_text or "Произошла ошибка" in map_text:
            map_text = f"Информация о сборке карт '{map_pack}' не найдена."
        reply_markup = create_reply_markup(back_keyboard)
        await update.message.reply_text(map_text, reply_markup=reply_markup, parse_mode='Markdown')  # Используем Markdown
        context.user_data['previous_menu'] = 'map_packs'
        context.user_data['current_menu'] = f'{map_pack.lower().replace(" ", "_")}_map'
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def handle_game_selection(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        game = update.message.text
        logger.info(f"Пользователь {user.id} выбрал игру: {game}")
        if game in ["ATS", "ETS 2"]:
            context.user_data['selected_game'] = game
            await game_menu(update, context, game)
        elif user.id in ADMIN_IDS and game == "Админ":
            await admin_menu(update, context)
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def go_back(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        previous_menu = context.user_data.get('previous_menu', 'main_menu')
        current_menu = context.user_data.get('current_menu', '')
        logger.info(f"Переход назад: текущий={current_menu}, предыдущий={previous_menu}")
        if current_menu == 'social':
            game = context.user_data.get('selected_game', 'ATS')
            await game_menu(update, context, game)
        elif current_menu in ['guide', 'console_on', 'console_commands', 'convoy_8plus', 'radio', 'oculus']:  # Обновляем список
            await show_guides(update, context)
        elif previous_menu == 'start_menu':
            await main_menu(update, context)
        elif previous_menu == 'main_menu':
            await main_menu(update, context)
        elif 'menu' in previous_menu:
            game = "ATS" if "ats" in previous_menu else "ETS 2"
            await game_menu(update, context, game)
        elif current_menu == 'admin_menu':
            await main_menu(update, context)
        elif current_menu == 'map_packs' or 'map' in current_menu:
            await game_menu(update, context, 'ETS 2')
        else:
            await show_guides(update, context) if previous_menu == 'guides' else \
            await show_mods(update, context) if previous_menu == 'mods' else \
            await show_social(update, context) if previous_menu == 'social' else \
            await main_menu(update, context)
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def broadcast(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id in ADMIN_IDS:
        # Инструкция для администратора
        instruction = (
            "📝 **Инструкция по созданию рассылки:**\n\n"
            "1. Вы можете отправить:\n"
            "   - Текст с Markdown форматированием.\n"
            "   - Фото с подписью (caption), также поддерживающей Markdown.\n\n"
            "2. **Markdown форматирование:**\n"
            "   - *Жирный текст*: `*жирный*`.\n"
            "   - _Курсив_: `_курсив_`.\n"
            "   - [Ссылка](https://example.com): `[текст](ссылка)`.\n"
            "3. **Примеры:**\n"
            "   - Текст с ссылкой: `Посетите [Google](https://www.google.com).`\n"
            "   - Фото с подписью: Отправьте фото с подписью `[Google](https://www.google.com)`.\n\n"
            "Отправьте ваше сообщение или фото с подписью:"
        )

        await update.message.reply_text(instruction, parse_mode='Markdown')
        context.user_data['waiting_for_broadcast'] = True
        context.user_data['broadcast_message'] = None
        context.user_data['broadcast_photo'] = None
    else:
        await update.message.reply_text("У вас нет доступа к этой функции.")

async def handle_broadcast_input(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id in ADMIN_IDS and context.user_data.get('waiting_for_broadcast'):
        # Проверяем, есть ли фото в сообщении
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
            context.user_data['broadcast_photo'] = photo_file.file_id
            logger.info(f"Фото сохранено: {photo_file.file_id}")

            # Сохраняем текст под фото (caption), если он есть
            if update.message.caption:
                context.user_data['broadcast_message'] = update.message.caption
                logger.info(f"Текст под фото (caption) сохранен: {update.message.caption}")
            else:
                context.user_data['broadcast_message'] = ""
                logger.info("Текст под фото отсутствует.")
        else:
            context.user_data['broadcast_photo'] = None
            logger.info("Фото не прикреплено.")

            # Сохраняем обычный текст, если фото нет
            if update.message.text:
                context.user_data['broadcast_message'] = update.message.text
                logger.info(f"Текст сообщения сохранен: {update.message.text}")
            else:
                context.user_data['broadcast_message'] = ""
                logger.info("Текст сообщения отсутствует.")

        # Предлагаем подтвердить отправку
        keyboard = [
            [InlineKeyboardButton("Отправить", callback_data='send_broadcast')],
            [InlineKeyboardButton("Отменить", callback_data='cancel_broadcast')],
            [InlineKeyboardButton("Назад", callback_data='back_from_broadcast')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Проверьте ваше сообщение:\n\n{context.user_data['broadcast_message']}\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'  # Указываем, что текст содержит Markdown
        )
    else:
        await update.message.reply_text("Вы не в режиме ожидания для рассылки.")

async def handle_broadcast_action(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if user.id in ADMIN_IDS:
        message = context.user_data.get('broadcast_message')
        photo = context.user_data.get('broadcast_photo')
        logger.info(f"Сообщение для рассылки: {message}")
        logger.info(f"Фото для рассылки: {photo}")

        if message or photo:
            if query.data == 'send_broadcast':
                conn, cursor = get_db_connection()
                try:
                    cursor.execute("SELECT user_id FROM users")
                    user_ids = [row[0] for row in cursor.fetchall()]
                    successful = 0
                    failed = 0
                    for user_id in user_ids:
                        try:
                            if photo:
                                # Отправляем фото с подписью (caption)
                                await context.bot.send_photo(
                                    chat_id=user_id,
                                    photo=photo,
                                    caption=message,
                                    parse_mode='Markdown'  # Указываем, что текст содержит Markdown
                                )
                                logger.info(f"Фото отправлено пользователю {user_id}")
                            else:
                                # Отправляем только текст
                                await context.bot.send_message(
                                    chat_id=user_id,
                                    text=message,
                                    parse_mode='Markdown'  # Указываем, что текст содержит Markdown
                                )
                                logger.info(f"Текст отправлен пользователю {user_id}")
                            successful += 1
                        except Exception as e:
                            logger.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
                            failed += 1
                    await query.edit_message_text(f"Рассылка завершена. Успешно отправлено: {successful}. Не удалось отправить: {failed}")
                except Exception as e:
                    logger.error(f"Ошибка при рассылке: {e}")
                    critical_logger.critical(f"Критическая ошибка при рассылке: {e}", exc_info=True)
                    await query.edit_message_text("Произошла ошибка при рассылке.")
                finally:
                    conn.close()
            elif query.data == 'cancel_broadcast':
                await query.edit_message_text("Рассылка отменена.")
            elif query.data == 'back_from_broadcast':
                await main_menu(update, context)
        else:
            await query.edit_message_text("Сообщение для рассылки не найдено.")
    else:
        await query.edit_message_text("У вас нет доступа к этой функции.")
    context.user_data['broadcast_message'] = None
    context.user_data['broadcast_photo'] = None
    context.user_data['waiting_for_broadcast'] = False

async def handle_mods_selection(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        logger.info(f"handle_mods_selection вызвана с текстом: {update.message.text}")
        current_menu = context.user_data.get('current_menu', '')
        selected_game = context.user_data.get('selected_game', 'ATS')
        if update.message.text in ["Гайды", "Моды", "Социальные сети", "Обзор актуального патча"]:
            if update.message.text == "Гайды":
                await show_guides(update, context)
            elif update.message.text == "Моды":
                await show_mods(update, context)
            elif update.message.text == "Социальные сети":
                await show_social(update, context)
            elif update.message.text == "Обзор актуального патча":
                await show_patch(update, context, selected_game)
        elif update.message.text == "Сборки карт" and selected_game == "ETS 2":
            reply_markup = create_reply_markup(map_packs_keyboard)
            await update.message.reply_text("Выберите сборку карт:", reply_markup=reply_markup)
            context.user_data['previous_menu'] = 'ets_menu'
            context.user_data['current_menu'] = 'map_packs'
        elif update.message.text == "Золотая сборка Русских карт" and current_menu == 'map_packs':
            await show_map_pack(update, context, "Золотая сборка Русских карт")
        elif update.message.text == "Назад":
            await go_back(update, context)
        elif update.message.text == "Главное меню":
            await main_menu(update, context)
        elif update.message.text in ["Гайд для новичка", "Включить консоль и свободную камеру", "Консольные команды", "Конвой на 8+ человек", "Своё радио для ETS2 и ATS", "Настройка OCULUS QUEST 2/3 для ATS и ETS2"]:
            await handle_guide_selection(update, context)
        elif update.message.text == "Таблица модов":
            await show_mods_table(update, context)
        elif update.message.text == "Талисман 'Шмилфа' в кабину":
            await show_schmilfa_in_cabin(update, context)
        elif user.id in ADMIN_IDS and update.message.text == "Статистика":
            await admin_stats(update, context)
        elif user.id in ADMIN_IDS and update.message.text == "Выгрузить ID пользователей":
            await export_user_ids(update, context)
        elif user.id in ADMIN_IDS and update.message.text == "Рассылка":
            await broadcast(update, context)
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def ignore_text_input(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        await update.message.reply_text("Пожалуйста, используйте кнопки меню для навигации.", reply_markup=create_reply_markup(back_keyboard))
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    if not user.is_bot:
        user_id = user.id
        logger.info(f"Пользователь {user_id} запустил бота.")
        await main_menu(update, context)
    else:
        logger.warning(f"Бот {user.id} пытается запустить бота.")
        await update.message.reply_text("Извините, боты не могут использовать этого бота.")

async def admin_stats(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id in ADMIN_IDS:
        conn, cursor = get_db_connection()
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            logger.info(f"Администратор {user.id} запросил статистику. Количество пользователей: {count}")
            await update.message.reply_text(f"Количество пользователей в базе данных: {count}")
        except Exception as e:
            logger.error(f"Ошибка при запросе статистики: {e}")
            critical_logger.critical(f"Критическая ошибка при запросе статистики: {e}", exc_info=True)
            await update.message.reply_text("Произошла ошибка при запросе статистики.")
        finally:
            conn.close()
    else:
        logger.warning(f"Пользователь {user.id} без прав администратора попытался запросить статистику.")
        await update.message.reply_text("У вас нет доступа к этой функции.")

async def export_user_ids(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id in ADMIN_IDS:
        conn, cursor = get_db_connection()
        try:
            cursor.execute("SELECT user_id FROM users")
            user_ids = [row[0] for row in cursor.fetchall()]
            with open('user_ids.json', 'w') as json_file:
                json.dump(user_ids, json_file)
            await update.message.reply_text("ID пользователей выгружены в user_ids.json.")
        except Exception as e:
            logger.error(f"Ошибка при выгрузке ID пользователей: {e}")
            await update.message.reply_text("Произошла ошибка при выгрузке ID пользователей.")
        finally:
            conn.close()
    else:
        await update.message.reply_text("У вас нет доступа к этой функции.")

def archive_logs(source, destination):
    """Перемещает архивные логи в указанную папку."""
    if os.path.exists(source):
        os.rename(source, os.path.join(destination, os.path.basename(source)))

def bot_namer(default_name):
    archive_logs(default_name, archive_bot_dir)
    return default_name

def critical_namer(default_name):
    archive_logs(default_name, archive_critical_dir)
    return default_name

bot_handler.namer = bot_namer
critical_handler.namer = critical_namer

# Добавление обработчиков
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^(ATS|ETS 2|Админ)$'), handle_game_selection))
application.add_handler(MessageHandler(
    filters.TEXT & filters.Regex('^(Гайды|Моды|Обзор актуального патча|Социальные сети|Главное меню|Назад|Гайд для новичка|Включить консоль и свободную камеру|Консольные команды|Конвой на 8\+ человек|Своё радио для ETS2 и ATS|Настройка OCULUS QUEST 2\/3 для ATS и ETS2|Статистика|Сборки карт|Золотая сборка Русских карт|Выгрузить ID пользователей|Рассылка)$'),
    handle_mods_selection
))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^(Таблица модов|Талисман \'Шмилфа\' в кабину)$'), handle_mods_selection))
application.add_handler(MessageHandler(filters.PHOTO, handle_broadcast_input))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_input))
application.add_handler(CallbackQueryHandler(handle_broadcast_action, pattern='^(send_broadcast|cancel_broadcast|back_from_broadcast)$'))

# Запуск
if __name__ == '__main__':
    conn = None
    try:
        logger.info("Запуск бота...")
        conn, _ = get_db_connection()
        application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        critical_logger.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
    finally:
        try:
            if conn:
                conn.close()
                logger.info("Соединение с базой данных закрыто.")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения с базой данных: {e}")
            critical_logger.critical(f"Критическая ошибка при закрытии соединения с базой данных: {e}", exc_info=True)
        finally:
            logger.info("Остановка бота...")