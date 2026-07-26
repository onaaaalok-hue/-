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
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ID администратора
ADMIN_ID = 7738822030

# База данных серверов в памяти: 
# { user_id: [ { "game": "...", "slots": "...", "region": "...", "price": ..., "ip": "...", "status": "Включен" } ] }
user_servers = {}


# Состояния FSM для покупки игрового сервера
class PurchaseState(StatesGroup):
    selecting_game = State()
    selecting_slots = State()
    selecting_region = State()
    confirming = State()
    selecting_payment = State()
    waiting_for_screenshot = State()


# Состояния для админ-панели (выдача сервера вручную)
class AdminState(StatesGroup):
    waiting_for_game = State()
    waiting_for_slots = State()
    waiting_for_region = State()
    waiting_for_user_id = State()


# Игры и их базовые цены за слот
GAMES = {
    "Minecraft": {"name": "Minecraft", "price_per_unit": 15, "unit": "слот"},
    "CRMP": {"name": "CRMP (GTA RP)", "price_per_unit": 2, "unit": "слот"},
    "SAMP": {"name": "SA-MP", "price_per_unit": 1.5, "unit": "слот"},
    "CSGO": {"name": "CS:GO", "price_per_unit": 25, "unit": "слот"},
    "CS16": {"name": "Counter-Strike 1.6", "price_per_unit": 10, "unit": "слот"}
}

# Доступные слоты для выбора
SLOTS_VARIANTS = [10, 25, 50, 100, 200, 500]

# Цены на регионы
REGION_PRICES = {
    "Москва": 0,
    "Санкт-Петербург": 50,
    "Нидерланды": 150,
    "Германия": 200
}


