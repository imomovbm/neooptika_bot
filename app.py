import re
from dotenv import load_dotenv
from os import getenv, path

BASE_DIR = path.dirname(path.abspath(__file__))
load_dotenv(path.join(BASE_DIR, ".env"))
BARCODE_DIR = path.join(BASE_DIR, "barcodes")

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from models import User, SessionLocal, Transaction
from barcode_making import generate_barcode_image
from datetime import datetime


from sqlalchemy.exc import IntegrityError

# Bot token can be obtained via https://t.me/BotFather
TOKEN = getenv("BOT_TOKEN")
WEBHOOK_PATH = getenv("WEBHOOK_PATH")
WEBHOOK_URL = getenv("WEBHOOK_URL")
# All handlers should be attached to the Router (or Dispatcher)

dp = Dispatcher()

def contact_keyboard():
    button = KeyboardButton(text="Telefon raqamni ulashish", request_contact=True)
    return ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True)

def balance_keyboard():
    button = KeyboardButton(text="Balans")
    return ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True)

def admin_keyboard():
    button = KeyboardButton(text="Admin")
    return ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True)

def admin_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Admin"),
                KeyboardButton(text="Balans")
            ]
        ],
        resize_keyboard=True
    )

def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    with SessionLocal() as session:
        # same query shape as your scratch script — filter_by telegram_id, not id
        existing_user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if existing_user:
            path_photo = path.join(BARCODE_DIR, f"{existing_user.barcode}.png")
            # welcome them back — maybe remind them of their barcode
            if not path.exists(path_photo):
                img = generate_barcode_image(existing_user.barcode)
                with open(path_photo, "wb") as f:
                    f.write(img.getvalue())               
            photo = FSInputFile(path_photo)
            
            await message.answer_photo(
                photo,
                caption=(
                    f"Har bir xaridingizdan 1% keshbek olish uchun yuqoridagi kodni taqdim eting.\n"
                    f"💰 {datetime.now().strftime('%d.%m.%Y %H:%M')} holatiga ko'ra balansingiz: "
                    f"{existing_user.cashback_balance} so'm\n"
                    f"💳 Karta raqami: {existing_user.barcode}"
                ),
                reply_markup=balance_keyboard() if not existing_user.is_admin else admin_menu_keyboard()
            )
        else:
            await message.answer(
                "Xush kelibsiz! Ro'yxatdan o'tish uchun telefon raqamingizni ulashing",
                reply_markup=contact_keyboard(),
            )

@dp.message(F.contact)
async def contact_handler(message: Message) -> None:
    # reject contact cards that aren't the sender's own — no DB needed for this check
    if message.contact.user_id != message.from_user.id:
        await message.answer("Iltimos o'zingizni telefon raqamni ulashing!")
        return

    with SessionLocal() as session:
        new_user = User(
            telegram_id=message.from_user.id,   # message.from_user.id
            phone_number=message.contact.phone_number,  # message.contact.phone_number
            barcode=str(message.from_user.id),       # your generation logic — str(message.from_user.id) is a fine start
        )

        try:
            session.add(new_user)
            session.commit()
        except IntegrityError:
            session.rollback()
            await message.answer("Siz allaqachon ro'yxatdan o'tgansiz")
            return
        
        img = generate_barcode_image(new_user.barcode)
        file_path = path.join(BARCODE_DIR, f"{new_user.barcode}.png")
        with open(file_path, "wb") as f:
            f.write(img.getvalue())
        photo = FSInputFile(file_path)
        # keep this reply inside the `with` block — reading new_user.barcode
        # after the session closes can throw an error

        await message.answer_photo(
            photo,
            caption=(
                f"Ro'yxatdan o'tdingiz! Har bir xaridingizdan 1% keshbek olish uchun yuqoridagi kodni taqdim eting.\n"
                f"💰 {datetime.now().strftime('%d.%m.%Y %H:%M')} holatiga ko'ra balansingiz: "
                f"{new_user.cashback_balance}\n so'm"
                f"💳 Karta raqami: {new_user.barcode}"
            ),
            reply_markup=balance_keyboard(),
        )

