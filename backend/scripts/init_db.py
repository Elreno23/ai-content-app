import asyncio
from app.db.connection import init_models

if __name__ == "__main__":
    asyncio.run(init_models())