# --- ГЛАВНОЕ МЕНЮ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🎮 Купить игровой сервер", callback_data="buy_game_server"),
        types.InlineKeyboardButton(text="💻 Мои сервера", callback_data="my_servers")
    )
    
    if message.from_user.id == ADMIN_ID:
        builder.row(types.InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel"))

    await message.answer(
        "👋 **Добро пожаловать в игровой хостинг!**\n\n"
        "У нас вы можете арендовать сервера для Minecraft, CRMP, SA-MP, CS:GO и CS 1.6.\n\n"
        "Выберите нужный раздел в меню ниже:",
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
            "❌ У вас не куплен ни один игровой сервер.\n\n"
            "Приобрести сервер можно по кнопке «Купить игровой сервер» ниже:"
        )
        builder.row(types.InlineKeyboardButton(text="🎮 Купить игровой сервер", callback_data="buy_game_server"))
    else:
        text = "💻 **Ваши активные игровые сервера:**"
        for idx, srv in enumerate(servers):
            status_icon = "🟢" if srv.get("status", "Включен") == "Включен" else "🔴"
            builder.row(
                types.InlineKeyboardButton(
                    text=f"{status_icon} {srv['game']} | {srv['slots']} слот. ({srv['region']})",
                    callback_data=f"server_info_{user_id}_{idx}"
                )
            )

    builder.row(types.InlineKeyboardButton(text="◀️ Назад в меню", callback_data="main_menu"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


# Управление конкретным сервером (вкл/выкл + данные)
@dp.callback_query(F.data.startswith("server_info_"))
async def server_details(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    user_id = int(data_parts[2])
    idx = int(data_parts[3])

    servers = user_servers.get(user_id, [])
    if idx < len(servers):
        srv = servers[idx]
        status = srv.get("status", "Включен")
        status_text = "Работает 🟢" if status == "Включен" else "Остановлен 🔴"
        
        text = (
            f"🎮 **Игровой сервер: {srv['game']}**\n\n"
            f"• Слоты: `{srv['slots']} шт.`\n"
            f"• Регион: `{srv['region']}`\n"
            f"• Статус: `{status_text}`\n\n"
            f"🔑 **Данные для подключения и управления:**\n"
            f"• IP:Port: `{srv.get('ip', '46.174.50.12:27015')}`\n"
            f"• Панель управления: `https://panel.myhost.ru/login/{user_id}`\n"
            f"• FTP доступ: `ftp://user{user_id}@panel.myhost.ru`\n"
            f"• Пароль: `GamePass#{user_id}`"
        )
        
        builder = InlineKeyboardBuilder()
        # Кнопка включения/выключения сервера
        toggle_text = "🔴 Выключить сервер" if status == "Включен" else "🟢 Включить сервер"
        builder.row(types.InlineKeyboardButton(text=toggle_text, callback_data=f"toggle_srv_{user_id}_{idx}"))
        builder.row(types.InlineKeyboardButton(text="◀️ Назад к серверам", callback_data="my_servers"))
    else:
        text = "❌ Сервер не найден."
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="◀️ Назад к серверам", callback_data="my_servers"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


# Обработка переключения статуса сервера (Вкл / Выкл)
@dp.callback_query(F.data.startswith("toggle_srv_"))
async def toggle_server_status(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    user_id = int(data_parts[2])
    idx = int(data_parts[3])

    if callback.from_user.id != user_id and callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет прав на управление этим сервером.", show_alert=True)
        return

    servers = user_servers.get(user_id, [])
    if idx < len(servers):
        current_status = servers[idx].get("status", "Включен")
        new_status = "Выключен" if current_status == "Включен" else "Включен"
        servers[idx]["status"] = new_status
        
        status_action = "выключен" if new_status == "Выключен" else "включен"
        await callback.answer(f"Сервер успешно {status_action}!", show_alert=False)
        
        # Обновляем интерфейс отображения сервера
        srv = servers[idx]
        status_text = "Работает 🟢" if new_status == "Включен" else "Остановлен 🔴"
        
        text = (
            f"🎮 **Игровой сервер: {srv['game']}**\n\n"
            f"• Слоты: `{srv['slots']} шт.`\n"
            f"• Регион: `{srv['region']}`\n"
            f"• Статус: `{status_text}`\n\n"
            f"🔑 **Данные для подключения и управления:**\n"
            f"• IP:Port: `{srv.get('ip', '46.174.50.12:27015')}`\n"
            f"• Панель управления: `https://panel.myhost.ru/login/{user_id}`\n"
            f"• FTP доступ: `ftp://user{user_id}@panel.myhost.ru`\n"
            f"• Пароль: `GamePass#{user_id}`"
        )
        
        builder = InlineKeyboardBuilder()
        toggle_text = "🔴 Выключить сервер" if new_status == "Включен" else "🟢 Включить сервер"
        builder.row(types.InlineKeyboardButton(text=toggle_text, callback_data=f"toggle_srv_{user_id}_{idx}"))
        builder.row(types.InlineKeyboardButton(text="◀️ Назад к серверам", callback_data="my_servers"))

        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    else:
        await callback.answer("❌ Сервер не найден.", show_alert=True)


# --- ПРОЦЕСС ПОКУПКИ СЕРВЕРА ---
@dp.callback_query(F.data == "buy_game_server")
async def buy_server_step1(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(PurchaseState.selecting_game)
    
    builder = InlineKeyboardBuilder()
    # Инлайн кнопки для выбора игр в ряд/колонку с красивыми эмодзи
    builder.row(types.InlineKeyboardButton(text="🧱 Minecraft", callback_data="game_Minecraft"))
    builder.row(types.InlineKeyboardButton(text="🚗 CRMP (GTA RP)", callback_data="game_CRMP"))
    builder.row(types.InlineKeyboardButton(text="🔫 SA-MP", callback_data="game_SAMP"))
    builder.row(types.InlineKeyboardButton(text="🎯 CS:GO", callback_data="game_CSGO"))
    builder.row(types.InlineKeyboardButton(text="💣 Counter-Strike 1.6", callback_data="game_CS16"))
    builder.row(types.InlineKeyboardButton(text="◀️ Назад в меню", callback_data="main_menu"))

    await callback.message.edit_text(
        "🎮 **Выбор игры**\n\nВыберите дисциплину с помощью инлайн-кнопок ниже:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(PurchaseState.selecting_game, F.data.startswith("game_"))
async def process_game_selection(callback: types.CallbackQuery, state: FSMContext):
    game_key = callback.data.split("_", 1)[1]
    game_info = GAMES.get(game_key)

    await state.update_data(game_key=game_key, game_name=game_info['name'], price_per_unit=game_info['price_per_unit'])
    await state.set_state(PurchaseState.selecting_slots)

    builder = InlineKeyboardBuilder()
    for slots in SLOTS_VARIANTS:
        total_price = slots * game_info['price_per_unit']
        builder.row(types.InlineKeyboardButton(text=f"{slots} слотов — {total_price}₽", callback_data=f"slots_{slots}"))
    builder.row(types.InlineKeyboardButton(text="◀️ Назад к играм", callback_data="buy_game_server"))

    await callback.message.edit_text(
        f"📊 **Вы выбрали игру:** {game_info['name']}\n\nВыберите количество слотов:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(PurchaseState.selecting_slots, F.data.startswith("slots_"))
async def process_slots_selection(callback: types.CallbackQuery, state: FSMContext):
    slots = int(callback.data.split("_")[1])
    data = await state.get_data()
    slots_price = slots * data['price_per_unit']

    await state.update_data(slots=slots, slots_price=slots_price)
    await state.set_state(PurchaseState.selecting_region)

    builder = InlineKeyboardBuilder()
    for reg, cost in REGION_PRICES.items():
        rec_text = " (Рекомендация)" if reg == "Москва" else ""
        builder.row(types.InlineKeyboardButton(text=f"🌍 {reg} (+{cost}₽){rec_text}", callback_data=f"reg_{reg}"))
    builder.row(types.InlineKeyboardButton(text="◀️ Назад к слотам", callback_data=f"game_{data['game_key']}"))

    await callback.message.edit_text(
        "🌍 **Выбор локации сервера**\n\nРекомендация для низкого пинга: Москва 🇷🇺\nВыберите регион:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(PurchaseState.selecting_region, F.data.startswith("reg_"))
async def process_region_selection(callback: types.CallbackQuery, state: FSMContext):
    region_name = callback.data.split("_", 1)[1]
    reg_price = REGION_PRICES.get(region_name, 0)

    await state.update_data(region=region_name, reg_price=reg_price)
    await state.set_state(PurchaseState.confirming)

    data = await state.get_data()
    total_price = data['slots_price'] + data['reg_price']
    await state.update_data(total_price=total_price)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Подтвердить данные", callback_data="confirm_order"))
    builder.row(types.InlineKeyboardButton(text="◀️ Назад к регионам", callback_data="buy_game_server"))

    text = (
        f"📋 **Подтверждение заказа:**\n\n"
        f"• Игра: `{data['game_name']}`\n"
        f"• Слоты: `{data['slots']} шт.` — `{data['slots_price']}₽`\n"
        f"• Локация: `{data['region']}` — `{data['reg_price']}₽`\n\n"
        f"💰 **Итого к оплате:** `{total_price}₽`"
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(PurchaseState.confirming, F.data == "confirm_order")
async def process_confirmation(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(PurchaseState.selecting_payment)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📱 СБП", callback_data="pay_sbp"))
    builder.row(types.InlineKeyboardButton(text="💳 По карте", callback_data="pay_card"))
    builder.row(types.InlineKeyboardButton(text="◀️ Назад", callback_data="buy_game_server"))

    await callback.message.edit_text(
        "💳 **Выберите способ оплаты:**\n\n"
        "Реквизиты для Т-Банк:\n"
        "• Карта: `2200702073082773`\n"
        "• СБП (телефон): `+79085127611` (Т-Банк)",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(PurchaseState.selecting_payment, F.data.in_({"pay_sbp", "pay_card"}))
async def process_payment_method(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pay_method = callback.data

    if pay_method == "pay_sbp":
        pay_info = "📱 **Оплата через СБП**\n\nНомер телефона: `+79085127611` (Банк: **Т-Банк**)\nСумма к оплате: `{total}₽`"
    else:
        pay_info = "💳 **Оплата по карте**\n\nНомер карты: `2200702073082773` (Банк: **Т-Банк**)\nСумма к оплате: `{total}₽`"

    formatted_pay_info = pay_info.format(total=data['total_price'])

    await state.set_state(PurchaseState.waiting_for_screenshot)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="◀️ Отменить заказ", callback_data="buy_game_server"))

    await callback.message.edit_text(
        f"{formatted_pay_info}\n\n"
        f"📸 **Отправьте скриншот или чек перевода в этот чат.**\n"
        f"После отправки поддержка проверит платеж, и игровой сервер будет выдан вручную!",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


# Получение скриншота и отправка администратору
@dp.message(PurchaseState.waiting_for_screenshot, F.photo)
async def process_payment_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = message.from_user
    photo = message.photo[-1].file_id

    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    
    await message.answer(
        "⏳ **Чек принят!**\n\nВаш платеж отправлен поддержке. Как только администратор проверит перевод, игровой сервер появится в разделе «Мои сервера».",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

    admin_builder = InlineKeyboardBuilder()
    admin_builder.row(
        types.InlineKeyboardButton(
            text="✅ Выдать сервер",
            callback_data=f"admin_give_game_{user.id}_{data['game_name']}_{data['slots']}_{data['region']}"
        )
    )

    caption = (
        f"🔔 **Новый чек на игровой сервер!**\n\n"
        f"• Пользователь: @{user.username} (ID: `{user.id}`)\n"
        f"• Игра: `{data['game_name']}` | Слоты: `{data['slots']}`\n"
        f"• Локация: `{data['region']}`\n"
        f"• Сумма: `{data['total_price']}₽`"
    )

    try:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo,
            caption=caption,
            reply_markup=admin_builder.as_markup(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить чек админу: {e}")


@dp.message(PurchaseState.waiting_for_screenshot)
async def wrong_screenshot_format(message: types.Message):
    await message.answer("❌ Пожалуйста, отправьте именно **скриншот (фото)** чека перевода.")


# --- АДМИН-ПАНЕЛЬ И ВЫДАЧА ИЗ ЧЕКА ---
@dp.callback_query(F.data.startswith("admin_give_game_"))
async def admin_give_from_order(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    parts = callback.data.split("_")
    target_user_id = int(parts[3])
    game_name = parts[4]
    slots = parts[5]
    region = "_".join(parts[6:])

    if target_user_id not in user_servers:
        user_servers[target_user_id] = []

    user_servers[target_user_id].append({
        "game": game_name,
        "slots": slots,
        "region": region,
        "ip": "46.174.50.88:27015",
        "status": "Включен"
    })

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ **СТАТУС: Игровой сервер успешно выдан!**",
        reply_markup=None
    )
    await callback.answer("Сервер успешно выдан пользователю!")

    try:
        await bot.send_message(
            target_user_id,
            f"🎉 **Ваш платеж успешно проверен!**\n\nИгровой сервер (`{game_name}`, слотов: `{slots}`, регион: `{region}`) добавлен в раздел «Мои сервера».",
            parse_mode="Markdown"
        )
    except Exception:
        pass


@dp.callback_query(F.data == "admin_panel")
async def admin_panel_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа к этой панели.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="➕ Выдать сервер вручную", callback_data="admin_give_manual"))
    builder.row(types.InlineKeyboardButton(text="◀️ Назад в меню", callback_data="main_menu"))

    await callback.message.edit_text(
        "⚙️ **Админ-панель игрового хостинга**\n\nВыберите действие:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_give_manual")
async def admin_give_manual_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    await state.set_state(AdminState.waiting_for_game)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_panel"))

    await callback.message.edit_text(
        "📝 **Ручная выдача (Шаг 1/4)**\n\nВведите название игры (например: `Minecraft` или `CS:GO`):",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(AdminState.waiting_for_game)
async def admin_get_game(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(game=message.text.strip())
    await state.set_state(AdminState.waiting_for_slots)
    await message.answer("📊 **Ручная выдача (Шаг 2/4)**\n\nВведите количество слотов (например: `32`):")


@dp.message(AdminState.waiting_for_slots)
async def admin_get_slots(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(slots=message.text.strip())
    await state.set_state(AdminState.waiting_for_region)
    await message.answer("🌍 **Ручная выдача (Шаг 3/4)**\n\nВведите регион (например: `Москва`):")


@dp.message(AdminState.waiting_for_region)
async def admin_get_region(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(region=message.text.strip())
    await state.set_state(AdminState.waiting_for_user_id)
    await message.answer("👤 **Ручная выдача (Шаг 4/4)**\n\nВведите Telegram ID пользователя, которому выдать сервер:")


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

    if target_user_id not in user_servers:
        user_servers[target_user_id] = []

    user_servers[target_user_id].append({
        "game": data['game'],
        "slots": data['slots'],
        "region": data['region'],
        "ip": "46.174.50.88:27015",
        "status": "Включен"
    })

    await message.answer(f"✅ Игровой сервер успешно выдан пользователю с ID `{target_user_id}`!", parse_mode="Markdown")

    try:
        await bot.send_message(
            target_user_id,
            f"🎉 Администратор выдал вам игровой сервер!\n\nИгра: `{data['game']}`\nСлотов: `{data['slots']}`\nРегион: `{data['region']}`\nПроверьте раздел «Мои сервера».",
            parse_mode="Markdown"
        )
    except Exception:
        pass


@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🎮 Купить игровой сервер", callback_data="buy_game_server"),
        types.InlineKeyboardButton(text="💻 Мои сервера", callback_data="my_servers")
    )
    if callback.from_user.id == ADMIN_ID:
        builder.row(types.InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel"))

    await callback.message.edit_text(
        "👋 **Главное меню игрового хостинга:**",
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
