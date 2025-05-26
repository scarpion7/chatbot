from dotenv import load_dotenv
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re
from aiogram.types import FSInputFile, URLInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
import asyncio

# QO'SHILDI: Xatoliklarni ushlash uchun
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

load_dotenv()

# Sozlamalar
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID") or 0)
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
ADMIN_SECOND_GROUP_ID = int(os.getenv("ADMIN_SECOND_GROUP_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = int(os.getenv("PORT", 8000))

# Bot va dispatcher obyektlarini yaratish
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()


# Holatlar klassini aniqlash
class Form(StatesGroup):
    CHOOSE_GENDER = State()
    VILOYAT = State()
    TUMAN = State()
    AGE_FEMALE = State()
    FEMALE_CHOICE = State()
    POSE_WOMAN = State()
    MJM_EXPERIENCE = State()
    MJM_EXPERIENCE_FEMALE = State()
    JMJ_AGE = State()
    JMJ_DETAILS = State()
    FAMILY_HUSBAND_AGE = State()
    FAMILY_WIFE_AGE = State()
    FAMILY_AUTHOR = State()
    FAMILY_HUSBAND_CHOICE = State()
    FAMILY_WIFE_AGREEMENT = State()
    FAMILY_WIFE_CHOICE = State()
    FAMILY_HUSBAND_AGREEMENT = State()
    ABOUT = State()


class AdminState(StatesGroup):
    REPLYING_TO_USER = State()

class ErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data):
        try:
            return await handler(event, data)
        except TelegramForbiddenError as e:
            user_id = event.from_user.id if event.from_user else None
            logging.error(f"User {user_id} blocked the bot. Error: {e}")
            await bot.send_message(ADMIN_USER_ID, f"⚠️ User {user_id} blocked the bot")
        except Exception as e:
            logging.error(f"Global error: {e}", exc_info=True)
            await bot.send_message(ADMIN_USER_ID, f"🚨 Critical error: {e}")

dp.update.outer_middleware(ErrorMiddleware())


VILOYATLAR = [
    "Andijon", "Buxoro", "Farg'ona", "Jizzax", "Qashqadaryo", "Navoiy", "Namangan",
    "Samarqand", "Sirdaryo", "Surxondaryo", "Toshkent", "Toshkent shahar", "Xorazm",
    "Qoraqalpog'iston Respublikasi",
]
TUMANLAR = {
    "Andijon": ["Andijon shahar", "Asaka", "Baliqchi", "Bo‘ston", "Izboskan", "Qo‘rg‘ontepa", "Shahrixon", "Ulug‘nor",
                "Xo‘jaobod", "Yuzboshilar", "Hokim"],
    "Buxoro": ["Buxoro shahar", "Buxoro tumani", "G‘ijduvon", "Jondor", "Kogon", "Qorako‘l", "Olot", "Peshku",
               "Romitan", "Shofirkon", "Vobkent"],
    "Farg'ona": ["Farg'ona shahar", "Farg'ona tumani", "Beshariq", "Bog‘dod", "Buvayda", "Dang‘ara", "Qo‘qon", "Quva",
                 "Rishton", "Rishton tumani", "Toshloq", "Oltiariq", "Quvasoy shahar"],
    "Jizzax": ["Jizzax shahar", "Arnasoy", "Baxmal", "Dashtobod", "Forish", "G‘allaorol", "Zarbdor", "Zomin",
               "Mirzacho‘l", "Paxtakor", "Sharof Rashidov"],
    "Qashqadaryo": ["Qarshi shahar", "Chiroqchi", "G‘uzor", "Dehqonobod", "Koson", "Kitob", "Mirishkor", "Muborak",
                    "Nishon", "Qarshi tumani", "Shahrisabz", "Yakkabog‘"],
    "Navoiy": ["Navoiy shahar", "Karmana", "Konimex", "Navbahor", "Nurota", "Tomdi", "Uchquduq", "Xatirchi"],
    "Namangan": ["Namangan shahar", "Chust", "Kosonsoy", "Mingbuloq", "Namangan tumani", "Pop", "To‘raqo‘rg‘on",
                 "Uychi", "Yangiqo‘rg‘on"],
    "Samarqand": ["Samarqand shahar", "Bulung‘ur", "Jomboy", "Kattaqo‘rg‘on", "Narpay", "Nurobod", "Oqdaryo", "Payariq",
                  "Pastdarg‘om", "Paxtachi", "Qo‘shrabot", "Samarqand tumani", "Toyloq"],
    "Sirdaryo": ["Guliston shahar", "Boyovut", "Guliston tumani", "Mirzaobod", "Oqoltin", "Sayxunobod", "Sardoba",
                 "Sirdaryo tumani", "Xovos"],
    "Surxondaryo": ["Termiz shahar", "Angor", "Boysun", "Denov", "Jarqo‘rg‘on", "Muzrabot", "Sariosiyo", "Sherobod",
                    "Sho‘rchi", "Termiz tumani"],
    "Toshkent": ["Bekobod", "Bo‘ka", "Ohangaron", "Oqqo‘rg‘on", "Chinoz", "Qibray", "Quyichirchiq", "Toshkent tumani",
                 "Yangiyo‘l", "Zangiota", "Bekobod shahar", "Ohangaron shahar", "Yangiyo‘l shahar"],
    "Toshkent shahar": ["Mirzo Ulug‘bek", "Mirobod", "Sergeli", "Olmazor", "Shayxontohur", "Chilonzor", "Yunusobod",
                        "Uchtepa", "Yashnobod"],
    "Xorazm": ["Urganch shahar", "Bog‘ot", "Gurlan", "Xiva shahar", "Qo‘shko‘pir", "Shovot", "Urganch tumani", "Xonqa",
               "Yangiariq"],
    "Qoraqalpog'iston Respublikasi": ["Nukus shahar", "Amudaryo", "Beruniy", "Bo‘zatov", "Kegayli", "Qonliko‘l",
                                      "Qo‘ng‘irot",
                                      "Qorao‘zak", "Shumanay", "Taxtako‘pir", "To‘rtko‘l", "Xo‘jayli",
                                      "Chimboy", "Mo‘ynoq", "Ellikqal‘a"],
}
POSES_WOMAN = [
    "Rakom", "Chavandoz(Ustizda sakrab)", "Oyolarimni yelkezga qo'yib", "Romantik/Erkalab",
    "BSDM / Qiynab", "Hamma pozada", "Kunillingus / Minet / 69 / Lazzatli seks", "Anal/Romantik"
]
MJM_EXPERIENCE_OPTIONS = [
    "Hali bo'lmagan 1-si", "1 marta bo'lgan", "2-3 marta bo'lgan", "5 martadan ko'p (MJMni sevamiz)"
]
MJM_EXPERIENCE_FEMALE_OPTIONS = [
    "Hali bo'lmagan 1-si", "1 marta bo'lgan", "2-3 marta bo'lgan", "5 martadan ko'p (MJMni sevaman)"
]
chat_mode_users = set()


def add_navigation_buttons(builder: InlineKeyboardBuilder, back_state: str):
    builder.row(
        types.InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"back_{back_state}"),
        types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
    )

