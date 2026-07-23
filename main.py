import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем токен из переменной окружения (или можно вставить строкой)
TOKEN = os.getenv("BOT_TOKEN", "8807605923:AAGkGlj4h0-AwE-jU5KRr6Cp_WNNpNJ6hw0")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ID администратора
ADMIN_ID = 7738822030

# Временная база данных в памяти (для демонстрации на ботхосте)
# user_servers = { user_id: [ { "ram": 5, "region": "Нидерланды", "price": 589, "ip": "185.243.x.x", "ftp": "ftp://..." } ] }
user_servers = {}


# Состояния FSM для покупки
class PurchaseState(StatesGroup):
    selecting_ram = State()
    selecting_region = State()
    confirming = State()
    selecting_payment = State()


# Состояния для админ-панели (выдача сервера)
class AdminState(StatesGroup):
    waiting_for_ram = State()
    waiting_for_region = State()
    waiting_for_term = State()
    waiting_for_user_id = State()


# Цены на RAM
RAM_PRICES = {
    "1 GB": 120,
    "2 GB": 200,
    "3 GB": 250,
    "4 GB": 300,
    "5 GB": 479,
    "10 GB": 890  # примерная для 10Гб, если не указана
}

# Цены на регионы
REGION_PRICES = {
    "Нидерланды": 110,
    "Москва": 249,
    "Латвия": 139,
    "Германия": 169,
    "США(большой пинг)": 679,
    "Африка": 99
}


