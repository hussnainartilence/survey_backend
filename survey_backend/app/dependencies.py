""" Application Dependencies """

import logging
from asyncio import TaskGroup
from enum import Enum
from typing import Annotated, AsyncIterator, Iterable,  Optional

from fastapi import Depends, Header, HTTPException
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from requests import HTTPError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status
from starlette.requests import Request

from .db.database import DBManager, DBHost
from .db.models import AuthMode, AuthRole, User


from .settings import SYSTEM_API_KEY

from .utils import (
    LocalTokenVerificationError,
    is_local_token,
    verify_local_token,
)

logger = logging.getLogger("auth_logger")

# api key authentication
api_key = APIKeyHeader(name="access_key")
api_key_multiple = APIKeyHeader(name="access_key", auto_error=False)

# authentication scheme
oauth2_scheme = OAuth2PasswordBearer("token")
oauth2_scheme_multiple = OAuth2PasswordBearer(
    tokenUrl="token", auto_error=False
)


class GRPCErrorMappingEnum(Enum):
    OK = 200
    INVALID_ARGUMENT = 400
    FAILED_PRECONDITION = 400
    OUT_OF_RANGE = 400
    UNAUTHENTICATED = 401
    PERMISSION_DENIED = 403
    NOT_FOUND = 404
    ABORTED = 409
    ALREADY_EXISTS = 409
    RESOURCE_EXHAUSTED = 429
    CANCELLED = 499
    DATA_LOSS = 500
    UNKNOWN = 500
    INTERNAL = 500
    NOT_IMPLEMENTED = 501
    NA = 502
    UNAVAILABLE = 503
    DEADLINE_EXCEEDED = 504


INVALID_TOKEN = "Invalid token"
TOKEN_EXPIRED = "Token expired"


def init_db_manager(
    host: DBHost = DBHost.LEADER,
) -> DBManager:
    return DBManager(host)


async def _close_sessions(db_sessions: Iterable[AsyncSession]):
    async with TaskGroup() as tg:
        for db_session in db_sessions:
            print(f"Closing session {id(db_session)}")
            tg.create_task(db_session.close())


async def close_all_sessions(db_manager: DBManager):
    """
    Close all sessions
    """
    sessions = db_manager.scoped_session.registry.registry.values()
    await _close_sessions(sessions)


async def get_db_manager() -> AsyncIterator[DBManager]:
    """
    Get leader database session
    """
    db_manager = init_db_manager()
    try:
        yield db_manager
    except SQLAlchemyError as err:
        logging.error(err)
    finally:
        await close_all_sessions(db_manager)


class DBHostAdapter:
    """
    This adapter can be used to override the default DB host
    """

    def __init__(self, host: DBHost):
        self.host = host

    async def __call__(self):
        db_manager = init_db_manager(self.host)
        try:
            yield db_manager
        except SQLAlchemyError as err:
            logging.error(err)
        finally:
            await close_all_sessions(db_manager)


dbManager = Annotated[DBManager, Depends(get_db_manager)]

# use follower db for read operations only
dbFollowerManager = Annotated[
    DBManager, Depends(DBHostAdapter(DBHost.FOLLOWER))
]


async def verify_token(
    db_manager: dbManager,
    token: str = Depends(oauth2_scheme),
):
    """
    Verify token

    Parameters
    ----------
    token - token to verify

    Returns
    -------
    user data
    """
    _session: AsyncSession
    async with db_manager.get_session() as _session:
        try:
            if is_local_token(token):
                # local token verification
                user_info = await verify_local_token(token, _session)
            return user_info, token
        except (
            HTTPError,
            LocalTokenVerificationError,
        ) as ex:
            raise HTTPException(
                status_code=401, detail={"token": INVALID_TOKEN}
            ) from ex


async def get_current_user(
    db_manager: dbManager,
    token: str = Depends(oauth2_scheme),
) -> Optional[User]:
    """
    Return the currently logged-in user
    Parameters
    ----------
    token - authentication token

    Returns
    -------
    the currently logged-in user
    """

    current_user: Optional[User] = None
    _session: AsyncSession

    async with db_manager.get_session() as _session:
        try:
            if is_local_token(token):
                # local token verification
                current_user = await verify_local_token(token, _session)
        except (
            HTTPError,
            LocalTokenVerificationError,
        ) as ex:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"token": "Invalid token"},
            ) from ex

        return current_user


