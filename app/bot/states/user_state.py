from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    setting_goal = State()
    sending_report = State()
