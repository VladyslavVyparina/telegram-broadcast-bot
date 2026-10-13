from aiogram.fsm.state import State, StatesGroup


class CreateBotState(StatesGroup):
    waiting_token = State()


class AdminState(StatesGroup):
    waiting_price = State()
    waiting_duration = State()
    waiting_crypto_price_usdt = State()
    waiting_crypto_price_ton = State()
    waiting_grant_user = State()
    waiting_broadcast_content = State()
    waiting_ar_trigger = State()
    waiting_ar_reply = State()
    waiting_ar_edit_trigger = State()
    waiting_ar_edit_reply = State()
