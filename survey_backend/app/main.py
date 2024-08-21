"""Main App"""

from datetime import datetime
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.schemas.validation_exception_handler import (
    validation_exception_handler,
)

from . import settings
from .db.models import AuthMode, User
from .dependencies import dbManager

from .routers import auth_router

from .schemas.token import (
    AccessTokenData,
    RefreshTokenData,
    RefreshTokenRequest,
    Token,
    TokenValidationErrorEnum,
)
from .utils import (
    LocalTokenVerificationError,
    check_password,
    create_access_token,
    create_refresh_token,
    increment_login_attempts_and_get_error_message,
    verify_refresh_token,
)

# pylint: disable = invalid-name


# create main app
app = FastAPI(
    title=f"{settings.SERVICE_NAME} - API",
    version=settings.SERVICE_API_VERSION,
    docs_url=None,
    redoc_url=None,
    description="Fast API Auth Service",
    terms_of_service="",
    openapi_url=None,
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Middleware to log request response time.
    """
    s = perf_counter()
    response = await call_next(request)
    print(f"Request {request.url} response time: {perf_counter() - s}")
    return response


# Add CORS Middleware
app.add_middleware(CORSMiddleware, **settings.CORSSettings().dict())

# Add GZIP Middleware
app.add_middleware(GZipMiddleware, minimum_size=settings.GZIP_MIN_SIZE)
app.add_exception_handler(ValidationError, validation_exception_handler)


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_spec(x_api_key: Annotated[str | None, Header()] = None):
    if settings.SHOW_API_DOCS or (x_api_key == settings.SYSTEM_API_KEY):
        return get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            contact=app.contact,
            license_info=app.license_info,
            routes=app.routes,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"global": "You are not authorized to see the OpenAPI specification."},
    )


@app.get("/docs", include_in_schema=False)
async def get_api_docs(x_api_key: Annotated[str | None, Header()] = None):
    if settings.SHOW_API_DOCS or (x_api_key == settings.SYSTEM_API_KEY):
        return get_swagger_ui_html(openapi_url="/openapi.json", title=app.title)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"global": "You are not authorized to see the API docs."},
    )


app.include_router(auth_router)
app.include_router(auth_router)


@app.post("/token", response_model=Token)
async def token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db_manager: dbManager,
):
    """Authenticate user and generates an authentication token on success"""
    # load user from database
    _session: AsyncSession
    async with db_manager.get_session() as _session:
        username = form_data.username.lower()
        stmt = select(User).where((User.email == username) | (User.name == username))
        result = await _session.execute(stmt)
        user: User = result.scalars().first()

        email_verified = True

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "username": (
                        "Incorrect email or password. Please try again or"
                        " reset your password."
                    ),
                    "email": (
                        "Incorrect email or password. Please try again or"
                        " reset your password."
                    ),
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.enabled is False:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "password": (
                        "You have entered the wrong password too many times. "
                        "Please try again later use this {{LINK}} if you have forgotten your password."
                    ),
                    "disable_login": True,
                },
            )

        if user.auth_mode == AuthMode.LOCAL:
            # check user password
            valid = check_password(form_data.password, user.password)
            if not valid:
                error_message = await increment_login_attempts_and_get_error_message(
                    user=user, session=_session
                )

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_message,
                    headers={"WWW-Authenticate": "Bearer"},
                )

            iat = datetime.now()
            exp = iat + settings.JWT_EXPIRATION_DELTA
            r_exp = iat + settings.REFRESH_TOKEN_EXPIRATION_DELTA

            access_token = create_access_token(
                data=AccessTokenData(sub=user.name, iat=iat, exp=exp)
            )
            # reset failed login attempts on successful login
            user.failed_login_attempts = 0
            # set the last_access field to now
            user.last_access = datetime.now()
            # save UID for refresh token
            user.refresh_token_uid = str(uuid4())
            # save token iat for verification
            user.token_iat = datetime.fromtimestamp(
                jwt.get_unverified_claims(access_token)["iat"]
            )
            _session.add(user)
            refresh_token = create_refresh_token(
                data=RefreshTokenData(
                    sub=user.name,
                    uid=user.refresh_token_uid,
                    iat=iat,
                    exp=r_exp,
                )
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"global": "Unknown auth mode"},
            )

        user.email_verified = email_verified
        _session.add(user)
        await _session.commit()

        # block log in if email not verified
        if not email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "email": (
                        "You need to verify your email before being able to"
                        " log in. Please check your associated email for the"
                        " verification link."
                    ),
                    "email_verified": False,
                },
            )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            email_verified=email_verified,
        )


@app.post("/token/refresh", response_model=Token)
async def refresh_token(db_manager: dbManager, data: RefreshTokenRequest) -> Token:
    """
    Generate a new access token using the refresh token of a user.

    Args:
        data (RefreshTokenRequest): The request payload containing the
            refresh token

    Returns:
        Token: A new access token for the authenticated user.
    """

    _session: AsyncSession
    # LOCAL USERS
    async with db_manager.get_session() as _session:
        user = await verify_refresh_token(data.refresh_token, _session)
        # store new refresh token UID
        user.refresh_token_uid = str(uuid4())
        _session.add(user)
        await _session.commit()

        iat = datetime.now()
        exp = iat + settings.JWT_EXPIRATION_DELTA

        access_token = create_access_token(
            data=AccessTokenData(sub=user.name, iat=iat, exp=exp)
        )
        user.token_iat = datetime.fromtimestamp(
            jwt.get_unverified_claims(access_token)["iat"]
        )
        _session.add(user)
        await _session.commit()

        r_exp = iat + settings.REFRESH_TOKEN_EXPIRATION_DELTA
        refresh_token = create_refresh_token(
            data=RefreshTokenData(
                sub=user.name, uid=user.refresh_token_uid, iat=iat, exp=r_exp
            )
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            email_verified=user.email_verified,
        )


@app.exception_handler(LocalTokenVerificationError)
async def token_verification_exception_handler(
    request: Request, exc: LocalTokenVerificationError
):
    """
    Exception handler for token validation errors.
    """
    match exc.code:
        case TokenValidationErrorEnum.INVALID:
            message = "Token is invalid."
        case TokenValidationErrorEnum.INVALID_SIGNATURE:
            message = "The token signature is invalid."
        case TokenValidationErrorEnum.EXPIRED:
            message = "Token has expired."
        case TokenValidationErrorEnum.USER_NOT_FOUND:
            message = "The user corresponding to the refresh token was not found"
        case TokenValidationErrorEnum.VERIFICATION_FAILED:
            message = "Token signature verification failed."
        case _:
            message = "The token validation failed for unknown reasons."
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": {"token": message}},
    )


@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "redis_client"):  # type: ignore
        await app.state.redis_client.disconnect()  # type: ignore