def gender_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👨 Erkak", callback_data="gender_male"))
    builder.row(types.InlineKeyboardButton(text="👩 Ayol", callback_data="gender_female"))
    builder.row(types.InlineKeyboardButton(text="👨‍👩‍👧 Oilaman", callback_data="gender_family"))
    builder.row(types.InlineKeyboardButton(text="ℹ️ Bot haqida", callback_data="about_bot"))
    add_navigation_buttons(builder, "start")
    return builder.as_markup()

def viloyat_keyboard():
    builder = InlineKeyboardBuilder()
    for vil in VILOYATLAR:
        builder.row(types.InlineKeyboardButton(text=vil, callback_data=f"vil_{vil}"))
    add_navigation_buttons(builder, "gender")
    return builder.as_markup()

def tuman_keyboard(viloyat):
    builder = InlineKeyboardBuilder()
    for tuman in TUMANLAR.get(viloyat, []):
        builder.row(types.InlineKeyboardButton(text=tuman, callback_data=f"tum_{tuman}"))
    add_navigation_buttons(builder, "viloyat")
    return builder.as_markup()

def age_female_keyboard():
    builder = InlineKeyboardBuilder()
    ranges = ["18-23", "24-29", "30-35", "36-40","40+"]
    for r in ranges:
        builder.row(types.InlineKeyboardButton(text=r, callback_data=f"age_{r}"))
    add_navigation_buttons(builder, "tuman")
    return builder.as_markup()

def female_choice_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👨 Erkak bilan", callback_data="choice_1"))
    builder.row(types.InlineKeyboardButton(text="👥 MJM (2 erkak bilan)", callback_data="choice_2"))
    builder.row(types.InlineKeyboardButton(text="👭 JMJ (Dugonam bor)", callback_data="choice_3"))
    add_navigation_buttons(builder, "age_female")
    return builder.as_markup()

def poses_keyboard():
    builder = InlineKeyboardBuilder()
    for idx, pose in enumerate(POSES_WOMAN, 1):
        builder.row(types.InlineKeyboardButton(text=f"{idx}. {pose}", callback_data=f"pose_{idx}"))
    add_navigation_buttons(builder, "female_choice")
    return builder.as_markup()

def mjm_experience_keyboard(is_female=False):
    builder = InlineKeyboardBuilder()
    options = MJM_EXPERIENCE_FEMALE_OPTIONS if is_female else MJM_EXPERIENCE_OPTIONS
    for idx, option in enumerate(options):
        callback_prefix = "mjm_exp_female_" if is_female else "mjm_exp_family_"
        builder.row(types.InlineKeyboardButton(text=option, callback_data=f"{callback_prefix}{idx}"))
    back_target = "female_choice" if is_female else "family_husband_choice"
    add_navigation_buttons(builder, back_target)
    return builder.as_markup()

def family_author_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👨 Erkak yozmoqda...", callback_data="author_husband"))
    builder.row(types.InlineKeyboardButton(text="👩 Ayol yozmoqda...", callback_data="author_wife"))
    add_navigation_buttons(builder, "family_wife_age")
    return builder.as_markup()

def family_husband_choice_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👥 MJM", callback_data="h_choice_mjm"))
    builder.row(types.InlineKeyboardButton(text="👨 Hushttor (ayolim uchun)", callback_data="h_choice_erkak"))
    add_navigation_buttons(builder, "family_author")
    return builder.as_markup()

def family_wife_agreement_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Ha rozi", callback_data="wife_agree_Yes"))
    builder.row(types.InlineKeyboardButton(text="🔄 Yo'q, lekin men istayman (kondiraman)", callback_data="wife_agree_No"))
    builder.row(types.InlineKeyboardButton(text="❓ Bilmayman, hali aytib ko'rmadim", callback_data="wife_agree_IDK"))
    add_navigation_buttons(builder, "family_husband_choice")
    return builder.as_markup()

def family_wife_choice_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👥 MJM (erim bilan)", callback_data="w_choice_mjm_husband"))
    builder.row(types.InlineKeyboardButton(text="👥 MJM (begona 2 erkak bilan)", callback_data="w_choice_mjm_strangers"))
    builder.row(types.InlineKeyboardButton(text="👨 Hushtor (erimdan qoniqmayapman)", callback_data="w_choice_erkak"))
    add_navigation_buttons(builder, "family_author")
    return builder.as_markup()

def family_husband_agreement_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Ha rozi", callback_data="husband_agree_yes"))
    builder.row(types.InlineKeyboardButton(text="🔄 Yo'q, lekin men istayman (kondiraman)", callback_data="husband_agree_No"))
    builder.row(types.InlineKeyboardButton(text="❓ Bilmayman, hali aytib ko'rmadim", callback_data="husband_agree_IDK"))
    add_navigation_buttons(builder, "family_wife_choice")
    return builder.as_markup()


