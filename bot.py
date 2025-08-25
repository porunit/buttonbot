import os
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import Forbidden
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, Defaults

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID_RAW = os.getenv("CHANNEL_ID", "@your_channel")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}

CHANNEL_ID = CHANNEL_ID_RAW if CHANNEL_ID_RAW.startswith("@") else int(CHANNEL_ID_RAW)

CHANNEL_POST_TEXT = (
    "<b>Главная ошибка при покупке машины — не знание цен в Европе!</b>\n\n"
    "Это не шутка: люди <b>переплачивают миллионы</b> за авто, которое даже не хотели, "
    "потому что в наличии ничего нет. Или ещё хуже — покупают китайца и просто терпят "
    "<b>постоянные поломки</b> и косые взгляды.\n\n"
    "Зачем всё это, когда можно привезти себе немца из Европы на <b>2–3 млн ₽ дешевле</b>.\n\n"
    "Надёжную машину, которая будет <b>только расти в цене</b> и не превратится в тыкву.\n\n"
    "Ещё и с нормальной растаможкой, без проблем с налогами и связей с сомнительными перекупами. "
    "Никаких скрытых аварий и скрученных пробегов.\n\n"
    "<b>Короче, хватит это терпеть!</b> Забирай по кнопке ниже бота, где уже отобраны лучшие предложения Европы!\n\n"
    "<blockquote>"
    "<b>Кто мы?</b><br><br>"
    "ООО «К14 АВТО»<br>"
    "ИНН <a href=\"https://egrul.nalog.ru/\">7811576729</a><br>"
    "ОГРН 1147847116340<br>"
    "<i>*Предложение не является публичной офертой</i>"
    "</blockquote>"
)

ALERT_TEXT = (
    "Дорогой друг, чтобы получить файл — подпишись на канал "
    "и нажми на кнопку ещё раз."
)
DM_TEXT = (
    "*Спасибо большое за вашу подписку*\\! ❗\n\n"
    "Теперь вы будете первыми узнавать обо всех интересных предложениях на рынке автомобилей\n\n"
    "> Просмотрите огромный выбор машин прямо сейчас и найдите идеальный автомобиль своей мечты\\!\n\n"
    "Когда что\\-то вам приглянется — заполняйте анкету и мы свяжемся с вами\n\n"
    "*Переходите в каталог автомобилей — кнопка расположена снизу* ❗"
)

CB_GET = "get_materials"
START_PARAM = "materials"

# ---- конфиг (можно в .env вынести) ----
MINIAPP_URL = "https://k14-frontend.vercel.app/#/?drawer=filters"
CAR_BOT_URL = "https://t.me/K14_auto_bot?start=900"

def build_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Каталог (мини-апп)", web_app=WebAppInfo(url=MINIAPP_URL))],
        [InlineKeyboardButton("🤝 Подобрать автомобиль", url=CAR_BOT_URL)],
    ])

async def is_subscribed(bot, user_id: int) -> bool:
    try:
        cm = await bot.get_chat_member(CHANNEL_ID, user_id)
        print(cm.status)
        return cm.status == 'creator' or cm.status == 'member' or cm.status == 'administrator'
    except Exception:
        return False

BOT_USERNAME = None
async def post_init(app: Application) -> None:
    global BOT_USERNAME
    me = await app.bot.get_me()
    BOT_USERNAME = me.username

async def cmd_publish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if ADMIN_IDS and (update.effective_user is None or update.effective_user.id not in ADMIN_IDS):
        await update.effective_message.reply_text("Недостаточно прав.")
        return

    kb = InlineKeyboardMarkup.from_button(
        InlineKeyboardButton("📥 Получить материалы", callback_data=CB_GET)
    )
    await context.bot.send_message(
        CHANNEL_ID,
        CHANNEL_POST_TEXT,
        reply_markup=kb,                 # если нужна клавиатура
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )

    if update.effective_chat:
        await update.effective_message.reply_text("Пост отправлен в канал ✅")

START_PARAM = "materials"

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user

    if query.data != CB_GET:
        await query.answer()
        return

    # 1) проверяем подписку
    if not await is_subscribed(context.bot, user.id):
        await query.answer(ALERT_TEXT, show_alert=True)
        return

    # 2) HTTPS deep-link
    deep_link = f"https://t.me/{BOT_USERNAME}?start={START_PARAM}"

    # 3) пытаемся сразу прислать материалы в ЛС (если бот уже стартован)
    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=DM_TEXT,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=build_main_kb(),     # ← КНОПКИ
        )
    except Forbidden:
        pass  # если бот не стартован — просто откроем чат по ссылке

    # 4) мгновенно переводим пользователя в чат с ботом
    await query.answer(url=deep_link, cache_time=0)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if args and args[0] == START_PARAM:
        await update.effective_message.reply_text(DM_TEXT, disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=build_main_kb())
    else:
        await update.effective_message.reply_text(
            "Привет! Нажмите кнопку под постом в канале, чтобы получить материалы."
        )

def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("Set BOT_TOKEN and CHANNEL_ID in .env")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("publish", cmd_publish))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
