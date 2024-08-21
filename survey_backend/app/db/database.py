""" Database """
import enum
from asyncio import current_task
from time import perf_counter

from sqlalchemy import event
from sqlalchemy.dialects.postgresql.base import PGDDLCompiler
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql.ddl import DropTable

from app import settings




class DBHost(str, enum.Enum):
    LEADER = "leader"
    FOLLOWER = "follower"


leader_engine = create_async_engine(
    settings.LIVE_DATABASE_LEADER_URI,
    **settings.db_settings.leader.engine_options
)
follower_engine = create_async_engine(
    settings.LIVE_DATABASE_FOLLOWER_URI,
    **settings.db_settings.follower.engine_options
)

sync_maker = sessionmaker()

common_session_params = {
    "autocommit": False,
    "autoflush": False,
    "expire_on_commit": False,
    "sync_session_class": sync_maker,
}

def get_sessionmaker(**kwargs) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker[AsyncSession](**kwargs)

def _get_current_task_id() -> int:
    return id(current_task())


sessionmakers = {
    DBHost.LEADER: async_sessionmaker[AsyncSession](
        bind=leader_engine, **common_session_params
    ),
    DBHost.FOLLOWER: async_sessionmaker[AsyncSession](
        bind=follower_engine, **common_session_params
    ),
}


class DBManager:
    def __init__(self, host: DBHost = DBHost.LEADER):
        self.host = host
        self.scoped_session = async_scoped_session(
            session_factory=sessionmakers[host],
            scopefunc=_get_current_task_id,
        )

    def get_session(self) -> AsyncSession:
        session = self.scoped_session()
        print(f"Spawning session {id(session)}")
        return session


@event.listens_for(leader_engine.sync_engine, "before_cursor_execute")
def bef_exc(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(perf_counter())


@event.listens_for(leader_engine.sync_engine, "after_cursor_execute")
def post_exc(conn, cursor, statement, parameters, context, executemany):
    total = perf_counter() - conn.info["query_start_time"].pop(-1)
    print(
        f"execution time: {total}; parameters: {parameters}; statement: {statement}"
    )
    # for k, v in context.__dict__.items():
    #     sql_logger.warning("%s = %s", k, v)


# base class for DB models
Base = declarative_base()
