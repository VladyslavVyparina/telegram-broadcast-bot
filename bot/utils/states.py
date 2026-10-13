from aiogram.fsm.state import State, StatesGroup


class BroadcastState(StatesGroup):
    waiting_content = State()
    waiting_forward = State()
    quick_content = State()


class AutoPostState(StatesGroup):
    waiting_content = State()
    waiting_edit_item = State()


class ContentState(StatesGroup):
    waiting_welcome = State()
    waiting_trigger = State()
    waiting_reply_text = State()


class SubState(StatesGroup):
    waiting_channel = State()
    waiting_grouped_msg = State()


class QuickReplyState(StatesGroup):
    waiting_slot = State()
    waiting_content = State()


class UsersState(StatesGroup):
    waiting_search = State()


class VerificationState(StatesGroup):
    waiting_captcha = State()
    waiting_invite = State()


class InactiveState(StatesGroup):
    waiting_days = State()
    waiting_message = State()
    waiting_hours = State()


class ContentButtonState(StatesGroup):
    waiting_label = State()
    waiting_url = State()


class FinanceState(StatesGroup):
    waiting_product_title = State()
    waiting_product_desc = State()
    waiting_product_price = State()
    waiting_admin_id = State()
    waiting_website_url = State()
    waiting_invite_code = State()
    waiting_donation_amount = State()
    waiting_access_price = State()
