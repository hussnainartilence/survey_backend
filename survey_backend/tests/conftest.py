""" Unit testing configuration """

import os
from asyncio import current_task, get_event_loop_policy
from typing import AsyncIterator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from pytest import FixtureRequest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from app.db.database import Base, DBManager
from app.dependencies import _close_sessions, get_db_manager
from app.main import app
from app.settings import TEST_DATABASE_URI

# pylint: disable = redefined-outer-name, unused-argument, invalid-name

from sqlalchemy.exc import SQLAlchemyError
@pytest.fixture(scope="session")
def event_loop(request: FixtureRequest) -> Generator:
    """
    Custom event loop for testing
    """
    loop = get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> Generator:
    """
    Sets up the test DB.
    """
    engine = create_engine(
        # use sync here
        f"{TEST_DATABASE_URI.replace('+aiosqlite', '')}",
        connect_args={"check_same_thread": False},
    )
    with engine.begin():
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        yield
        Base.metadata.drop_all(engine)
        Base.metadata.reflect(engine)



@pytest_asyncio.fixture(name="session")
async def session():
    """
    Create a database session for testing
    """
    # create test engine
    engine = create_async_engine(
        TEST_DATABASE_URI, connect_args={"check_same_thread": False}
    )
    # init connection to test DB
    async with engine.connect() as conn:
        await conn.begin()
        await conn.begin_nested()
        async_session_factory = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=conn,
            future=True,
            expire_on_commit=False,
        )

        def _get_current_task_id() -> int:
            return id(current_task())

        class TestDBManager(DBManager):
            def __init__(self):
                self.scoped_session_factory = async_scoped_session(
                    session_factory=async_session_factory,
                    scopefunc=_get_current_task_id,
                )

            def get_session(self):
                session = self.scoped_session_factory()
                print(f"Spawning session {id(session)}")
                return session

        # override app dependency to use test DB

        async def test_get_session() -> AsyncIterator[DBManager]:
            db_manager = TestDBManager()
            try:
                yield db_manager
            except SQLAlchemyError:
                pass
            finally:
                sessions = (
                    db_manager.scoped_session_factory.registry.registry.values()
                )
                await _close_sessions(sessions)

        app.dependency_overrides[get_db_manager] = test_get_session
        db_manager = TestDBManager()

        # drop database tables
        yield db_manager.get_session()
        sessions = db_manager.scoped_session_factory.registry.registry.values()
        await _close_sessions(sessions)
        await conn.rollback()
        app.dependency_overrides.clear()


@pytest_asyncio.fixture(name="client")
async def async_client_fixture():
    """
    Create a test client
    """

    # yield client to testing framework
    async with AsyncClient(app=app, base_url="http://tests") as async_client:
        yield async_client
