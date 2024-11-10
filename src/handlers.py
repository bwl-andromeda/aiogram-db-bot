import asyncpg
from aiogram.fsm.context import FSMContext
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from src.kb import start_kb
from src.states import ReplenishmentStates, WasteStates, CategoryStates
from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

router = Router(name=__name__)


@router.message(CommandStart())
async def start_handler(message: Message):
    start_message = f"Привет, *{
        message.from_user.full_name}*\nДанный бот сделан как курсовая работа\n\
Я думаю тебе стоит попробовать мой функционал :)"
    await message.answer(start_message, reply_markup=await start_kb())


@router.message(F.text == "👤 Профиль")
async def profile(message: Message, db_pool: asyncpg.Pool):
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT full_name, balance FROM users WHERE user_id = $1",
            message.from_user.id,
        )
        if user:
            await message.reply(
                f"Имя: {user['full_name']}\nБаланс: {int(user['balance'])} руб.",
                reply_markup=await start_kb(),
            )


@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message, db_pool: asyncpg.Pool):
    async with db_pool.acquire() as conn:
        statistics = await conn.fetch(
            """
            SELECT c.name AS category_name, SUM(t.amount) AS total_amount
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = $1 AND t.is_income = FALSE
            GROUP BY c.name
            """,
            message.from_user.id,
        )

        if statistics:
            stats_message = "\n".join(
                [
                    f"{stat['category_name']}: {stat['total_amount']} руб."
                    for stat in statistics
                ]
            )
            await message.reply(f"Статистика *трат* по категориям:\n{stats_message}")
        else:
            await message.reply("У вас пока нет трат.")


@router.message(F.text == "💰 Пополнение")
async def start_replenishment(message: Message, state: FSMContext):
    await message.reply("*Введите сумму пополнения:*")
    await state.set_state(ReplenishmentStates.WAITING_FOR_AMOUNT)


@router.message(ReplenishmentStates.WAITING_FOR_AMOUNT)
async def process_replenishment(
    message: Message, state: FSMContext, db_pool: asyncpg.Pool
):
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError("*Сумма должна быть положительной!*")

        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET balance = balance + $1 WHERE user_id = $2",
                amount,
                message.from_user.id,
            )
            await conn.execute(
                "INSERT INTO transactions (amount, user_id, is_income) VALUES ($1, $2, TRUE)",
                amount,
                message.from_user.id,
            )
            await message.reply(
                f"Твой баланс был успешно пополнен на *{amount}* руб.",
                reply_markup=await start_kb(),
            )
            await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, введите *корректную* сумму.")


@router.message(F.text == "💸 Трата")
async def start_waste(message: Message, state: FSMContext):
    await message.reply("*Введите сумму траты:*")
    await state.set_state(WasteStates.WAITING_FOR_AMOUNT)


@router.message(WasteStates.WAITING_FOR_AMOUNT)
async def process_waste_amount(
    message: Message, state: FSMContext, db_pool: asyncpg.Pool
):
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")

        await state.update_data(amount=amount)

        async with db_pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT user_id FROM users WHERE user_id = $1", message.from_user.id
            )
            if user:
                user_id = user["user_id"]
                categories = await conn.fetch(
                    "SELECT name FROM categories WHERE user_id = $1",
                    user_id,
                )
            else:
                categories = None

        if categories:
            list_category = [category["name"] for category in categories]
            kb_list = []
            for category in list_category:
                kb_list.append([KeyboardButton(text=category)])
                print(kb_list)

            kb = ReplyKeyboardMarkup(
                keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True
            )
            await message.reply("Выберите категорию траты:", reply_markup=kb)
            await state.set_state(WasteStates.WAITING_FOR_CATEGORY)
        else:
            await message.reply("У вас нет категорий. Сначала добавьте категорию.")
            await state.clear()
    except ValueError as e:
        print(e)
        await message.reply("Пожалуйста, введите корректную сумму.")


