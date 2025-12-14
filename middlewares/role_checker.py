from typing import Any, Awaitable
from aiogram.types import Message, CallbackQuery
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from database.database import get_user_role, add_user_role
from functools import wraps
from lexicon.lexicon import LEXICON
from typing import Union, Callable
import logging
from aiogram.filters import Filter

logger = logging.getLogger(__name__)

class RolesMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # store both raw user_id and the resolved role in data for handlers
        user_id = None
        if hasattr(event, 'from_user') and event.from_user is not None:
            user_id = event.from_user.id
        # store user_id and resolved role in data so decorators/handlers can access them
        data["user_id"] = user_id
        data["user_role"] = get_user_role(user_id=user_id) if user_id is not None else None
        

        # Aiogram's router/observer typically calls handlers with the data dict as a
        # second positional argument (wrapped_inner(event, data)). To remain
        # compatible with aiogram internals and avoid passing framework-internal
        # keys as unexpected keyword args, pass the data dict positionally.
        return await handler(event, data)
    
class RoleFilter(Filter):
    def __init__(self, role: str | list[str]):
        self.roles = [role] if isinstance(role, str) else role
    
    async def __call__(
        self,
        event: Union[Message, CallbackQuery],
        **kwargs
    ) -> bool:
        user_id = event.from_user.id
        
        # Пытаемся получить роль из данных, которые middleware уже добавил
        # Ищем data в аргументах или kwargs
        user_role = None
        
        # Пробуем получить data из kwargs
        if 'data' in kwargs:
            data = kwargs['data']
            if isinstance(data, dict):
                user_role = data.get('user_role')
        
        # Если не нашли в data, получаем из БД
        if user_role is None:
            user_role = get_user_role(user_id=user_id)
        
        return user_role in self.roles
    
def require_role(*allowed_roles: str):
    logger.info(f"ALLOWED ROLES {allowed_roles}")
    def decorator(handler: Callable) -> Callable:
        logger.info(f"ALLOWED ROLES {allowed_roles}")
        @wraps(handler)
        async def wrapper(event: Union[Message, CallbackQuery], *args, **kwargs):
            logger.info(f"ALLOWED ROLES {allowed_roles}")
            user_id = event.from_user.id
                
            if not user_id:
                await event.answer(LEXICON["no_permissions"])
                return
            
            # Try to obtain role from middleware-injected data. Aiogram commonly
            # passes a data dict as a second positional arg, so check there first;
            # fall back to kwargs if needed, otherwise query DB.
            user_role = None
            data_dict = None
            if args and isinstance(args[0], dict):
                data_dict = args[0]
            elif 'user_role' in kwargs or 'user_id' in kwargs:
                data_dict = kwargs

            if data_dict is not None and 'user_role' in data_dict and data_dict['user_role'] is not None:
                user_role = data_dict['user_role']
            else:
                user_role = get_user_role(user_id=user_id)
            logger.info(f"user_id={user_id!r}, USER ROLE={user_role!r}, allowed={allowed_roles}")
            if user_role not in allowed_roles:
                logger.info(f"User {user_id} is not allowed in group: {allowed_roles}")
                return
            return await handler(event, *args, **kwargs)
        return wrapper
    return decorator