# --- ГЛАВНОЕ МЕНЮ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🛒 Покупка VDS сервера", callback_data="buy_vds"),
        types.InlineKeyboardButton(text="💻 Мои сервера", callback_data="my_servers")
    )
    
    # Если пользователь администратор, добавляем кнопку админ-панели
    if message.from_user.id == ADMIN_ID:
        builder.row(types.InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel"))

    await message.answer(
        "👋 **Добро пожаловать в сервис аренды VDS серверов!**\n\nВыберите нужный раздел в меню ниже:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )


# --- РАЗДЕЛ: МОИ СЕРВЕРА ---
@dp.callback_query(F.data == "my_servers")
async def show_my_servers(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    servers = user_servers.get(user_id, [])

    builder = InlineKeyboardBuilder()

    if not servers:
        text = (
            "❌ У вас не куплен ни один сервер.\n\n"
            "Приобрести сервер можно по кнопке «Покупка VDS сервера» ниже:"
        )
        builder.row(types.InlineKeyboardButton(text="🛒 Покупка VDS сервера", callback_data="buy_vds"))
    else:
        text = "💻 **Ваши активные VDS сервера:**"
        for idx, srv in enumerate(servers):
            # Кнопка для каждого купленного сервера
            builder.row(
                types.InlineKeyboardButton(
                    text=f"{srv['ram']}GB rg: {srv['region']}",
                    callback_data=f"server_info_{user_id}_{idx}"
                )
            )

    builder.row(types.InlineKeyboardButton(text="◀️ Назад в меню", callback_data="main_menu"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


# Просмотр конкретного купленного сервера
@dp.callback_query(F.data.startswith("server_info_"))
async def server_details(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    user_id = int(data_parts[2])
    idx = int(data_parts[3])

    servers = user_servers.get(user_id, [])
    if idx < len(servers):
        srv = servers[idx]
        text = (
            f"🖥 **Информация о сервере:**\n\n"
            f"• Память: `{srv['ram']} GB`\n"
            f"• Регион: `{srv['region']}`\n"
            f"• Статус: `Активен`\n\n"
            f"🔑 **Доступные данные:**\n"
            f"• VDS IP: `{srv.get('ip', '185.221.160.15')}`\n"
            f"• VDS FTP: `ftp://user:{user_id}@185.221.160.15:21`\n"
            f"• SSH Порт: `22`\n"
            f"• Пароль root: `SecurePass99#{user_id}`"
        )
    else:
        text = "❌ Сервер не найден."

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="◀️ Назад к серверам", callback_data="my_servers"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


# --- ПРОЦЕСС ПОКУПКИ VDS ---
@dp.callback_query(F.data == "buy_vds")
async def buy_vds_step1(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(PurchaseState.selecting_ram)
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="1 GB — 120₽", callback_data="ram_1"))
    builder.row(types.InlineKeyboardButton(text="2 GB — 200₽", callback_data="ram_2"))
    builder.row(types.InlineKeyboardButton(text="3 GB — 250₽", callback_data="ram_3"))
    builder.row(types.InlineKeyboardButton(text="4 GB — 300₽", callback_data="ram_4"))
    builder.row(types.InlineKeyboardButton(text="5 GB — 479₽", callback_data="ram_5"))
    builder.row(types.InlineKeyboardButton(text="10 GB — 890₽", callback_data="ram_10"))
    builder.row(types.InlineKeyboardButton(text="◀️ Назад в меню", callback_data="main_menu"))

    await callback.message.edit_text(
        "🛒 **Покупка VDS**\n\nВыберите гигабайты сервера:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(PurchaseState.selecting_ram, F.data.startswith("ram_"))
async def process_ram_selection(callback: types.CallbackQuery, state: FSMContext):
    ram_val = callback.data.split("_")[1]
    ram_str = f"{ram_val} GB"
    price = RAM_PRICES.get(ram_str, 120)

    await state.update_data(ram=ram_val, ram_price=price)
    await state.set_state(PurchaseState.selecting_region)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🇳🇱 Нидерланды (Рекомендация для России)", callback_data="reg_Нидерланды"))
    builder.row(types.InlineKeyboardButton(text="🇷🇺 Москва", callback_data="reg_Москва"))
    builder.row(types.InlineKeyboardButton(text="🇱🇻 Латвия", callback_data="reg_Латвия"))
    builder.row(types.InlineKeyboardButton(text="🇩🇪 Германия", callback_data="reg_Германия"))
    builder.row(types.InlineKeyboardButton(text="🇺🇸 США (большой пинг)", callback_data="reg_США(большой пинг)"))
    builder.row(types.InlineKeyboardButton(text="🌍 Африка", callback_data="reg_Африка"))
    builder.row(types.InlineKeyboardButton(text="◀️ Назад", callback_data="buy_vds"))

    await callback.message.edit_text(
        "🌍 **Выбор региона VDS**\n\nРекомендация для России: Нидерланды 🇳🇱\nВыберите регион:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(PurchaseState.selecting_region, F.data.startswith("reg_"))
async def process_region_selection(callback: types.CallbackQuery, state: FSMContext):
    region_name = callback.data.split("_", 1)[1]
    reg_price = REGION_PRICES.get(region_name, 110)

    await state.update_data(region=region_name, reg_price=reg_price)
    await state.set_state(PurchaseState.confirming)

    data = await state.get_data()
    total_price = data['ram_price'] + data['reg_price']
    await state.update_data(total_price=total_price)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Подтвердить данные", callback_data="confirm_order"))
    builder.row(types.InlineKeyboardButton(text="◀️ Назад к регионам", callback_data="buy_vds"))

    text = (
        f"📋 **Уточнение заказа:**\n\n"
        f"• Выбрано Гб: `{data['ram']} GB` — `{data['ram_price']}₽`\n"
        f"• Регион: `{data['region']}` — `{data['reg_price']}₽`\n\n"
        f"💰 **Итоговая цена:** `{total_price}₽`"
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(PurchaseState.confirming, F.data == "confirm_order")
async def process_confirmation(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(PurchaseState.selecting_payment)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📱 СБП", callback_data="pay_sbp"))
    builder.row(types.InlineKeyboardButton(text="💳 По карте", callback_data="pay_card"))
    builder.row(types.InlineKeyboardButton(text="◀️ Назад", callback_data="buy_vds"))

    await callback.message.edit_text(
        "💳 **Выберите способ оплаты:**\n\n"
        "Реквизиты для Т-Банк: `2200702073082773`",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(PurchaseState.selecting_payment, F.data.in_({"pay_sbp", "pay_card"}))
async def process_payment_method(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pay_method = callback.data

    if pay_method == "pay_sbp":
        pay_info = "📱 **Оплата через СБП**\n\nНомер телефона: `+7 (999) 123-45-67` (Т-Банк / Сбер)\nСумма: `{total}₽`"
    else:
        pay_info = "💳 **Оплата по карте**\n\nНомер карты (Т-Банк): `2200702073082773`\nСумма: `{total}₽`"

    formatted_pay_info = pay_info.format(total=data['total_price'])

    # Имитируем успешную покупку и добавляем в список серверов пользователя
    user_id = callback.from_user.id
    if user_id not in user_servers:
        user_servers[user_id] = []

    user_servers[user_id].append({
        "ram": data['ram'],
        "region": data['region'],
        "price": data['total_price']
    })

    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💻 Мои сервера", callback_data="my_servers"))
    builder.row(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))

    await callback.message.edit_text(
        f"{formatted_pay_info}\n\n✅ **Оплата прошла успешно!** Ваш сервер добавлен в раздел «Мои сервера».",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


# --- АДМИН-ПАНЕЛЬ ---
@dp.callback_query(F.data == "admin_panel")
async def admin_panel_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа к этой панели.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="➕ Выдать сервер", callback_data="admin_give_server"))
    builder.row(types.InlineKeyboardButton(text="◀️ Назад в меню", callback_data="main_menu"))

    await callback.message.edit_text(
        "⚙️ **Админ-панель управления**\n\nВыберите действие:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_give_server")
async def admin_give_server_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    await state.set_state(AdminState.waiting_for_ram)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_panel"))

    await callback.message.edit_text(
        "📝 **Выдача сервера (Шаг 1/4)**\n\nВведите память сервера (например: `5` или `5 GB`):",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(AdminState.waiting_for_ram)
async def admin_get_ram(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(ram=message.text.strip())
    await state.set_state(AdminState.waiting_for_region)
    await message.answer("🌍 **Выдача сервера (Шаг 2/4)**\n\nВведите регион сервера (например: `Нидерланды`):")


@dp.message(AdminState.waiting_for_region)
async def admin_get_region(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(region=message.text.strip())
    await state.set_state(AdminState.waiting_for_term)
    await message.answer("⏳ **Выдача сервера (Шаг 3/4)**\n\nВведите срок (например: `30 дней` или `Навсегда`):")


@dp.message(AdminState.waiting_for_term)
async def admin_get_term(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(term=message.text.strip())
    await state.set_state(AdminState.waiting_for_user_id)
    await message.answer("👤 **Выдача сервера (Шаг 4/4)**\n\nВведите ID аккаунта Telegram пользователя, кому выдать сервер:")


@dp.message(AdminState.waiting_for_user_id)
async def admin_get_userid(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        target_user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный ID. Введите числовой Telegram ID:")
        return

    data = await state.get_data()
    await state.clear()

    # Добавляем сервер в базу целевого пользователя
    if target_user_id not in user_servers:
        user_servers[target_user_id] = []

    user_servers[target_user_id].append({
        "ram": data['ram'],
        "region": data['region'],
        "term": data['term']
    })

    await message.answer(f"✅ Сервер успешно выдан пользователю с ID `{target_user_id}`!", parse_mode="Markdown")

    # Уведомление пользователя (опционально)
    try:
        await bot.send_message(
            target_user_id,
            f"🎉 Вам администратор выдал новый сервер!\n\nПамять: `{data['ram']}`\nРегион: `{data['region']}`\nПроверьте раздел «Мои сервера».",
            parse_mode="Markdown"
        )
    except Exception:
        pass


# Возврат в главное меню по кнопке
@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🛒 Покупка VDS сервера", callback_data="buy_vds"),
        types.InlineKeyboardButton(text="💻 Мои сервера", callback_data="my_servers")
    )
    if callback.from_user.id == ADMIN_ID:
        builder.row(types.InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel"))

    await callback.message.edit_text(
        "👋 **Главное меню сервиса:**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