@dp.message(Command("balans"))
@dp.message(F.text == "Balans")
async def balance_handler(message: Message):
    with SessionLocal() as session:
        user = session.query(User).filter_by(
            telegram_id=message.from_user.id
        ).first()

        if not user:
            await message.answer(
                "Avval /start buyrug'ini yuborib ro'yxatdan o'ting.",
                reply_markup=contact_keyboard()
            )
            return

        path_photo = path.join(BARCODE_DIR, f"{user.barcode}.png")

        if not path.exists(path_photo):
            img = generate_barcode_image(user.barcode)
            with open(path_photo, "wb") as f:
                f.write(img.getvalue())

        photo = FSInputFile(path_photo)

        await message.answer_photo(
            photo,
            caption=(
                "Har bir xaridingizdan 1% keshbek olish uchun yuqoridagi kodni taqdim eting.\n\n"
                f"💰 {datetime.now().strftime('%d.%m.%Y %H:%M')} holatiga ko'ra balansingiz: "
                f"{user.cashback_balance} so'm\n"
                f"💳 Karta raqami: {user.barcode}"
            ),
            reply_markup=balance_keyboard() if not user.is_admin else admin_menu_keyboard()
        )

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

@dp.message(Command("cancel"))
@dp.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state is None:
        await message.answer("Bekor qilinadigan amal yo'q.")
        return

    await state.clear()

    with SessionLocal() as session:
        user = session.query(User).filter_by(
            telegram_id=message.from_user.id
        ).first()

    await message.answer(
        "✅ Amal bekor qilindi.",
        reply_markup=admin_menu_keyboard() if user and user.is_admin else balance_keyboard()
    )

class PurchaseStates(StatesGroup):
    waiting_for_customer = State()
    waiting_for_amount = State()

@dp.message(F.text == "Admin")
async def admin_handler(message: Message, state: FSMContext):
    with SessionLocal() as session:
        admin = session.query(User).filter_by(
            telegram_id=message.from_user.id, is_admin = True
        ).first()

        if not admin:
            await message.answer(
                "Siz admin emassiz!",
                reply_markup=balance_keyboard()
            )
            return
        await state.set_state(PurchaseStates.waiting_for_customer)

        await message.answer(
                "Xaridor telefon raqamini kiriting:",
            reply_markup=cancel_keyboard()
        )

@dp.message(PurchaseStates.waiting_for_customer)
async def get_customer(message: Message, state: FSMContext):

    phone = re.sub(r"\D", "", message.text)

    if phone.startswith("998"):
        phone = "+" + phone
    else:
        phone = "+998" + phone

    with SessionLocal() as session:
        user = session.query(User).filter_by(
            phone_number=phone
        ).first()

    if not user:
        await message.answer(
            "Bunday xaridor mavjud emas",
        )
        return
    
    await state.update_data(user=user.id)

    # Keyingi holat
    await state.set_state(PurchaseStates.waiting_for_amount)

    await message.answer(
        "Summani kiriting:",
        reply_markup=cancel_keyboard()
    )

@dp.message(PurchaseStates.waiting_for_amount)
async def get_amount(message: Message, state: FSMContext):

    try:
        amount = float(message.text.strip())
        cashback = round(amount * 0.01,2)
        
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Iltimos to'g'ri qiymat kiriting:")
        return
    
    data = await state.get_data()
    user_id = data["user"] # user=user.id

    with SessionLocal() as session:
        admin = session.query(User).filter_by(
            telegram_id=message.from_user.id,
            is_admin=True
        ).first()   
        if admin is None:
            await message.answer("Admin topilmadi.")
            await state.clear()
            return

        new_transaction = Transaction(
            user_id=user_id,
            purchase_amount=amount,
            cashback_earned=cashback,
            admin_id=admin.id,
        )
        try:
            session.add(new_transaction)

            customer = session.query(User).filter_by(id=user_id).first()
            if customer is None:
                await message.answer("Foydalanuvchi topilmadi.")
                return
            
            customer.cashback_balance += new_transaction.cashback_earned
            
            customer_phone = customer.phone_number
            customer_balance = customer.cashback_balance
            
            session.commit()
        except IntegrityError:
            session.rollback()
            await message.answer("Xatolik!")
            return

    await message.answer(
        f"✅ Xarid qo'shildi\n\n"
        f"👤 {customer_phone}\n"
        f"💵 Xarid summasi: {amount:,.0f} so'm\n"
        f"💰 Shundan keshbek: {cashback:,.2f} so'm"
        f"💵💵💵 Umumiy keshbek: {customer_balance:,.2f} so'm",
        reply_markup=admin_menu_keyboard()
    )

    # FSM ni tugatish
    await state.clear()

@dp.message()
async def unknown(message: Message):
    await message.answer(
        "Noma'lum buyruq. /start ni bosing."
    )

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)
