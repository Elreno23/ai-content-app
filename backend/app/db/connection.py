from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async_engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True
)

async_session_maker = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False
)

async def get_db():
    async with async_session_maker() as session:
        yield session