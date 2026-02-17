import os
import asyncio
import random
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from loguru import logger
from collections import defaultdict

# Store group members for lottery feature
group_members = defaultdict(set)  # {group_id: {(user_id, name), ...}}

# Active lobby participants and message tracking for /random_1
participants_lobby = defaultdict(dict)  # {chat_id: {user_id: name, ...}}
lobby_message_id = {}  # {chat_id: message_id}
lobby_open = set()  # set of chat_ids with open lobby

# Define states for conversation
class Form(StatesGroup):
    waiting_for_username = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_domain = State()
    waiting_for_member_names = State()

# Load environment variables from .env file first
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Import settings after loading environment variables
from config.settings import settings
from src.modules.osint.username import search_username
from src.modules.osint.scrapers import scrape_username_info
from src.modules.osint.phone import search_phone, search_phone_on_sites
from src.modules.osint.email import search_email, get_email_domain_info
from src.modules.osint.domain import analyze_domain_complete
from src.utils.formatter import format_result, extract_images_from_result

# Debug print to verify settings
print("Debug - BOT_TOKEN in settings:", getattr(settings, 'BOT_TOKEN', 'NOT FOUND'))

# Initialize bot and dispatcher without HTML parse mode
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """Send welcome message and help."""
    welcome_text = (
        f" Привет, {message.from_user.first_name}!\n\n"
        " Я бот для OSINT-разведки. Вот что я умею:\n\n"
        "• /osint_username [ник] - Поиск по никнейму\n"
        "• /osint_phone [телефон] - Поиск по номеру телефона\n"
        "• /osint_email [email] - Поиск по email\n"
        "• /osint_domain [домен] - Анализ домена или IP\n"
        "\nИспользуйте /help для справки."
        "\n\nДля работы в группах используйте /random_1."
    )
    await message.reply(welcome_text)

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    """Send help message."""
    help_text = (
        "*Доступные команды:*\n\n"
        "*Основные команды:*\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n\n"
        "*OSINT-инструменты:*\n"
        "/osint_username [ник] - Поиск по никнейму\n"
        "/osint_phone [телефон] - Анализ номера телефона\n"
        "/osint_email [email] - Анализ email\n"
        "/osint_domain [домен] - Анализ домена или IP\n\n"
        "*Групповые команды:*\n"
        "/random_1 - Распределить случайные числа (0-50) участникам группы\n\n"
        "*Примеры:*\n"
        "/osint_username johndoe\n"
        "/osint_phone +79123456789\n"
        "/osint_email example@domain.com\n"
        "/osint_domain example.com"
    )
    await message.reply(help_text)

@dp.message_handler(commands=['osint_username'])
async def cmd_osint_username(message: types.Message, state: FSMContext):
    """Handle username search command - step 1: ask for username"""
    await Form.waiting_for_username.set()
    cancel_btn = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Отмена'))
    await message.reply("🔍 Введите никнейм для поиска:", reply_markup=cancel_btn)

