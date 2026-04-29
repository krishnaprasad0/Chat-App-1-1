import asyncio
from app.db.session import SessionLocal
from app.models.user import User
from sqlalchemy import select

async def get_users():
    async with SessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f"Username: {u.username} | ID: {u.id}")

if __name__ == "__main__":
    asyncio.run(get_users())
