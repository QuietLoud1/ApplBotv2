import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import application modules
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from middlewares.role_checker import RolesMiddleware, require_role
from database.database import add_user_role, user_roles


class FakeUser:
    def __init__(self, id):
        self.id = id

class FakeMessage:
    def __init__(self, user_id):
        self.from_user = FakeUser(user_id)
    async def answer(self, text):
        print("answer:", text)


@require_role("admin")
async def handler(event):
    print("handler executed")
    await event.answer("OK")


async def run_test():
    print("-- test: admin user should be allowed --")
    add_user_role(123, "admin")
    msg = FakeMessage(123)
    middleware = RolesMiddleware()
    # Aiogram passes a wrapped handler which accepts (event, data) and then
    # calls the actual user handler. We simulate that here so middleware sees
    # the same call pattern as in runtime.
    async def wrapped_handler(event, data):
        return await handler(event)

    await middleware(wrapped_handler, msg, {})

    print("-- test: default user should be blocked (no handler executed) --")
    msg2 = FakeMessage(999)
    await middleware(wrapped_handler, msg2, {})

if __name__ == '__main__':
    asyncio.run(run_test())
