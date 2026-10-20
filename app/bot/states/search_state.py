from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_for_query = State()
    asking_book_question = State()


class UserStates(StatesGroup):
    setting_goal = State()
    sending_report = State()