async def get_current_user_or_none(
    db_manager: dbManager,
    request: Request,
) -> User | None:
    if request.headers.get("Authorization"):
        authorization = request.headers.get("Authorization")
        _, token = get_authorization_scheme_param(authorization)
        if not token:
            return None

        try:
            user = await get_current_user(
            token=token, db_manager=db_manager
            )
        except HTTPException:
            return None

        return user
    return None


async def get_current_user_from_api_key(
    db_manager: dbManager, api_key_header: str = Depends(api_key)
):
    async with db_manager.get_session() as _session:
        # load user from DB
        result = await _session.execute(
            select(User)
            .where(User.api_key == api_key_header)
            .options(selectinload(User.groups))
        )
        user = result.scalars().first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"api_key": "The access_key is no longer valid"},
            )
    return user


async def get_current_user_from_multiple_auth(
    db_manager: dbManager,
    api_key: Optional[str] = Depends(api_key_multiple),
    token: Optional[str] = Depends(oauth2_scheme_multiple),
) -> User:
    # check first api_key
    if api_key:
        try:
            return await get_current_user_from_api_key(
                api_key_header=api_key, db_manager=db_manager
            )
        except HTTPException:
            pass
    # then check token if API key didn't work
    if token:
        try:
            return await get_current_user(
             token=token, db_manager=db_manager
            )
        except HTTPException:
            pass

    # if neither API key nor token is valid, raise an exception
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"api_key": "Not valid.", "token": "Not valid."},
    )


def get_system_qa_key_from_header(
    x_qa_key: Annotated[str | None, Header()] = None
) -> str | None:
    return x_qa_key


def get_system_key_from_header(
    x_api_key: Annotated[str | None, Header()] = None
) -> str | None:
    return x_api_key


XAPIKey = Annotated[str | None, Depends(get_system_key_from_header)]


class RoleAuthorization:
    """
    Dependency that extracts user using get_current_user method and checks required roles.
    """

    def __init__(
        self,
        required_roles: list[AuthRole | str] = None,
        *,
        visible_roles: list[AuthRole | str] = None,
        show_for_firebase: bool = False,
        use_x_api_key: bool = False,
    ) -> None:
        self.required_roles = required_roles
        # routes with flag show_for_firebase always allowed for firebase users
        self.show_for_firebase = show_for_firebase
        self.visible_roles = visible_roles if visible_roles else required_roles
        self.use_x_api_key = use_x_api_key

    def __call__(
        self,
        user=Depends(get_current_user_or_none),
    ) -> User:
        self.user: User | None = user
        self._check_user_roles()

        return user

    def _check_user_roles(self, x_api_key: XAPIKey = "") -> bool:
        forbidden_access_exception = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"global": "Access denied: insufficient permissions."},
        )

        if self.use_x_api_key and x_api_key == SYSTEM_API_KEY:
            return True

        # return immediately on routes which have no constraint
        if not self.required_roles:
            return True
        if not self.user:
            # "NOT_A_USER" is a special case in which a route is invisible
            # only to logged in users
            if "__NOT_A_USER__" in self.required_roles:
                return True
            # otherwise raise forbidden access
            else:
                raise forbidden_access_exception

        # raise forbidden access is user is unverified
        if not self.user.email_verified:
            raise forbidden_access_exception

        # return on self.show_for_firebase after user check
        if self.show_for_firebase and self.user.auth_mode == AuthMode.FIREBASE:
            return True

        # raise forbidden access is user has no groups
        if not self.user.groups:
            raise forbidden_access_exception

        user_roles = set([group.name for group in self.user.groups])

        # return always for admin
        if AuthRole.ADMIN in user_roles:
            return True

        # look for the user's role in the required roles then raise if empty
        matching_roles = user_roles.intersection(set(self.required_roles))
        if not matching_roles:
            raise forbidden_access_exception

        return True

    async def check_user_roles(
        self, db_manager: DBManager, request: Request, x_api_key: XAPIKey = ""
    ) -> bool:
        self.user = await get_current_user_or_none(
            db_manager=db_manager, request=request
        )
        return self._check_user_roles(x_api_key=x_api_key)


class RoleAuthorizationFromApikey(RoleAuthorization):
    def __call__(
        self,
        x_api_key: XAPIKey = "",
        user=Depends(get_current_user_from_api_key),
    ) -> User:
        self.user: User = user
        self._check_user_roles(x_api_key=x_api_key)

        return user


class RoleAuthorizationForMultipleAuth(RoleAuthorization):
    def __call__(
        self,
        user=Depends(get_current_user_from_multiple_auth),
    ) -> User:
        self.user: User = user
        self._check_user_roles()

        return user

