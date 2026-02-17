import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from loguru import logger

# Define states for conversation
class Form(StatesGroup):
    waiting_for_username_platform = State()  # Выбор платформы для поиска
    waiting_for_username_input = State()  # Ввод никнейма
    waiting_for_username_similar = State()  # Похожие никнеймы
    waiting_for_username_profile = State()  # Просмотр профиля
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

# Initialize bot and dispatcher
bot = Bot(token=settings.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Platform keyboard for username search
def get_platform_keyboard():
    """Create keyboard for platform selection"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton('📱 Telegram'))
    keyboard.add(KeyboardButton('📸 Instagram'))
    keyboard.add(KeyboardButton('🎵 TikTok'))
    keyboard.add(KeyboardButton('🌐 Web (Скоро...)'))
    keyboard.add(KeyboardButton('❌ Отмена'))
    return keyboard

# Similar usernames keyboard (up to 7)
def get_similar_usernames_keyboard(similar_usernames: list, platform: str):
    """Create inline keyboard with similar usernames as buttons"""
    keyboard = InlineKeyboardMarkup()
    for username in similar_usernames[:7]:
        keyboard.add(InlineKeyboardButton(
            text=f"@{username}",
            callback_data=f"user_profile:{platform}:{username}"
        ))
    # Add "Search more" button
    keyboard.add(InlineKeyboardButton(
        text="🔄 Поискать ещё",
        callback_data=f"user_more:{platform}"
    ))
    return keyboard

# Mock function to generate similar usernames
# In production, this would call an API or use a database
def get_similar_usernames(base_username: str, platform: str) -> list:
    """Generate similar usernames (mock implementation)"""
    import random
    similar = []
    # Generate 5-7 similar usernames based on base
    base = base_username.lower().strip()
    variations = [
        f"{base}_{random.choice(['official', 'real', 'the', ''])}",
        f"{base}{random.randint(1, 99)}",
        f"the_{base}",
        f"{base}.ru",
        f"{base}_bot",
        f"i_{base}",
        base * 2,
    ]
    random.shuffle(variations)
    # Add the original username
    similar.append(base)
    # Add 4-6 variations
    for v in variations[:random.randint(4, 6)]:
        similar.append(v)
    return similar[:7]

# Mock function to get full profile info
# In production, this would scrape the actual platform
def get_profile_info(username: str, platform: str) -> dict:
    """Get full profile information (mock implementation)"""
    import random
    
    # Common mock data for demonstration
    profiles_data = {
        'telegram': {
            'name': f'User {username}',
            'first_name': username.capitalize(),
            'last_name': 'LastName',
            'phone': f'+79{random.randint(100000000, 999999999)}',
            'user_id': random.randint(100000000, 999999999),
            'country': random.choice(['Russia', 'Ukraine', 'Belarus', 'Kazakhstan', 'USA']),
            'bio': f'Profile of @{username}',
        },
        'instagram': {
            'name': f'Instagram User {username}',
            'first_name': username.capitalize(),
            'last_name': 'LastName',
            'phone': f'+79{random.randint(100000000, 999999999)}',
            'user_id': random.randint(100000000, 999999999),
            'country': random.choice(['Russia', 'Ukraine', 'Belarus', 'Kazakhstan', 'USA']),
            'bio': f'Instagram profile @{username}',
        },
        'tiktok': {
            'name': f'TikTok User {username}',
            'first_name': username.capitalize(),
            'last_name': 'LastName',
            'phone': f'+79{random.randint(100000000, 999999999)}',
            'user_id': random.randint(100000000, 999999999),
            'country': random.choice(['Russia', 'Ukraine', 'Belarus', 'Kazakhstan', 'USA']),
            'bio': f'TikTok profile @{username}',
        },
    }
    
    return profiles_data.get(platform, profiles_data['telegram'])

@dp.message(Command(commands=['start']))
async def send_welcome(message: types.Message):
    """Send welcome message and help."""
    welcome_text = (
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот для OSINT-разведки. Вот что я умею:\n\n"
        "🔍 /osint_username - Поиск по никнейму\n"
        "📱 /osint_phone - Поиск по номеру телефона\n"
        "📧 /osint_email - Поиск по email\n"
        "🌍 /osint_domain - Анализ домена или IP\n\n"
        "Используйте /help для справки."
    )
    await message.reply(welcome_text)

@dp.message(Command(commands=['help']))
async def help_command(message: types.Message):
    """Send help message."""
    help_text = (
        "*Доступные команды:*\n\n"
        "*Основные команды:*\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n\n"
        "*OSINT-инструменты:*\n"
        "/osint_username - Поиск по никнейму (Telegram, Instagram, TikTok)\n"
        "/osint_phone - Анализ номера телефона\n"
        "/osint_email - Анализ email\n"
        "/osint_domain - Анализ домена или IP\n\n"
        "*Примеры:*\n"
        "/osint_username\n"
        "/osint_phone +79123456789\n"
        "/osint_email example@domain.com\n"
        "/osint_domain example.com"
    )
    await message.reply(help_text)

@dp.message(Command(commands=['osint_username']))
async def cmd_osint_username(message: types.Message, state: FSMContext):
    """Handle username search command - step 1: select platform"""
    await state.clear()  # Сбросить любое предыдущее состояние
    await Form.waiting_for_username_platform.set()

    platform_text = (
        "🔍 *Поиск по никнейму*\n\n"
        "Выберите платформу для поиска:\n\n"
        "📱 Telegram - поиск в Telegram\n"
        "📸 Instagram - поиск в Instagram\n"
        "🎵 TikTok - поиск в TikTok\n"
        "🌐 Web - поиск по другим источникам (скоро...)"
    )
    
    await message.reply(platform_text, reply_markup=get_platform_keyboard(), parse_mode='markdown')

@dp.message(State(Form.waiting_for_username_platform))
async def process_platform_selection(message: types.Message, state: FSMContext):
    """Process platform selection and ask for username"""
    platform = message.text.strip()
    
    if platform.lower() in ['отмена', '❌ отмена', 'cancel']:
        await state.clear()
        await message.reply("❌ Отменено", reply_markup=ReplyKeyboardRemove())
        return
    
    # Map button text to platform
    platform_map = {
        '📱 telegram': 'telegram',
        '📸 instagram': 'instagram',
        '🎵 tiktok': 'tiktok',
        '🌐 web (скоро...)': 'web',
    }
    
    platform_key = platform.lower()
    if platform_key not in platform_map:
        await message.reply("❌ Пожалуйста, выберите платформу из списка:")
        return
    
    selected_platform = platform_map[platform_key]
    
    if selected_platform == 'web':
        await state.clear()
        await message.reply("🌐 *Web поиск скоро будет доступен...*", 
                           reply_markup=ReplyKeyboardRemove(), 
                           parse_mode='markdown')
        return
    
    # Save platform to state
    await state.update_data(selected_platform=selected_platform)
    await Form.waiting_for_username_input.set()
    
    platform_names = {
        'telegram': 'Telegram',
        'instagram': 'Instagram', 
        'tiktok': 'TikTok'
    }
    
    await message.reply(
        f"📱 Выбрана платформа: *{platform_names.get(selected_platform, selected_platform)}*\n\n"
        f"Введите никнейм для поиска:",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Отмена')),
        parse_mode='markdown'
    )

@dp.message(State(Form.waiting_for_username_input))
async def process_username_input(message: types.Message, state: FSMContext):
    """Process username input and show similar usernames"""
    if message.text.lower() in ['отмена', '❌ отмена', 'cancel']:
        await state.clear()
        await message.reply("❌ Отменено", reply_markup=ReplyKeyboardRemove())
        return
    
    username = message.text.strip().lstrip('@')
    if not username:
        await message.reply("❌ Никнейм не может быть пустым. Пожалуйста, введите никнейм:")
        return

    # Get platform from state
    user_data = await state.get_data()
    platform = user_data.get('selected_platform', 'telegram')
    
    # Save current search
    await state.update_data(current_username=username, current_platform=platform)
    
    # Get similar usernames (mock)
    similar_usernames = get_similar_usernames(username, platform)
    await state.update_data(similar_usernames=similar_usernames)
    
    await Form.waiting_for_username_similar.set()
    
    # Show typing action
    await bot.send_chat_action(message.chat.id, 'typing')
    
    platform_names = {
        'telegram': 'Telegram',
        'instagram': 'Instagram',
        'tiktok': 'TikTok'
    }
    
    similar_text = (
        f"🔍 *Похожие никнеймы в {platform_names.get(platform, platform)}:*\n\n"
        "Выберите пользователя из списка или нажмите 'Поискать ещё':"
    )
    
    await message.reply(
        similar_text,
        reply_markup=get_similar_usernames_keyboard(similar_usernames, platform),
        parse_mode='markdown'
    )

@dp.callback_query(State(Form.waiting_for_username_similar))
async def process_similar_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Process callback from similar username selection"""
    await callback_query.answer()
    
    data = callback_query.data
    action, platform, *rest = data.split(':')
    platform = ':'.join(rest) if rest else platform  # Handle platform with colon
    
    if action == 'user_profile':
        username = rest[-1] if rest else ''
        if not username:
            await callback_query.message.edit_text("❌ Ошибка выбора пользователя")
            return
        
        # Get profile info
        profile = get_profile_info(username, platform)
        
        profile_text = (
            f"👤 *Профиль пользователя @{username}*\n\n"
            f"📱 *Платформа:* {platform.capitalize()}\n\n"
            f"📛 *Имя:* {profile.get('first_name', 'N/A')}\n"
            f"📛 *Фамилия:* {profile.get('last_name', 'N/A')}\n"
            f"📞 *Телефон:* {profile.get('phone', 'N/A')}\n"
            f"🆔 *Telegram ID:* {profile.get('user_id', 'N/A')}\n"
            f"🌍 *Страна:* {profile.get('country', 'N/A')}\n"
            f"📝 *О себе:* {profile.get('bio', 'N/A')}"
        )
        
        await callback_query.message.edit_text(
            profile_text,
            parse_mode='markdown',
            reply_markup=None
        )
        await state.clear()
        
    elif action == 'user_more':
        # Generate new similar usernames (mock)
        user_data = await state.get_data()
        current_username = user_data.get('current_username', '')
        
        new_similar = get_similar_usernames(current_username + '_new', platform)
        await state.update_data(similar_usernames=new_similar)
        
        await callback_query.message.edit_text(
            "🔄 *Новые похожие никнеймы:*\n\nВыберите пользователя:",
            reply_markup=get_similar_usernames_keyboard(new_similar, platform),
            parse_mode='markdown'
        )

@dp.message(Command(commands=['cancel']))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Allow user to cancel any action"""
    current_state = await state.get_state()
    if current_state is None:
        await message.reply("❌ Нет активных действий для отмены.")
        return
    
    await state.clear()
    await message.reply("❌ Действие отменено.", reply_markup=ReplyKeyboardRemove())


@dp.message(Command(commands=['osint_phone']))
async def cmd_osint_phone(message: types.Message, state: FSMContext):
    """Handle phone search command"""
    await state.clear()  # Сбросить любое предыдущее состояние
    await Form.waiting_for_phone.set()
    cancel_btn = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Отмена'))
    await message.reply("📱 Введите номер телефона (можно с + и -):", reply_markup=cancel_btn)


@dp.message(State(Form.waiting_for_phone))
async def process_phone(message: types.Message, state: FSMContext):
    """Process phone input and show results"""
    if message.text and message.text.lower() in ['отмена', '❌ отмена', 'cancel']:
        await state.clear()
        await message.reply("❌ Отменено", reply_markup=ReplyKeyboardRemove())
        return
    
    if not message.text:
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
        
        # Format and send results
        response = format_result(result)
        await message.reply(response, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in process_phone: {e}")
        await message.reply("❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.")
    finally:
        await state.clear()


@dp.message(Command(commands=['osint_email']))
async def cmd_osint_email(message: types.Message, state: FSMContext):
    """Handle email search command"""
    await state.clear()
    await Form.waiting_for_email.set()
    cancel_btn = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Отмена'))
    await message.reply("📧 Введите email адрес:", reply_markup=cancel_btn)


@dp.message(State(Form.waiting_for_email))
async def process_email(message: types.Message, state: FSMContext):
    """Process email input and show results"""
    if message.text and message.text.lower() in ['отмена', '❌ отмена', 'cancel']:
        await state.clear()
        await message.reply("❌ Отменено", reply_markup=ReplyKeyboardRemove())
        return
    
    if not message.text:
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
        
        # Format and send results
        response = format_result(result)
        await message.reply(response, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in process_email: {e}")
        await message.reply("❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.")
    finally:
        await state.clear()


@dp.message(Command(commands=['osint_domain']))
async def cmd_osint_domain(message: types.Message, state: FSMContext):
    """Handle domain analysis command"""
    await state.clear()
    await Form.waiting_for_domain.set()
    cancel_btn = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Отмена'))
    await message.reply("🌍 Введите домен или IP адрес:", reply_markup=cancel_btn)


@dp.message(State(Form.waiting_for_domain))
async def process_domain(message: types.Message, state: FSMContext):
    """Process domain input and show results"""
    if message.text and message.text.lower() in ['отмена', '❌ отмена', 'cancel']:
        await state.clear()
        await message.reply("❌ Отменено", reply_markup=ReplyKeyboardRemove())
        return
    
    if not message.text:
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
        await state.clear()

# Debug handler - отвечает на любое текстовое сообщение
@dp.message()
async def debug_handler(message: types.Message):
    """Debug handler - отвечает на любое сообщение"""
    logger.info(f"Received message: {message.text} from {message.from_user.id}")
    await message.reply(f"✅ Бот работает! Получено: {message.text}\n\nИспользуйте /help для списка команд.")

async def start_bot():
    """Start the bot."""
    try:
        logger.info("🚀 Starting OSINT Bot...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
    finally:
        await bot.session.close()
        logger.info("OSINT Bot has been stopped")