@router.message(WasteStates.WAITING_FOR_CATEGORY)
async def process_waste_category(message: Message, state: FSMContext):
    category_name = message.text
    await state.update_data(
        category=category_name
    )  # Сохраняем категорию для дальнейшего использования
    await message.reply("Введите описание траты:")
    await state.set_state(
        WasteStates.WAITING_FOR_DESCRIPTION
    )  # Переходим к ожиданию описания


@router.message(WasteStates.WAITING_FOR_DESCRIPTION)
async def process_waste_description(
    message: Message, state: FSMContext, db_pool: asyncpg.Pool
):
    description = message.text
    data = await state.get_data()
    category_name = data["category"]
    amount = data["amount"]
    async with db_pool.acquire() as conn:
        category = await conn.fetchrow(
            "SELECT id FROM categories WHERE name = $1 AND user_id = $2",
            category_name,
            message.from_user.id,
        )
        if category:
            await conn.execute(
                "UPDATE users SET balance = balance - $1 WHERE user_id = $2",
                amount,
                message.from_user.id,
            )
            await conn.execute(
                "INSERT INTO transactions (amount, category_id, user_id, is_income, description) VALUES ($1, $2, $3, FALSE, $4)",
                amount,
                category["id"],
                message.from_user.id,
                description,
            )
            await message.reply(
                f"Трата в размере {amount} руб. в категории '{category_name}' с описанием '{description}' успешно записана.",
                reply_markup=await start_kb(),
            )
        else:
            await message.reply("Категория не найдена. Попробуйте еще раз.")
    await state.clear()


@router.message(F.text == "📂 Категории")
async def start_categories(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Показать категории", callback_data="show_categories"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Добавить категорию", callback_data="add_category"
                )
            ],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_main")],
        ]
    )
    await message.reply("Выберите действие:", reply_markup=kb)


@router.callback_query(
    lambda c: c.data in ["show_categories", "add_category", "back_to_main"]
)
async def process_category_action(
    callback_query: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool
):
    await callback_query.answer()

    if callback_query.data == "show_categories":
        async with db_pool.acquire() as conn:
            categories = await conn.fetch(
                "SELECT name FROM categories WHERE user_id = $1",
                callback_query.from_user.id,
            )

        if categories:
            category_list = "\n".join(
                [f"- {category['name']}" for category in categories]
            )
            await callback_query.message.reply(f"Ваши категории:\n{category_list}")
        else:
            await callback_query.message.reply("У вас пока нет категорий.")

    elif callback_query.data == "add_category":
        await callback_query.message.reply("Введите название новой категории:")
        await state.set_state(CategoryStates.WAITING_FOR_NEW_CATEGORY)

    elif callback_query.data == "back_to_main":
        await callback_query.message.reply(
            "Возвращаемся в главное меню.", reply_markup=await start_kb()
        )

    # Удаляем инлайн-клавиатуру после выбора действия
    await callback_query.message.edit_reply_markup(reply_markup=None)


@router.message(CategoryStates.WAITING_FOR_NEW_CATEGORY)
async def add_new_category(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    new_category = message.text

    async with db_pool.acquire() as conn:
        existing_category = await conn.fetchrow(
            "SELECT id FROM categories WHERE name = $1 AND user_id = $2",
            new_category,
            message.from_user.id,
        )

        if existing_category:
            await message.reply("Такая категория уже существует.")
        else:
            await conn.execute(
                "INSERT INTO categories (name, user_id) VALUES ($1, $2)",
                new_category,
                message.from_user.id,
            )
            await message.reply(f"Категория '{new_category}' успешно добавлена.")

    await state.clear()

    # Возвращаемся к выбору действий с категориями
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Показать категории", callback_data="show_categories"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Добавить категорию", callback_data="add_category"
                )
            ],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_main")],
        ]
    )
    await message.reply("Что бы вы хотели сделать дальше?", reply_markup=kb)
