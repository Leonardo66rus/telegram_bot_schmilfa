import os
import sqlite3
import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

TOKEN = os.getenv('TOKEN')
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Создание экземпляра приложения
application = Application.builder().token(TOKEN).build()

# Соединение с базой данных
def get_db_connection():
    """Создание соединения с базой данных."""
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
    return conn, cursor

def load_text(file_path):
    """Загрузка текста из файла с обработкой ошибок."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()  # Удаление лишних пробелов
        logger.warning(f"Файл {file_path} не найден.")
        return "Файл не найден."
    except Exception as e:
        logger.error(f"Ошибка при чтении файла {file_path}: {e}")
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
admin_keyboard = [["Статистика"], ["Главное меню"]]
guides_keyboard = [["Гайд для новичка"], ["Включить консоль и свободную камеру"], ["Консольные команды"], ["Конвой на 8+ человек"], ["Назад"]]
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
        mods_table_text = load_text('data/mods/mods_table.txt')

        # Создаем инлайн-кнопку для ссылки
        mods_link_button = InlineKeyboardMarkup([[InlineKeyboardButton("Ссылка на моды", url="https://clck.ru/Xxs42")]])

        # Отправляем текст с инлайн-клавиатурой для ссылки
        await update.message.reply_text(mods_table_text, reply_markup=mods_link_button)

        context.user_data['previous_menu'] = 'mods'
        context.user_data['current_menu'] = 'mods_table'
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def show_schmilfa_in_cabin(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        selected_game = context.user_data.get('selected_game', 'ATS')  # По умолчанию ATS
        schmilfa_file = f'data/mods/schmilfa_in_cabin_{selected_game.lower()}.txt'  # Формируем путь к файлу
        schmilfa_text = load_text(schmilfa_file)  # Загружаем текст из файла
        reply_markup = create_reply_markup(back_keyboard)
        await update.message.reply_text(schmilfa_text, reply_markup=reply_markup)
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

        # Создаем инлайн-кнопки для социальных сетей с эмодзи
        social_buttons = [
            [InlineKeyboardButton("✈️ Подписаться в Telegram", url="https://t.me/banka_alivok")],
            [InlineKeyboardButton("📺 Подписаться на YouTube", url="https://www.youtube.com/user/TheAlive55?sub_confirmation=1")],
            [InlineKeyboardButton("📺 Подписаться на Дзен", url="https://dzen.ru/thealive55")]
        ]

        # Используем ReplyKeyboardMarkup для кнопки "Назад"
        reply_keyboard = back_keyboard  # Уже определено как [['Назад']]
        reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)

        # Отправляем сообщение с инлайн-кнопками для социальных сетей
        await update.message.reply_text(social_text, reply_markup=InlineKeyboardMarkup(social_buttons))
        # Отправляем отдельное сообщение для кнопки "Назад"
        await update.message.reply_text("Нажмите 'Назад' для возврата в предыдущее меню:", reply_markup=reply_markup)

        context.user_data['previous_menu'] = context.user_data.get('current_menu', 'game_menu')
        context.user_data['current_menu'] = 'social'
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def show_patch(update: Update, context: CallbackContext, game: str) -> None:
    user = update.message.from_user
    if not user.is_bot:
        patch_file = f'data/patches/patch_{game.lower()}.txt'
        patch_text = load_text(patch_file)
        if "Файл не найден." in patch_text or "Произошла ошибка" in patch_text:
            patch_text = f"Обзор актуального патча для {game} не найден."
        reply_markup = create_reply_markup(back_keyboard)
        await update.message.reply_text(patch_text, reply_markup=reply_markup)
        context.user_data['previous_menu'] = context.user_data.get('current_menu', 'game_menu')
        context.user_data['current_menu'] = f'{game.lower()}_patch'
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def show_convoy_info(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        convoy_text = load_text('data/guides/convoy_8plus.txt')
        reply_markup = create_reply_markup(back_keyboard)
        await update.message.reply_text(convoy_text, reply_markup=reply_markup)
        context.user_data['previous_menu'] = 'guides'
        context.user_data['current_menu'] = 'convoy'
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
        if topic == "Конвой на 8+ человек":
            await show_convoy_info(update, context)
        else:
            file_map = {
                "Включить консоль и свободную камеру": 'data/guides/console_on.txt',
                "Консольные команды": 'data/guides/console_commands.txt',
                "Гайд для новичка": 'data/guides/guide.txt'
            }
            text = load_text(file_map.get(topic, 'data/guides/guide.txt'))
            reply_markup = create_reply_markup(back_keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup)
            context.user_data['previous_menu'] = 'guides'
            context.user_data['current_menu'] = 'guide'
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def handle_game_selection(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        game = update.message.text
        if game in ["ATS", "ETS 2"]:
            context.user_data['selected_game'] = game  # Устанавливаем выбранную игру в user_data
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

        if current_menu == 'convoy':
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
        elif current_menu == 'map_packs':
            await game_menu(update, context, 'ETS 2')
        else:
            await show_guides(update, context) if previous_menu == 'guides' else \
            await show_mods(update, context) if previous_menu == 'mods' else \
            await show_social(update, context) if previous_menu == 'social' else \
            await main_menu(update, context)
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def handle_mods_selection(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        current_menu = context.user_data.get('current_menu', '')
        selected_game = context.user_data.get('selected_game', 'ATS')  # Получаем выбранную игру

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
        elif update.message.text == "Золотая сборка Русских карт" and context.user_data.get('current_menu', '') == 'map_packs':
            gold_rus_text = load_text('data/maps/gold_rus.txt')
            reply_markup = create_reply_markup(back_keyboard)
            await update.message.reply_text(gold_rus_text, reply_markup=reply_markup)
        elif update.message.text == "Назад":
            await go_back(update, context)
        elif update.message.text == "Главное меню":
            await main_menu(update, context)
        elif update.message.text in ["Гайд для новичка", "Включить консоль и свободную камеру", "Консольные команды", "Конвой на 8+ человек"]:
            await handle_guide_selection(update, context)
        elif update.message.text == "Таблица модов":
            await show_mods_table(update, context)
        elif update.message.text == "Талисман 'Шмилфа' в кабину":
            await show_schmilfa_in_cabin(update, context)
        elif user.id in ADMIN_IDS and update.message.text == "Статистика":
            await admin_stats(update, context)
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
        logger.info(f"Бот {user.id} пытается запустить бота.")
        await update.message.reply_text("Извините, боты не могут использовать этого бота.")

async def admin_stats(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id in ADMIN_IDS:
        conn, cursor = get_db_connection()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        await update.message.reply_text(f"Количество пользователей в базе данных: {count}")
        context.user_data['previous_menu'] = 'admin_menu'
        context.user_data['current_menu'] = 'admin_stats'
    else:
        await update.message.reply_text("У вас нет доступа к этой функции.")

# Добавление обработчиков
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^(ATS|ETS 2|Админ)$'), handle_game_selection))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^(Гайды|Моды|Обзор актуального патча|Социальные сети|Главное меню|Назад|Гайд для новичка|Включить консоль и свободную камеру|Консольные команды|Конвой на 8\+ человек|Статистика|Сборки карт|Золотая сборка Русских карт)$'), handle_mods_selection))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^(Таблица модов|Талисман \'Шмилфа\' в кабину)$'), handle_mods_selection))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ignore_text_input))

# Запуск
if __name__ == '__main__':
    try:
        application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        # Убедимся, что соединение с базой данных закрыто
        conn, _ = get_db_connection()
        conn.close()