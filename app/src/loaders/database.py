"""
MySQL Database management module using SQLAlchemy (Async).

"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
import logging


class DatabaseInterface:
    """Defines interface for any database connection."""
    async def get_session(self):
        raise NotImplementedError("get_session() must be implemented.")

class MySQLDatabase(DatabaseInterface):
    """Manage MySQL async connection and sessions."""
    _instance = None

    def __new__(cls, database_url: str):
        """Implement Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, database_url: str):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self.database_url = database_url
        self.engine = create_async_engine(self.database_url, echo=True)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        logging.info(f"MySQLDatabase initialized: {self.database_url}")


    @asynccontextmanager
    async def get_session(self):
        """Provide a transactional scope around a series of operations."""
        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logging.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()


    async def close(self):
        """Dispose database engine."""
        await self.engine.dispose()
        logging.info("Database engine disposed.")

def get_database() -> MySQLDatabase:
    """Factory to get the singleton MySQL database."""
    DATABASE_URL = "mysql+aiomysql://my_user:my_password@103.138.113.68/my_database"
    return MySQLDatabase(DATABASE_URL)
