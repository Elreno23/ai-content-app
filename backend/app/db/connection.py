from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.base import Base

DATABASE_URL = "postgresql+asyncpg://postgres:LL.mamA.@localhost:5432/simulation_db"

#Engine asincrono: administra conexiones y ejecuta sql

engine = create_async_engine(
    DATABASE_URL,
    echo=True,# Muestra las consultas SQL en consola
    future=True # Activa el modo moderno de SQLAlchemy 2.x
)

#sessionmaker asíncrono: crea sesiones por request
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession, #asíncrono igual que el engine
    expire_on_commit=False
)

#Dependencia para FastAPI: abre y cierra sesiones
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Función para crear tablas desde código (usar en startup o script)
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)