@dp.message_handler(state=Form.waiting_for_username)
async def process_username(message: types.Message, state: FSMContext):
    """Process username input and show results"""
    if message.text.lower() in ['отмена', '❌ отмена', 'cancel']:
        await state.finish()
        await message.reply("❌ Отменено", reply_markup=ReplyKeyboardRemove())
        return
    
    username = message.text.strip()
    if not username:
        await message.reply("❌ Никнейм не может быть пустым. Пожалуйста, введите никнейм:")
        return

    await message.reply("🔍 Ищу информацию...", reply_markup=ReplyKeyboardRemove())
    
    try:
        # Show typing action
        await bot.send_chat_action(message.chat.id, 'typing')
        
        # Search for username asynchronously
        result = await search_username(username)
        
        # Extract and send images if found
        images = extract_images_from_result(result)
        if images:
            try:
                if len(images) == 1:
                    # Send single photo
                    await bot.send_photo(message.chat.id, images[0])
                else:
                    # Send multiple photos as album
                    media_group = [types.InputMediaPhoto(media=img) for img in images[:10]]  # Max 10 photos
                    await bot.send_media_group(message.chat.id, media_group)
            except Exception as e:
                logger.debug(f"Could not send images: {e}")
        
        # Format and send results
        response = format_result(result)
        await message.reply(response, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in process_username: {e}")
        await message.reply("❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.")
    finally:
        await state.finish()

@dp.message_handler(commands=['cancel'], state='*')
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Allow user to cancel any action"""
    current_state = await state.get_state()
    if current_state is None:
        await message.reply("❌ Нет активных действий для отмены.")
        return
    
    await state.finish()
    await message.reply("❌ Действие отменено.", reply_markup=ReplyKeyboardRemove())


@dp.message_handler(commands=['osint_phone'])
async def cmd_osint_phone(message: types.Message, state: FSMContext):
    """Handle phone search command"""
    await Form.waiting_for_phone.set()
    cancel_btn = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Отмена'))
    await message.reply("📱 Введите номер телефона (можно с + и -):", reply_markup=cancel_btn)


@dp.message_handler(state=Form.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    """Process phone input and show results"""
    if message.text.lower() in ['отмена', '❌ отмена', 'cancel']:
        await state.finish()
        await message.reply("❌ Отменено", reply_markup=ReplyKeyboardRemove())
        return
    
    phone = message.text.strip()
    if not phone:
        await message.reply("❌ Номер телефона не может быть пустым. Пожалуйста, введите номер:")
        return

    await message.reply("🔍 Ищу информацию по номеру телефона...", reply_markup=ReplyKeyboardRemove())
    
    try:
        await bot.send_chat_action(message.chat.id, 'typing')
        
        # Search for phone
        result = await search_phone(phone)
        
        # Extract and send images if found
        images = extract_images_from_result(result)
        if images:
            try:
                if len(images) == 1:
                    # Send single photo
                    await bot.send_photo(message.chat.id, images[0])
                else:
                    # Send multiple photos as album
                    media_group = [types.InputMediaPhoto(media=img) for img in images[:10]]  # Max 10 photos
                    await bot.send_media_group(message.chat.id, media_group)
            except Exception as e:
                logger.debug(f"Could not send images: {e}")
        
        # Format and send results
        response = format_result(result)
        await message.reply(response, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in process_phone: {e}")
        await message.reply("❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.")
    finally:
        await state.finish()


@dp.message_handler(commands=['osint_email'])
async def cmd_osint_email(message: types.Message, state: FSMContext):
    """Handle email search command"""
    await Form.waiting_for_email.set()
    cancel_btn = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Отмена'))
    await message.reply("📧 Введите email адрес:", reply_markup=cancel_btn)


@dp.message_handler(state=Form.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    """Process email input and show results"""
    if message.text.lower() in ['отмена', '❌ отмена', 'cancel']:
        await state.finish()
        await message.reply("❌ Отменено", reply_markup=ReplyKeyboardRemove())
        return
    
    email = message.text.strip()
    if not email:
        await message.reply("❌ Email не может быть пустым. Пожалуйста, введите email:")
        return

    await message.reply("🔍 Ищу информацию по email адресу...", reply_markup=ReplyKeyboardRemove())
    
    try:
        await bot.send_chat_action(message.chat.id, 'typing')
        
        # Search for email
        result = await search_email(email)
        
        # Extract and send images if found
        images = extract_images_from_result(result)
        if images:
            try:
                if len(images) == 1:
                    # Send single photo
                    await bot.send_photo(message.chat.id, images[0])
                else:
                    # Send multiple photos as album
                    media_group = [types.InputMediaPhoto(media=img) for img in images[:10]]  # Max 10 photos
                    await bot.send_media_group(message.chat.id, media_group)
            except Exception as e:
                logger.debug(f"Could not send images: {e}")
        
        # Format and send results
        response = format_result(result)
        await message.reply(response, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in process_email: {e}")
        await message.reply("❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.")
    finally:
        await state.finish()


@dp.message_handler(commands=['osint_domain'])
async def cmd_osint_domain(message: types.Message, state: FSMContext):
    """Handle domain analysis command"""
    await Form.waiting_for_domain.set()
    cancel_btn = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Отмена'))
    await message.reply("🌍 Введите домен или IP адрес:", reply_markup=cancel_btn)


@dp.message_handler(state=Form.waiting_for_domain)
async def process_domain(message: types.Message, state: FSMContext):
    """Process domain input and show results"""
    if message.text.lower() in ['отмена', '❌ отмена', 'cancel']:
        await state.finish()
        await message.reply("❌ Отменено", reply_markup=ReplyKeyboardRemove())
        return
    
    domain = message.text.strip()
    if not domain:
        await message.reply("❌ Домен не может быть пустым. Пожалуйста, введите домен:")
        return

    await message.reply("🔍 Анализирую домен/IP адрес...", reply_markup=ReplyKeyboardRemove())
    
    try:
        await bot.send_chat_action(message.chat.id, 'typing')
        
        # Analyze domain
        result = await analyze_domain_complete(domain)
        
        # Format and send results
        response = format_result(result)
        await message.reply(response, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in process_domain: {e}")
        await message.reply("❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.")
    finally:
        await state.finish()

@dp.message_handler(commands=['random_1'])
async def cmd_random_lottery(message: types.Message):
    """Open a lobby for users to join via button."""

    if message.chat.type not in ['group', 'supergroup']:
        await message.reply("❌ Эта команда работает только в групповых чатах.")
        return

    chat_id = message.chat.id
    if chat_id in lobby_open:
        await message.reply('❗ Набор уже открыт. Нажмите кнопку "Участвовать" или закройте набор командой /stop_in.')
        return

    # Open lobby
    lobby_open.add(chat_id)
    participants_lobby[chat_id] = {}

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton(text='Участвовать', callback_data=f'lottery_join:{chat_id}')
    )

    sent = await message.reply("Это набор участников для раздачи номеров Random. Нажмите кнопку, чтобы записаться. Команда /stop_in закроет набор.", reply_markup=keyboard)
    lobby_message_id[chat_id] = sent.message_id


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('lottery_join:'))
async def callback_lottery_join(callback_query: types.CallbackQuery):
    """Handle user joining the lottery via inline button."""
    try:
        data = callback_query.data
        _, chat_id_str = data.split(':', 1)
        chat_id = int(chat_id_str)
        user = callback_query.from_user
        name = user.first_name or user.username or 'Unknown'

        # Add to lobby participants
        participants_lobby[chat_id][user.id] = name
        # Also remember in historical members
        group_members[chat_id].add((user.id, name))

        await callback_query.answer('✅ Вы записаны на участие', show_alert=False)

        # Optionally edit lobby message to show count
        if chat_id in lobby_message_id:
            try:
                msg_id = lobby_message_id[chat_id]
                count = len(participants_lobby[chat_id])
                await bot.edit_message_text(
                    f"Набор на участие открыт! Нажмите кнопку, чтобы записаться. (Записано: {count})\nКоманда /stop_in закроет набор.",
                    chat_id=chat_id,
                    message_id=msg_id,
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton(text='Участвовать', callback_data=f'lottery_join:{chat_id}')
                    )
                )
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error in callback_lottery_join: {e}")


@dp.message_handler(commands=['stop_in'])
async def cmd_stop_lottery(message: types.Message):
    """Close lobby and distribute numbers to participants."""
    chat_id = message.chat.id
    if chat_id not in lobby_open:
        await message.reply('❗ Набор не открыт.')
        return

    # Only admins or creator can stop the lobby
    try:
        member = await bot.get_chat_member(chat_id, message.from_user.id)
        if member.status not in ['administrator', 'creator']:
            await message.reply('❌ Только администратор может закрыть набор.')
            return
    except Exception as e:
        logger.debug(f"Error checking admin status for stop_in: {e}")
        await message.reply('❌ Не удалось проверить права. Попробуйте снова.')
        return

    # Close lobby
    lobby_open.discard(chat_id)

    # Remove inline keyboard
    if chat_id in lobby_message_id:
        try:
            await bot.edit_message_reply_markup(chat_id, lobby_message_id[chat_id], reply_markup=None)
        except Exception:
            pass

    participants = list(participants_lobby.get(chat_id, {}).items())  # [(user_id, name), ...]
    if not participants:
        await message.reply('ℹ️ Никто не записался на участие.')
        participants_lobby.pop(chat_id, None)
        lobby_message_id.pop(chat_id, None)
        return

    # Shuffle participants
    random.shuffle(participants)

    distribution = []
    if len(participants) <= 50:
        numbers = list(range(1, 51))
        random.shuffle(numbers)
        for i, (user_id, name) in enumerate(participants):
            distribution.append((name, numbers[i]))
    else:
        numbers = list(range(1, 51))
        random.shuffle(numbers)
        # first 50
        for i in range(50):
            user_id, name = participants[i]
            distribution.append((name, numbers[i]))
        # rest 1-10 random
        for user_id, name in participants[50:]:
            distribution.append((name, random.randint(1, 10)))

    # Build and send result
    result_message = '🎲 *РЕЗУЛЬТАТЫ РАСПРЕДЕЛЕНИЯ ЧИСЕЛ:*\n\n'
    for i, (name, number) in enumerate(distribution, 1):
        result_message += f"{i}. {name}: *{number}*\n"

    result_message += f"\n📊 *Всего участников: {len(distribution)}*"
    if len(participants) > 50:
        result_message += f"\n\n⚠️ В группе {len(participants)} записавшихся. Первые 50 получили числа 1-50. Остальные получили числа 1-10."

    await message.reply(result_message, parse_mode='markdown')

    # cleanup
    participants_lobby.pop(chat_id, None)
    lobby_message_id.pop(chat_id, None)

@dp.message_handler(content_types=types.ContentType.ANY)
async def track_group_members(message: types.Message):
    """Track users who interact in the group.

    - Add `from_user` for any message type (text, photo, sticker, etc.).
    - Also register `new_chat_members` service messages.
    """
    if message.chat.type not in ['group', 'supergroup']:
        return

    # Register users who send messages (covers text, photos, stickers, etc.)
    user = message.from_user
    if user:
        name = (user.first_name or '') + (f" {user.last_name}" if user.last_name else '')
        name = name.strip() or user.username or 'Unknown'
        group_members[message.chat.id].add((user.id, name))

    # If there are new chat members (service message), register them too
    if hasattr(message, 'new_chat_members') and message.new_chat_members:
        for new_user in message.new_chat_members:
            name = (new_user.first_name or '') + (f" {new_user.last_name}" if new_user.last_name else '')
            name = name.strip() or new_user.username or 'Unknown'
            group_members[message.chat.id].add((new_user.id, name))

    # Don't consume message, let other handlers process it
    return

async def start_bot():
    """Start the bot."""
    try:
        logger.info("🚀 Starting OSINT Bot...")
        await dp.skip_updates()
        await dp.start_polling()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
    finally:
        await bot.close()
        logger.info("OSINT Bot has been stopped")
