from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from sqlalchemy.engine import URL


from app.config import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    DB_ECHO
)


DATABASE_URL = URL.create(
    drivername="postgresql+asyncpg",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)




engine = create_async_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    future=True,
)


AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)