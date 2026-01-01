import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.files import JSONStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from loguru import logger

# Define states for conversation
class Form(StatesGroup):
    waiting_for_username = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_domain = State()

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
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "🔍 Я бот для OSINT-разведки. Вот что я умею:\n\n"
        "• /osint_username [ник] - Поиск по никнейму\n"
        "• /osint_phone [телефон] - Поиск по номеру телефона\n"
        "• /osint_email [email] - Поиск по email\n"
        "• /osint_domain [домен] - Анализ домена или IP\n"
        "\nИспользуйте /help для справки."
    )
    await message.reply(welcome_text)

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    """Send help message."""
    help_text = (
        "🔍 *Доступные команды:*\n\n"
        "*Основные команды:*\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n\n"
        "*OSINT-инструменты:*\n"
        "/osint_username [ник] - Поиск по никнейму\n"
        "/osint_phone [телефон] - Анализ номера телефона\n"
        "/osint_email [email] - Анализ email\n"
        "/osint_domain [домен] - Анализ домена или IP\n\n"
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
        logger.info("👋 OSINT Bot has been stopped")