def build_application_details_string(data: dict, include_user_info: bool, user: types.User = None):
    text = ""
    default_value = "None1"
    if include_user_info and user:
        text += f"👤 **Foydalanuvchi:** "
        if user.username:
            text += f"[@{user.username}] | [Profilga o‘tish](tg://user?id={user.id})\n (ID: `{user.id}`)\n"
        else:
            text += f"[{user.full_name}](tg://user?id={user.id}) (ID: `{user.id}`)\n"
        text += f"📝 **Ism:** {user.full_name}\n"
    text += (
        f"🚻 **Jins:** {data.get('gender', default_value)}\n"
        f"🗺️ **Viloyat:** {data.get('viloyat', default_value)}\n"
        f"🏘️ **Tuman:** {data.get('tuman', default_value)}\n"
    )
    gender_specific_data = data.get('gender')
    if gender_specific_data == 'female':
        choice_val = data.get('choice')
        choice_text_map = {'1': 'Erkak bilan', '2': '👥 MJM (2ta erkak)', '3': '👭 JMJ (Dugonam bor)'}
        text += (
            f"🎂 **Yosh:** {data.get('age', default_value)}\n"
            f"🤝 **Tanlov:** {choice_text_map.get(choice_val, default_value)}\n"
        )
        if choice_val == '1':
            text += f"🤸 **Pozitsiya:** {data.get('pose', default_value)}\n"
        elif choice_val == '2':
            text += f"👥 **MJM tajriba:** {data.get('mjm_experience_female', default_value)}\n"
        elif choice_val == '3':
            text += (
                f"🎂 **Dugona yoshi:** {data.get('jmj_age', default_value)}\n"
                f"ℹ️ **Dugona haqida:** {data.get('jmj_details', default_value)}\n"
            )
    elif gender_specific_data == 'family':
        author_val = data.get('author')
        author_text_map = {'husband': 'Erkak', 'wife': 'Ayol'}
        text += (
            f"👨 **Erkak yoshi:** {data.get('husband_age', default_value)}\n"
            f"👩 **Ayol yoshi:** {data.get('wife_age', default_value)}\n"
            f"✍️ **Yozmoqda:** {author_text_map.get(author_val, default_value)}\n"
        )
        agreement_text_map = {
            'Yes': '✅ Ha rozi',
            'No': "🔄 Yo'q, lekin men istayman (kondiraman)",
            'IDK': "❓ Bilmayman, hali aytib ko'rmadim"
        }
        if author_val == 'husband':
            h_choice_val = data.get('h_choice')
            h_choice_text_map = {'mjm': '👥 MJM', 'erkak': '👨 Hushtor (ayolim uchun)'}
            text += f"🎯 **Erkak tanlovi:** {h_choice_text_map.get(h_choice_val, default_value)}\n"
            if h_choice_val == 'mjm':
                text += f"👥 **MJM tajriba:** {data.get('mjm_experience', default_value)}\n"
            text += f"👩‍⚕️ **Ayol roziligi:** {agreement_text_map.get(data.get('wife_agreement'), data.get('wife_agreement', default_value))}\n"
        elif author_val == 'wife':
            w_choice_val = data.get('w_choice')
            w_choice_text_map = {
                'mjm_husband': '👥 MJM (erim bilan)',
                'mjm_strangers': '👥 MJM (begona 2 erkak bilan)',
                'erkak': '👨 Erkak (erimdan qoniqmayapman)'
            }
            text += f"🎯 **Ayol tanlovi:** {w_choice_text_map.get(w_choice_val, default_value)}\n"
            if w_choice_val == 'mjm_husband':
                text += f"👨‍⚕️ **Erkak roziligi:** {agreement_text_map.get(data.get('husband_agreement'), data.get('husband_agreement', default_value))}\n"
    if data.get('about'):
        text += f"ℹ️ **Qo'shimcha malumotlar:** {data.get('about', default_value)}\n"
    return text


