import os
import sqlite3
import logging
from telegram import Update, ReplyKeyboardMarkup
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
main_keyboard = [["ATS", "ETS"]]
game_keyboard = [["Гайды", "Моды"], ["Обзор патча", "Социальные сети"], ["Главное меню"]]
guides_keyboard = [["Гайд для новичка"], ["Включить консоль и свободную камеру"], ["Консольные команды"], ["Конвой на 8+ человек"], ["Назад"]]
back_keyboard = [["Назад"]]

async def main_menu(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        conn, cursor = get_db_connection()
        save_user_id(user.id, cursor, conn)
        conn.close()
        logger.info(f"Отображение главного меню для пользователя {user.id}")
        reply_markup = create_reply_markup(main_keyboard)
        await update.message.reply_text("Выберите игру:", reply_markup=reply_markup)
        context.user_data['previous_menu'] = 'main_menu'
        context.user_data['current_menu'] = 'main_menu'
    else:
        logger.info(f"Бот {user.id} пытается получить доступ к главному меню.")
        await update.message.reply_text("Извините, боты не могут использовать этот бот.")

async def show_mods(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        mods_text = load_text('data/mods/mods.txt')
        reply_markup = create_reply_markup(back_keyboard)
        await update.message.reply_text(mods_text, reply_markup=reply_markup)
        context.user_data['previous_menu'] = context.user_data.get('current_menu', 'game_menu')
        context.user_data['current_menu'] = 'mods'
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
        social_text = load_text('data/social/social.txt')
        reply_markup = create_reply_markup(back_keyboard)
        await update.message.reply_text(social_text, reply_markup=reply_markup)
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
            patch_text = f"Обзор патча для {game} не найден."
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
        if game in ["ATS", "ETS"]:
            await game_menu(update, context, game)
    else:
        await update.message.reply_text("Извините, боты не могут использовать эту функцию.")

async def go_back(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if not user.is_bot:
        previous_menu = context.user_data.get('previous_menu', 'main_menu')
        current_menu = context.user_data.get('current_menu', '')

        if current_menu == 'convoy':
            await show_guides(update, context)
        elif previous_menu == 'main_menu':
            await main_menu(update, context)
        elif 'menu' in previous_menu:
            game = "ATS" if "ats" in previous_menu else "ETS"
            await game_menu(update, context, game)
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
        game = "ATS" if "ats" in current_menu else "ETS" if "ets" in current_menu else None

        if update.message.text in ["Гайды", "Моды", "Социальные сети", "Обзор патча"] and game:
            if update.message.text == "Гайды":
                await show_guides(update, context)
            elif update.message.text == "Моды":
                await show_mods(update, context)
            elif update.message.text == "Социальные сети":
                await show_social(update, context)
            elif update.message.text == "Обзор патча":
                await show_patch(update, context, game)
        elif update.message.text == "Назад":
            await go_back(update, context)
        elif update.message.text == "Главное меню":
            await main_menu(update, context)
        elif update.message.text in ["Гайд для новичка", "Включить консоль и свободную камеру", "Консольные команды", "Конвой на 8+ человек"]:
            await handle_guide_selection(update, context)
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

# Добавление обработчиков
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^(ATS|ETS)$'), handle_game_selection))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^(Гайды|Моды|Обзор патча|Социальные сети|Главное меню|Назад|Гайд для новичка|Включить консоль и свободную камеру|Консольные команды|Конвой на 8\+ человек)$'), handle_mods_selection))
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