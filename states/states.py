from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State, default_state
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

class MenuStates(StatesGroup):
    main_menu = State()
    report_problem_restaurant_pick = State()
    report_a_problem_with_text = State()
    view_claimed_requests_mechanic = State()
    admin_panel_pick_statistics = State()

@dataclass
class PaginationState:
    """Состояние пагинации для пользователя"""
    applications: List[dict]
    current_index: int = 0
    application_type: str = ""  # 'in_work' или 'pending'
    last_update: datetime = datetime.now()


class PaginationManager:
    """Менеджер состояний пагинации"""
    
    def __init__(self):
        self.user_states: Dict[int, PaginationState] = {}
    
    def set_state(self, user_id: int, applications: List[dict], app_type: str):
        """Установить состояние для пользователя"""
        self.user_states[user_id] = PaginationState(
            applications=applications,
            current_index=0,
            application_type=app_type
        )
    
    def get_state(self, user_id: int) -> Optional[PaginationState]:
        """Получить состояние пользователя"""
        return self.user_states.get(user_id)
    
    def update_index(self, user_id: int, delta: int):
        if user_id in self.user_states:
            state = self.user_states[user_id]
            new_index = state.current_index + delta
            
            # Проверяем границы
            if 0 <= new_index < len(state.applications):
                state.current_index = new_index
                state.last_update = datetime.now()
    
    def remove_application(self, user_id: int, application_id: int):
        """Удалить заявку из состояния пользователя"""
        if user_id in self.user_states:
            state = self.user_states[user_id]
            state.applications = [
                app for app in state.applications 
                if app['id'] != application_id
            ]
            
            if state.current_index >= len(state.applications):
                state.current_index = max(0, len(state.applications) - 1)
    
    def clear_state(self, user_id: int):
        """Очистить состояние пользователя"""
        self.user_states.pop(user_id, None)


# Глобальный экземпляр менеджера
pagination_manager = PaginationManager()