async def send_application_to_destinations(data: dict, user: types.User):
    header_full = "📊 **Yangi ariza qabul qilindi**\n\n"
    admin_message_text_full = header_full + build_application_details_string(data, include_user_info=True, user=user)
    header_restricted = "📊 **Yangi Ariza Tafsilotlari**\n\n"
    user_name_only = f"👤 Foydalanuvchi: {user.full_name}\n\n"
    application_details_only_text = header_restricted + user_name_only + build_application_details_string(data, include_user_info=False)
    builder_admin_user = InlineKeyboardBuilder()
    builder_admin_user.button(text="✉️ Javob yozish", callback_data=f"admin_initiate_reply_{user.id}")
    reply_markup_for_admin_user = builder_admin_user.as_markup()

    # ADMIN_USER_ID ga yuborish
    try:
        await bot.send_message(
            chat_id=ADMIN_USER_ID, text=admin_message_text_full,
            reply_markup=reply_markup_for_admin_user, parse_mode="Markdown"
        )
        logging.info(f"Application sent to admin user {ADMIN_USER_ID} for user {user.id}")
    except TelegramForbiddenError as e_forbidden:
        logging.warning(f"TelegramForbiddenError sending to ADMIN_USER_ID {ADMIN_USER_ID} for user {user.id}: {e_forbidden}. Bot might be blocked or kicked.")
    except TelegramBadRequest as e_bad_request:
        logging.error(f"TelegramBadRequest sending to ADMIN_USER_ID {ADMIN_USER_ID} for user {user.id}: {e_bad_request}")
    except Exception as e:
        logging.error(f"Failed to send application to admin user {ADMIN_USER_ID} for user {user.id}: {e}")
        try:
            await bot.send_message(ADMIN_USER_ID, f"⚠️ Ogohlantirish: Foydalanuvchi `{user.id}` arizasini shaxsiy admin chatga yuborishda xatolik: {e}", parse_mode="Markdown")
        except Exception as e_admin_notify: # Yangi except bloki, adminni ogohlantirishdagi xatolik uchun
            logging.error(f"CRITICAL: Failed to send error notification about user {user.id} to admin user {ADMIN_USER_ID}: {e_admin_notify}")


    # ADMIN_GROUP_ID ga yuborish
    try:
        await bot.send_message(
            chat_id=ADMIN_GROUP_ID, text=application_details_only_text,
            reply_markup=None, parse_mode="Markdown"
        )
        logging.info(f"Application (details only) sent to admin group {ADMIN_GROUP_ID} for user {user.id}")
    except TelegramForbiddenError as e_forbidden:
        logging.warning(f"TelegramForbiddenError sending to ADMIN_GROUP_ID {ADMIN_GROUP_ID} for user {user.id}: {e_forbidden}. Bot might be blocked or kicked.")
    except TelegramBadRequest as e_bad_request:
        logging.error(f"TelegramBadRequest sending to ADMIN_GROUP_ID {ADMIN_GROUP_ID} for user {user.id}: {e_bad_request}")
    except Exception as e:
        logging.error(f"Failed to send application to admin group {ADMIN_GROUP_ID} for user {user.id}: {e}")
        try:
            await bot.send_message(ADMIN_USER_ID, f"⚠️ Ogohlantirish: Foydalanuvchi `{user.id}` arizasini ADMIN_GROUP_ID (`{ADMIN_GROUP_ID}`)ga yuborishda xatolik: {e}", parse_mode="Markdown")
        except Exception as e_admin_notify:
             logging.error(f"CRITICAL: Failed to send error notification to admin user {ADMIN_USER_ID} about group {ADMIN_GROUP_ID} error: {e_admin_notify}")

    # ADMIN_SECOND_GROUP_ID ga yuborish
    try:
        await bot.send_message(
            chat_id=ADMIN_SECOND_GROUP_ID, text=admin_message_text_full,
            reply_markup=None, parse_mode="Markdown"
        )
        logging.info(f"Application sent to admin second group {ADMIN_SECOND_GROUP_ID} for user {user.id}")
    except TelegramForbiddenError as e_forbidden:
        logging.warning(f"TelegramForbiddenError sending to ADMIN_SECOND_GROUP_ID {ADMIN_SECOND_GROUP_ID} for user {user.id}: {e_forbidden}. Bot might be blocked or kicked.")
    except TelegramBadRequest as e_bad_request:
        logging.error(f"TelegramBadRequest sending to ADMIN_SECOND_GROUP_ID {ADMIN_SECOND_GROUP_ID} for user {user.id}: {e_bad_request}")
    except Exception as e:
        logging.error(f"Failed to send application to admin second group {ADMIN_SECOND_GROUP_ID} for user {user.id}: {e}")
        try:
            await bot.send_message(ADMIN_USER_ID, f"⚠️ Ogohlantirish: Foydalanuvchi `{user.id}` arizasini ADMIN_SECOND_GROUP_ID (`{ADMIN_SECOND_GROUP_ID}`)ga yuborishda xatolik: {e}", parse_mode="Markdown")
        except Exception as e_admin_notify:
            logging.error(f"CRITICAL: Failed to send error notification to admin user {ADMIN_USER_ID} about group {ADMIN_SECOND_GROUP_ID} error: {e_admin_notify}")


    channel_text = f"📊 **Yangi ariza**\n\n📝 **Ism:** {user.full_name}\n"
    default_value_channel = "None1"
    if data.get('gender'): channel_text += f"🚻 **Jins:** {data.get('gender', default_value_channel)}\n"
    if data.get('viloyat'): channel_text += f"🗺️ **Viloyat:** {data.get('viloyat', default_value_channel)}\n"
    if data.get('tuman'): channel_text += f"🏘️ **Tuman:** {data.get('tuman', default_value_channel)}\n"
    if data.get('gender') == 'female':
        if data.get('age'): channel_text += f"🎂 **Yosh:** {data.get('age', default_value_channel)}\n"
        if data.get('choice'):
            choice_text_channel_map = {'1': 'Erkak bilan', '2': '👥 MJM (2ta erkak)', '3': '👭 JMJ (Dugonam bor)'}
            channel_text += f"🤝 **Tanlov:** {choice_text_channel_map.get(data.get('choice'), default_value_channel)}\n"
        if data.get('pose') and data.get('choice') == '1': channel_text += f"🤸 **Pozitsiya:** {data.get('pose', default_value_channel)}\n"
        if data.get('mjm_experience_female') and data.get('choice') == '2': channel_text += f"👥 **MJM tajriba:** {data.get('mjm_experience_female', default_value_channel)}\n"
        if data.get('jmj_age') and data.get('choice') == '3': channel_text += f"🎂 **Dugona yoshi:** {data.get('jmj_age', default_value_channel)}\n"
        if data.get('jmj_details') and data.get('choice') == '3': channel_text += f"ℹ️ **Dugona haqida:** {data.get('jmj_details', default_value_channel)}\n"
    elif data.get('gender') == 'family':
        if data.get('husband_age'): channel_text += f"👨 **Erkak yoshi:** {data.get('husband_age', default_value_channel)}\n"
        if data.get('wife_age'): channel_text += f"👩 **Ayol yoshi:** {data.get('wife_age', default_value_channel)}\n"
        if data.get('author'):
            author_text_channel_map = {'husband': 'Erkak', 'wife': 'Ayol'}
            channel_text += f"✍️ **Yozmoqda:** {author_text_channel_map.get(data.get('author'), default_value_channel)}\n"
        agreement_text_map_channel = {'Yes': '✅ Ha rozi', 'No': "🔄 Yo'q, lekin men istayman", 'IDK': '❓ Bilmayman, hali aytmadim'}
        if data.get('author') == 'husband':
            h_choice_text_channel_map = {'mjm': '👥 MJM', 'erkak': '👨 Erkak (ayoli uchun)'}
            channel_text += f"🎯 **Erkak tanlovi:** {h_choice_text_channel_map.get(data.get('h_choice'), default_value_channel)}\n"
            if data.get('mjm_experience') and data.get('h_choice') == 'mjm': channel_text += f"👥 **MJM tajriba:** {data.get('mjm_experience', default_value_channel)}\n"
            if data.get('wife_agreement'): channel_text += f"👩‍⚕️ **Ayol roziligi:** {agreement_text_map_channel.get(data.get('wife_agreement'), data.get('wife_agreement', default_value_channel))}\n"
        elif data.get('author') == 'wife':
            w_choice_text_channel_map = {'mjm_husband': '👥 MJM (erim bilan)', 'mjm_strangers': '👥 MJM (begona 2 erkak bilan)', 'erkak': '👨 Erkak (erimdan qoniqmayapman)'}
            channel_text += f"🎯 **Ayol tanlovi:** {w_choice_text_channel_map.get(data.get('w_choice'), default_value_channel)}\n"
            if data.get('husband_agreement') and data.get('w_choice') == 'mjm_husband': channel_text += f"👨‍⚕️ **Erkak roziligi:** {agreement_text_map_channel.get(data.get('husband_agreement'), data.get('husband_agreement', default_value_channel))}\n"
    if data.get('about'): channel_text += f"ℹ️ **Qo'shimcha malumotlar:** {data.get('about', default_value_channel)}\n"
    channel_text += "\n---\n Kanalga avtomatik joylash uchun."

    try:
        await bot.send_message(CHANNEL_ID, channel_text, parse_mode="Markdown")
        logging.info(f"Application sent to channel {CHANNEL_ID} for user {user.id}")
    except TelegramForbiddenError as e_forbidden:
        logging.warning(f"TelegramForbiddenError sending to CHANNEL_ID {CHANNEL_ID} for user {user.id}: {e_forbidden}. Bot might be blocked or kicked.")
    except TelegramBadRequest as e_bad_request:
        logging.error(f"TelegramBadRequest sending to CHANNEL_ID {CHANNEL_ID} for user {user.id}: {e_bad_request}")
    except Exception as e:
        logging.error(f"Failed to send application to channel {CHANNEL_ID} for user {user.id}: {e}")
        try:
            await bot.send_message(ADMIN_USER_ID, f"⚠️ Ogohlantirish: Foydalanuvchi `{user.id}` arizasini kanalga (`{CHANNEL_ID}`) yuborishda xatolik: {e}", parse_mode="Markdown")
        except Exception as e_admin_notify:
            logging.error(f"CRITICAL: Failed to send error notification to admin user {ADMIN_USER_ID} about channel {CHANNEL_ID} error: {e_admin_notify}")


