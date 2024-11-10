from aiogram.fsm.state import State, StatesGroup


class ReplenishmentStates(StatesGroup):
    WAITING_FOR_AMOUNT = State()


class WasteStates(StatesGroup):
    WAITING_FOR_AMOUNT = State()
    WAITING_FOR_CATEGORY = State()
    WAITING_FOR_DESCRIPTION = State()


class CategoryStates(StatesGroup):
    WAITING_FOR_ACTION = State()
    WAITING_FOR_NEW_CATEGORY = State()
