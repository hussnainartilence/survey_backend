""" Utility functions """
from datetime import datetime

from fastapi import HTTPException, status
from jose import jwt
from jose.exceptions import JWTClaimsError, JWTError
from jwt import DecodeError, ExpiredSignatureError
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import settings
from app.db.models import AuthMode, User

from .schemas.token import (
    AccessTokenData,
    RefreshTokenData,
    TokenValidationErrorEnum,
)

# pylint: disable = unsupported-binary-operation

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LocalTokenVerificationError(Exception):
    """Custom exception for locally generated token verification errors"""

    def __init__(self, code=TokenValidationErrorEnum):
        """
        Inits the instance of this class.
        """
        self.code = code


def encrypt_password(pwd: str):
    """
    Encrypt a password for database storage. Auto-generates the salt and encrypts it into the hash.
    :param pwd: the clear password to encrypt
    :return: the encrypted password
    """
    return pwd_context.hash(pwd)


def check_password(pwd: str, hashed_pwd):
    """
    Check encrypted password
    :param pwd: the clear password to check
    :param hashed_pwd: the hashed password to check against
    :return: true if the passwords match, false otherwise
    """

    try:
        valid = pwd_context.verify(pwd, hashed_pwd)
    except UnknownHashError:
        valid = False

    return valid


def create_access_token(data: AccessTokenData):
    """
    Creates an access token for JWT authentication
    :param data: token data
    """
    encoded_jwt = jwt.encode(
        data.dict(), settings.SECRET_KEY, algorithm=settings.HASH_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: RefreshTokenData) -> str:
    """
    Generates a refresh token.

    Args:
        data (RefreshTokenData): The token data.

    Returns:
        str: The JWT encoded refresh token.
    """

    return jwt.encode(
        data.dict(), settings.SECRET_KEY, algorithm=settings.HASH_ALGORITHM
    )


async def verify_local_token(token: str, session: AsyncSession) -> User | None:
    """
    Verifies a locally generated token
    :param token: access token
    :return: user information or relevant data from the token
    """
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.HASH_ALGORITHM]
        )
    except DecodeError as ex:
        raise LocalTokenVerificationError(
            code=TokenValidationErrorEnum.INVALID_SIGNATURE
        ) from ex
    except ExpiredSignatureError as ex:
        raise LocalTokenVerificationError(
            code=TokenValidationErrorEnum.EXPIRED
        ) from ex
    except JWTError as ex:
        raise LocalTokenVerificationError(
            code=TokenValidationErrorEnum.VERIFICATION_FAILED
        ) from ex

    user = await session.scalar(
        select(User)
        .options(selectinload(User.groups))
        .where(User.name == decoded_token["sub"])
    )
    if not user:
        return None
    iat = datetime.fromtimestamp(decoded_token["iat"])
    if user.token_iat != iat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"token": "Invalid token"},
        )
    return user


async def verify_refresh_token(rtoken: str, session: AsyncSession):
    try:
        decoded_token = jwt.decode(
            rtoken, settings.SECRET_KEY, algorithms=[settings.HASH_ALGORITHM]
        )
        token_data = RefreshTokenData(**decoded_token)
    except DecodeError as ex:
        raise LocalTokenVerificationError(
            code=TokenValidationErrorEnum.INVALID_SIGNATURE
        ) from ex
    except ExpiredSignatureError as ex:
        raise LocalTokenVerificationError(
            code=TokenValidationErrorEnum.EXPIRED
        ) from ex
    except JWTError as ex:
        raise LocalTokenVerificationError(
            code=TokenValidationErrorEnum.VERIFICATION_FAILED
        ) from ex

    # verify token content
    user = await session.scalar(
        select(User).where(User.name == token_data.sub)
    )
    if not user:
        raise LocalTokenVerificationError(
            code=TokenValidationErrorEnum.USER_NOT_FOUND
        )

    if token_data.uid != user.refresh_token_uid:
        raise LocalTokenVerificationError(
            code=TokenValidationErrorEnum.INVALID
        )

    return user


def is_local_token(token: str) -> bool:
    """
    Checks if the token is locally generated
    :param token: access token
    :return: True if the token is locally generated, False otherwise
    """
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.HASH_ALGORITHM]
        )
        token_type = decoded_token.get("auth_mode")
        return token_type == AuthMode.LOCAL
    except (DecodeError, ExpiredSignatureError, JWTClaimsError, JWTError):
        return False




async def increment_login_attempts_and_get_error_message(
    user: User,
    session: AsyncSession,
    firebase_user: bool = False,
    blocked_by_firebase: bool = False,
):
    # Increment failed login attempts for both user types.
    if user.failed_login_attempts is None:
        user.failed_login_attempts = 0
    user.failed_login_attempts += 1
    await session.commit()

    error_message = {
        "password": "Incorrect email or password. Please try again or reset your password."
    }

    # Firebase users are blocked by Firebase, so we check if it's blocked and return appropriate message.
    if firebase_user:
        if blocked_by_firebase:
            error_message = {
                "password": (
                    "You have entered the wrong password too many times. "
                    "Please try again later use this {{LINK}} if you have forgotten your password."
                ),
                "disable_login": True,
            }

        return error_message

    # Local users are blocked in our database.
    if user.failed_login_attempts >= settings.PASSWORD_MAX_LOGIN_ATTEMPTS:
        user.enabled = False
        await session.commit()

        error_message = {
            "password": (
                "You have entered the wrong password too many times. "
                "Please try again later use this {{LINK}} if you have forgotten your password."
            ),
            "disable_login": True,
        }

    return error_message