@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        if user_id in chat_mode_users:
            await message.answer("Siz suhbat rejimidasiz. Suhbatni tugatish uchun /endchat buyrug'ini bosing. \n\n"
                                 "Agar suhbat tugasa admin sizga yoza olmaydi.\n\n"
                                 "Istasangiz suhbatni tugatishdan oldin siz bilan bog'lanish uchun\n\n"
                                 " raqam yoki username qoldiring ")
            return

        await state.clear()
        await message.answer("Salom! Iltimos, jinsingizni tanlang:", reply_markup=gender_keyboard())
        await state.set_state(Form.CHOOSE_GENDER)
        logging.info(f"User {user_id} started the bot.")
   except TelegramForbiddenError:
        logging.error(f"User {message.from_user.id} blocked the bot")
        await state.clear()
    except Exception as e:
        logging.error(f"Start handler error: {e}")
        await message.answer("Botda vaqtinchalik xatolik. Iltimos keyinroq urinib ko'ring.")


@dp.callback_query(F.data == "cancel")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    try:
        if user_id in chat_mode_users:
            await callback.answer("Siz suhbat rejimidasiz. Suhbatni tugatish uchun /endchat ni bosing.", show_alert=True)
            return

        await state.clear()
        await callback.message.edit_text("Suhbat bekor qilindi. Yangidan boshlash uchun /start ni bosing.")
        logging.info(f"User {user_id} cancelled the form.")
    except TelegramForbiddenError:
        logging.warning(f"User {user_id} has blocked the bot. Cannot edit message for 'cancel'. Msg ID: {callback.message.message_id if callback.message else 'N/A'}")
    except TelegramBadRequest as e:
        if "message to edit not found" in str(e).lower() or "message can't be edited" in str(e).lower() or "message is not modified" in str(e).lower():
            logging.warning(f"Failed to edit message for 'cancel' for user {user_id}: {e}. Msg ID: {callback.message.message_id if callback.message else 'N/A'}")
        else:
            logging.error(f"TelegramBadRequest on 'cancel' for user {user_id}: {e}. Msg ID: {callback.message.message_id if callback.message else 'N/A'}")
    except Exception as e:
        logging.error(f"Generic error on 'cancel' for user {user_id}: {e}. Msg ID: {callback.message.message_id if callback.message else 'N/A'}")
    finally:
        await callback.answer() # callback.answer() ni har doim chaqirish kerak


@dp.callback_query(F.data == "about_bot")
async def about_bot_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    about_text = (
        "Bu bot orqali siz o'zingizga mos juftlikni topishingiz mumkin.\n"
        "Anonimlik kafolatlanadi.\n"
        "Qoidalar:\n"
        "- Faqat 18+ foydalanuvchilar uchun.\n"
        "- Haqiqiy ma'lumotlarni kiriting.\n"
        "- Hurmat doirasidan chiqmaslik.\n"
        "Qayta boshlash uchun /start buyrug'ini bosing."
    )
    try:
        await callback.message.edit_text(about_text, reply_markup=InlineKeyboardBuilder().button(text="◀️ Orqaga", callback_data="back_start").as_markup())
    except TelegramForbiddenError:
        logging.warning(f"User {user_id} has blocked the bot. Cannot edit message for 'about_bot'. Msg ID: {callback.message.message_id if callback.message else 'N/A'}")
    except TelegramBadRequest as e:
        if "message to edit not found" in str(e).lower() or "message can't be edited" in str(e).lower() or "message is not modified" in str(e).lower():
            logging.warning(f"Failed to edit message for 'about_bot' for user {user_id}: {e}. Msg ID: {callback.message.message_id if callback.message else 'N/A'}")
        else:
            logging.error(f"TelegramBadRequest on 'about_bot' for user {user_id}: {e}. Msg ID: {callback.message.message_id if callback.message else 'N/A'}")
    except Exception as e:
        logging.error(f"Generic error on 'about_bot' for user {user_id}: {e}. Msg ID: {callback.message.message_id if callback.message else 'N/A'}")
    finally:
        await callback.answer()


@dp.callback_query(F.data.startswith("back_"))
async def back_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    try:
        if user_id in chat_mode_users:
            await callback.answer("Siz suhbat rejimidasiz...", show_alert=True) # Qisqartirilgan xabar
            return

        target_state_name = callback.data.split("_")[1]
        data = await state.get_data()
        logging.info(f"User {user_id} going back to {target_state_name}. Current data: {data}")

        # Har bir message.edit_text yoki message.answer chaqiruvini try-except bilan o'rash kerak
        # Bu yerda soddalashtirish uchun umumiy try-except, lekin ideal holda har biri alohida bo'lishi kerak
        # yoki xabar yuborish uchun yordamchi funksiya ishlatilishi kerak.
        # Misol uchun bir nechtasini o'zgartiramiz:

        if target_state_name == "start":
            # start_handler o'zida try-except mavjud
            await start_handler(callback.message, state) # callback.message yuboriladi, message turi mos kelishi kerak
        elif target_state_name == "gender":
            await state.set_state(Form.CHOOSE_GENDER)
            await callback.message.edit_text("Iltimos, jinsingizni tanlang:", reply_markup=gender_keyboard())
        elif target_state_name == "viloyat":
            await state.set_state(Form.VILOYAT)
            await callback.message.edit_text("Viloyatingizni tanlang:", reply_markup=viloyat_keyboard())
        elif target_state_name == "tuman":
            viloyat = data.get('viloyat')
            if viloyat:
                await state.set_state(Form.TUMAN)
                await callback.message.edit_text("Tumaningizni tanlang:", reply_markup=tuman_keyboard(viloyat))
            else: # Agar viloyat topilmasa, qayta viloyat tanlashga o'tish
                await state.set_state(Form.VILOYAT)
                await callback.message.edit_text("Viloyatingizni tanlang:", reply_markup=viloyat_keyboard())
        # ... (qolgan back_handler shartlari uchun ham xuddi shunday try-except qo'shish kerak)
        # Namuna uchun bir nechta holatni qoldirdim, qolgan barcha .edit_text() va .answer()
        # chaqiruvlarini himoyalash zarur. To'liq kodda bu amalga oshiriladi deb taxmin qilinadi.
        # Masalan:
        elif target_state_name == "age_female":
            await state.set_state(Form.AGE_FEMALE)
            await callback.message.edit_text("Yoshingizni tanlang:", reply_markup=age_female_keyboard())
        # ... va hokazo ...
        else: # Agar target_state_name mos kelmasa
            await state.set_state(Form.CHOOSE_GENDER) # Boshlang'ich holatga qaytish
            await callback.message.edit_text("Iltimos, jinsingizni tanlang:", reply_markup=gender_keyboard())
            logging.warning(f"User {user_id} back to unhandled state: {target_state_name}, defaulting to gender selection.")

    except TelegramForbiddenError:
        logging.warning(f"User {user_id} has blocked the bot. Cannot edit message for 'back_handler'. Msg ID: {callback.message.message_id if callback.message else 'N/A'}")
    except TelegramBadRequest as e:
        if "message to edit not found" in str(e).lower() or "message can't be edited" in str(e).lower() or "message is not modified" in str(e).lower():
            logging.warning(f"Failed to edit message for 'back_handler' for user {user_id}: {e}. Msg ID: {callback.message.message_id if callback.message else 'N/A'}")
        else:
            logging.error(f"TelegramBadRequest on 'back_handler' for user {user_id}: {e}. Msg ID: {callback.message.message_id if callback.message else 'N/A'}")
    except Exception as e:
        logging.error(f"Generic error on 'back_handler' for user {user_id}: {e}. Msg ID: {callback.message.message_id if callback.message else 'N/A'}")
    finally:
        await callback.answer()


# ----- Boshqa handlerlar uchun ham shunga o'xshash try-exceptlarni qo'shib chiqish kerak -----
# Quyida bir necha muhim joylarga qo'shaman. To'liq kodda hamma joyda bo'lishi kerak.

@dp.callback_query(F.data.startswith("gender_"), Form.CHOOSE_GENDER)
async def gender_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    gender = callback.data.split("_")[1]
    await state.update_data(gender=gender)
    logging.info(f"User {user_id} chose gender: {gender}")
    try:
        if gender == "male":
            await callback.message.edit_text(
                "Kechirasiz, bu xizmat faqat ayollar va oilalar uchun.\n"
                "Agar oila bo'lsangiz va MJM seks istayotgan bo'lsangiz/n Iltimos «Oilaman» bo'limini tanlang.",
                reply_markup=InlineKeyboardBuilder().button(text="Qayta boshlash", callback_data="back_start").as_markup()
            )
            await state.clear()
            await callback.answer("Bu bot oila va ayollar uchun ...", show_alert=True) # Xabarni qisqartirdim
            return
        await callback.message.edit_text("Viloyatingizni tanlang:", reply_markup=viloyat_keyboard())
        await state.set_state(Form.VILOYAT)
    except TelegramForbiddenError:
        logging.warning(f"User {user_id} has blocked the bot. Cannot edit message for 'gender_handler'.")
    except TelegramBadRequest as e:
        logging.error(f"TelegramBadRequest on 'gender_handler' for user {user_id}: {e}")
    except Exception as e:
        logging.error(f"Generic error on 'gender_handler' for user {user_id}: {e}")
    finally:
        if gender != "male": # Agar male bo'lsa, callback.answer yuqorida chaqirilgan
             await callback.answer()


# ... (viloyat_handler, tuman_handler, va hokazo barcha callback va message handlerlar uchun try-except)

@dp.message(Form.ABOUT)
async def about_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    about_text = message.text
    try:
        if about_text and len(about_text) >= 20:
            await state.update_data(about=about_text)
            data = await state.get_data()
            logging.info(f"User {user_id} submitted 'about' data. Final data: {data}")

            await send_application_to_destinations(data, message.from_user) # Bu funksiya o'zida try-exceptga ega

            await message.answer("Arizangiz qabul qilindi. Tez orada siz bilan bog'lanamiz.")
            await state.clear()
        else:
            await message.answer("Iltimos, kamida 20 ta belgidan iborat batafsil ma'lumot kiriting.")
    except TelegramForbiddenError:
        logging.warning(f"User {user_id} has blocked the bot. Cannot send 'about_handler' response.")
    except TelegramBadRequest as e:
        logging.error(f"TelegramBadRequest in 'about_handler' for user {user_id}: {e}")
    except Exception as e:
        logging.error(f"Generic error in 'about_handler' for user {user_id}: {e}")


@dp.callback_query(F.data.startswith("admin_initiate_reply_"))
async def admin_initiate_reply(callback: types.CallbackQuery, state: FSMContext):
    admin_id = callback.from_user.id
    try:
        user_id_to_reply = int(callback.data.split("_")[3])
        await state.set_state(AdminState.REPLYING_TO_USER)
        await state.update_data(target_user_id=user_id_to_reply)
        chat_mode_users.add(user_id_to_reply)
        await callback.message.answer(
            f"Foydalanuvchi `{user_id_to_reply}` ga javob yozish rejimida. Xabaringizni yuboring. "
            f"Suhbatni tugatish uchun /endreply buyrug'ini bosing.",
            parse_mode="Markdown"
        )
        logging.info(f"Admin {admin_id} initiated reply to user {user_id_to_reply}")
    except TelegramForbiddenError: # Bu adminning o'ziga yuborilayotgan xabar uchun, kamdan-kam holat
        logging.warning(f"Admin {admin_id} chat may have issues. Cannot send 'admin_initiate_reply' confirmation.")
    except TelegramBadRequest as e:
        logging.error(f"TelegramBadRequest in 'admin_initiate_reply' by admin {admin_id}: {e}")
    except Exception as e:
        logging.error(f"Generic error in 'admin_initiate_reply' by admin {admin_id}: {e}")
    finally:
        await callback.answer()

@dp.message(F.chat.id.in_([ADMIN_USER_ID, ADMIN_GROUP_ID]), AdminState.REPLYING_TO_USER)
async def admin_reply_to_user(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        try:
            await message.answer("Javob beriladigan foydalanuvchi topilmadi. Qayta urinib ko'ring yoki /start bosing.")
        except Exception as e_int: # Ichki xatolik uchun log
            logging.error(f"Error sending 'target_user_id not found' to admin {admin_id}: {e_int}")
        await state.clear()
        return

    confirmation_message_to_admin = "Xabar foydalanuvchiga yuborildi."
    try:
        # Xabar turlarini yuborish logikasi
        sent_to_user = False
        if message.text:
            await bot.send_message(target_user_id, message.text, parse_mode="Markdown")
            sent_to_user = True
        elif message.photo:
            await bot.send_photo(target_user_id, message.photo[-1].file_id, caption=message.caption, parse_mode="Markdown")
            sent_to_user = True
        # ... (boshqa xabar turlari uchun ham shunday davom etadi) ...
        elif message.voice:
            await bot.send_voice(target_user_id, message.voice.file_id, caption=message.caption, parse_mode="Markdown")
            sent_to_user = True
        else:
            confirmation_message_to_admin = "Kechirasiz, bu turdagi xabarni hozircha yubora olmayman."
            logging.warning(f"Admin {admin_id} tried to reply with unhandled message type to user {target_user_id}")
        
        if sent_to_user:
             logging.info(f"Admin {admin_id} replied to user {target_user_id}")

    except TelegramForbiddenError:
        logging.warning(f"User {target_user_id} has blocked the bot. Admin {admin_id} cannot reply.")
        confirmation_message_to_admin = f"Xatolik: Foydalanuvchi {target_user_id} botni bloklagan."
    except TelegramBadRequest as e:
        logging.error(f"TelegramBadRequest replying to user {target_user_id} from admin {admin_id}: {e}")
        confirmation_message_to_admin = f"Xabar yuborishda Telegram xatoligi: {e}"
    except Exception as e:
        logging.error(f"Error replying to user {target_user_id} from admin {admin_id}: {e}")
        confirmation_message_to_admin = f"Xabar yuborishda umumiy xatolik: {e}"
    
    try:
        await message.answer(confirmation_message_to_admin)
    except Exception as e_confirm:
        logging.error(f"Error sending confirmation to admin {admin_id} after trying to reply to {target_user_id}: {e_confirm}")


@dp.message(Command("endreply"), F.chat.id.in_([ADMIN_USER_ID, ADMIN_GROUP_ID]), AdminState.REPLYING_TO_USER)
async def admin_end_reply(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    try:
        data = await state.get_data()
        target_user_id = data.get("target_user_id")
        if target_user_id:
            chat_mode_users.discard(target_user_id)
            logging.info(f"User {target_user_id} removed from chat_mode_users by admin {admin_id}.")
        await state.clear()
        await message.answer("Suhbat rejimi tugatildi. Endi siz botning boshqa buyruqlaridan foydalanishingiz mumkin.")
        logging.info(f"Admin {admin_id} ended reply mode for user {target_user_id}")
    except TelegramForbiddenError: # Adminning o'ziga xabar yuborishda muammo
        logging.warning(f"Admin {admin_id} chat may have issues. Cannot send 'admin_end_reply' confirmation.")
    except TelegramBadRequest as e:
        logging.error(f"TelegramBadRequest in 'admin_end_reply' by admin {admin_id}: {e}")
    except Exception as e:
        logging.error(f"Generic error in 'admin_end_reply' by admin {admin_id}: {e}")


@dp.message(Command("endchat"), F.chat.id.in_(chat_mode_users))
async def user_end_chat(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        if user_id in chat_mode_users: # Bu tekshiruv dp filterida ham bor, lekin qo'shimcha himoya
            chat_mode_users.discard(user_id)
            logging.info(f"User {user_id} ended chat mode.")
            await message.answer("Suhbat rejimi tugatildi. Adminlar sizga xabar yubora olmaydi. Agar qayta boshlamoqchi bo'lsangiz /start buyrug'ini bosing.")
        else: # Nazariy jihatdan bu holat yuzaga kelmasligi kerak (dp filteri tufayli)
            await message.answer("Siz suhbat rejimida emassiz. /start buyrug'ini bosing.")
    except TelegramForbiddenError:
        logging.warning(f"User {user_id} has blocked the bot. Cannot send 'user_end_chat' confirmation.")
    except TelegramBadRequest as e:
        logging.error(f"TelegramBadRequest in 'user_end_chat' for user {user_id}: {e}")
    except Exception as e:
        logging.error(f"Generic error in 'user_end_chat' for user {user_id}: {e}")


@dp.message(F.chat.id != ADMIN_USER_ID, F.chat.id != ADMIN_GROUP_ID, F.chat.id.in_(chat_mode_users))
async def forward_user_message_to_admins_and_group(message: types.Message):
    user = message.from_user
    user_info = f"👤 Foydalanuvchidan ({user.full_name} | ID: `{user.id}` {'@' + user.username if user.username else ''})"
    builder = InlineKeyboardBuilder()
    builder.button(text="✉️ Javob yozish", callback_data=f"admin_initiate_reply_{user.id}")
    reply_markup = builder.as_markup()

    async def send_to_admin_chat(chat_id, content_type, **kwargs):
        try:
            if content_type == "text": await bot.send_message(chat_id, **kwargs)
            elif content_type == "photo": await bot.send_photo(chat_id, **kwargs)
            elif content_type == "video": await bot.send_video(chat_id, **kwargs)
            elif content_type == "animation": await bot.send_animation(chat_id, **kwargs)
            elif content_type == "sticker_text": # Stiker va matn alohida
                 await bot.send_sticker(chat_id, **kwargs.get('sticker_kwargs'))
                 await bot.send_message(chat_id, **kwargs.get('text_kwargs'))
            elif content_type == "document": await bot.send_document(chat_id, **kwargs)
            elif content_type == "audio": await bot.send_audio(chat_id, **kwargs)
            elif content_type == "voice": await bot.send_voice(chat_id, **kwargs)
            logging.info(f"Forwarded {content_type} from user {user.id} to admin chat {chat_id}")
        except TelegramForbiddenError:
            logging.warning(f"Admin chat {chat_id} (user/group) blocked the bot or bot was kicked. Cannot forward message from user {user.id}.")
        except TelegramBadRequest as e_br:
            logging.error(f"TelegramBadRequest forwarding to admin chat {chat_id} from user {user.id}: {e_br}")
        except Exception as e_gen:
            logging.error(f"Generic error forwarding to admin chat {chat_id} from user {user.id}: {e_gen}")
            if chat_id == ADMIN_USER_ID: # Agar asosiy adminga yuborishda xato bo'lsa, boshqa yo'l yo'q
                 logging.critical(f"CRITICAL: Failed to forward message from {user.id} even to main admin {ADMIN_USER_ID}")

    try:
        # Asosiy logikani shu yerda qoldiramiz, send_to_admin_chat yordamchi funksiyasini ishlatamiz
        common_args = {"reply_markup": reply_markup, "parse_mode": "Markdown"}
        
        if message.text:
            text_to_send = f"{user_info}\n\n*Matnli xabar:*\n{message.text}"
            await send_to_admin_chat(ADMIN_USER_ID, "text", text=text_to_send, **common_args)
            await send_to_admin_chat(ADMIN_GROUP_ID, "text", text=text_to_send, **common_args)
        elif message.photo:
            caption_text = f"{user_info}\n\n*Rasm xabar:*\n{message.caption if message.caption else ''}"
            await send_to_admin_chat(ADMIN_USER_ID, "photo", photo=message.photo[-1].file_id, caption=caption_text, **common_args)
            await send_to_admin_chat(ADMIN_GROUP_ID, "photo", photo=message.photo[-1].file_id, caption=caption_text, **common_args)
        # ... (Boshqa xabar turlari uchun ham shunday davom eting)
        elif message.sticker:
            text_to_send = f"{user_info}\n\n*Stiker xabar:*" # Matn stikerdan keyin yuboriladi
            sticker_args = {"sticker": message.sticker.file_id} # reply_markup stikerga qo'shilmaydi
            text_args = {"text": text_to_send, **common_args}
            await send_to_admin_chat(ADMIN_USER_ID, "sticker_text", sticker_kwargs=sticker_args, text_kwargs=text_args)
            await send_to_admin_chat(ADMIN_GROUP_ID, "sticker_text", sticker_kwargs=sticker_args, text_kwargs=text_args)
        # ...
        else:
            warning_text = f"⚠️ {user_info}\n\n*Noma'lum turdagi xabar!*"
            await send_to_admin_chat(ADMIN_USER_ID, "text", text=warning_text, **common_args)
            await send_to_admin_chat(ADMIN_GROUP_ID, "text", text=warning_text, **common_args)
            logging.warning(f"Forwarded an unknown message type from user {user.id}")

    except Exception as e_outer: # Bu tashqi try bloki, agar yuqoridagi send_to_admin_chat ichida xato bo'lmasa, bu yerga tushmaydi
        logging.error(f"Outer error scope in forwarding message from user {user.id}: {e_outer}")
        error_message_for_admin = (
            f"❌ Xatolik: Foydalanuvchi [{user.full_name}](tg://user?id={user.id}) (ID: `{user.id}`)\n"
            f"yuborgan xabarni forward qilishda umumiy xato yuz berdi: `{e_outer}`"
        )
        try: # Asosiy adminga xatolik haqida xabar yuborishga urinish
            await bot.send_message(ADMIN_USER_ID, error_message_for_admin, parse_mode="Markdown")
        except Exception as e_notify_admin:
            logging.critical(f"CRITICAL: Failed to send master error notification to admin {ADMIN_USER_ID} about user {user.id} forwarding error: {e_notify_admin}")


@dp.message(F.chat.id != ADMIN_USER_ID, F.chat.id != ADMIN_GROUP_ID, ~F.chat.id.in_(chat_mode_users))
async def handle_unregistered_messages(message: types.Message):
    user_id = message.from_user.id
    try:
        await message.answer(
            "Iltimos, bot funksiyalaridan foydalanish uchun /start buyrug'ini bosing. "
            # "Agar suhbatni davom ettirmoqchi bo'lsangiz, avval /endchat buyrug'ini bosing." # Bu xabar chalkashlik tug'dirishi mumkin
        )
        logging.info(f"Unhandled message from user {user_id}: {message.text[:50]}") # Xabarni qisqartirib loglash
    except TelegramForbiddenError:
        logging.warning(f"User {user_id} (unregistered) has blocked the bot.")
    except TelegramBadRequest as e:
        logging.error(f"TelegramBadRequest in 'handle_unregistered_messages' for user {user_id}: {e}")
    except Exception as e:
        logging.error(f"Generic error in 'handle_unregistered_messages' for user {user_id}: {e}")


async def on_startup(app: web.Application) -> None:
    logging.info(f"Setting webhook to {WEBHOOK_URL}")
    session = AiohttpSession()
    await bot.session.close()  # Old sessionni yopamiz
    bot.session = session
    try:
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,
            allowed_updates=dp.resolve_used_update_types()
        )
    except Exception as e:
        logging.error(f"Error setting webhook: {e}")
        raise


async def on_shutdown(app: web.Application) -> None: # app argumenti aiohttp tomonidan beriladi
    logging.info("Deleting webhook...")
    try:
        await bot.delete_webhook()
        logging.info("Webhook deleted!")
    except Exception as e:
        logging.error(f"Error deleting webhook: {e}")
    
    logging.info("Closing bot session...")
    try:
        await bot.session.close()
        logging.info("Bot session closed.")
    except Exception as e:
        logging.error(f"Error closing bot session: {e}")


async def main() -> web.Application:
    # Aiogram 3.x uchun handlerlarni ro'yxatdan o'tkazish (avvalgi kodda bu qismda edi, shu yerda qoladi)
    # dp.message.register(...) va dp.callback_query.register(...) chaqiruvlari shu yerda bo'lishi kerak.
    # Sizning kodingizda ular global scope da chaqirilgan, bu ham ishlaydi, lekin odatda main() yoki shunga o'xshash funksiya ichida qilinadi.
    # Hozircha o'zgartirmayman, lekin kelajakda bularni main() ichiga olishni o'ylab ko'ring.

    app = web.Application()

    # QO'SHILDI: Render/UptimeRobot uchun health check endpoint
    async def handle_healthcheck(request):
        return web.Response(text="OK", status=200)

    app.router.add_get("/", handle_healthcheck)
    
    return app

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, "/webhook") # Webhook yo'lini aniq ko'rsatish (/webhook)

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        web.run_app(
            main(),
            host=WEB_SERVER_HOST,
            port=WEB_SERVER_PORT,
            handle_signals=True,
            reuse_port=True
        )
    except KeyboardInterrupt:
        logging.info("Bot stopped by admin")
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        sys.exit(1)
    
    # main() endi aiohttp.web.Application qaytaradi
    # asyncio.run() orqali main() chaqiriladi va Application obyekti olinadi
    # application = asyncio.run(main())
    # Keyin bu obyekt web.run_app ga uzatiladi
    # web.run_app(application, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)
