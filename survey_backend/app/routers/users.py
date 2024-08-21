"""
Module for user public APIs which do not require authentication.
"""

import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import secrets
import uuid
from pydantic import SecretStr
from app.db.models import AuthMode, AuthRole, Group, PasswordHistory, User
from sqlalchemy.orm import selectinload
from app.dependencies import (
    RoleAuthorization,
    dbManager,
    get_current_user_from_multiple_auth,
)
from app.schemas.user import (
    UserCreate,
    UserCreateResponse,
    PaginatedUserGet,
    GroupFilter,
    UserGet,
    UserDeleteResponse,
    UserUpdateResponse,
    UserUpdate,
)
from app.utils import encrypt_password, check_password

from .utils import (
    ErrorMessage,
    is_valid_password,
    get_updated_user_name_if_same_with_mail,
    update_user_data_last_accessed,
    send_email,
    load_user,
    check_password_history,
    update_password_history,
)

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={status.HTTP_404_NOT_FOUND: {"description": "Not found."}},
)


async def update_groups_association(groups: list, user: User, session: AsyncSession):
    """
    If groups is not an empty list, iterate over it and for each group:
     - if the group does not exist, create it in the DB first
     - update the association with the new user and groups

    Parameters
    ----------
        groups - the list of groups
        user - the new user

    Returns
    -------
        The updated user
    """
    # check if groups are specified in the request body
    if groups:
        for group in groups:
            stmt = select(Group).where(Group.name == group.name)
            result = await session.execute(stmt)
            db_group = result.scalars().first()
            # create new group if group doesn't exist
            if db_group is None:
                # create new group
                db_group = Group(**group.dict())
                session.add(db_group)

            user.groups.append(db_group)
    return user


async def update_user_password(
    token: str,
    db_user: User,
    new_password: SecretStr,
    current_password: str,
    email: str | None = None,
) -> tuple[str, str | None]:
    """
    Updates the user password in the database

    Args:
        token (str): The user's token from the request.
        db_user (User): The user record from the database.
        new_password (SecretStr): The user's new password.
        current_password (str): The user's current password.
        email (str | None, optional): The user's email address, used
        Defaults to None

    Raises:
        HTTPException: 400 BAD REQUEST if passwords don't match.

    Returns:
        tuple[str, str | None]: The new  tokens if the
            user exist, `token, None,` otherwise.
    """
    if db_user.auth_mode == AuthMode.LOCAL:
        # check current password matches with stored hash
        if not check_password(pwd=current_password, hashed_pwd=db_user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"current_password": ErrorMessage.PASSWORD_DOES_NOT_MATCH},
            )
        # hash new password
        new_hashed_pass = encrypt_password(new_password.get_secret_value())
        # save new hashed password to user db
        db_user.password = new_hashed_pass

    return token, None


@router.post("/register", response_model=UserCreateResponse)
async def register_user(
    db_manager: dbManager,
    user: UserCreate,
    _=Depends(
        RoleAuthorization(
            [
                AuthRole.ADMIN,
            ]
        )
    ),
    __=Depends(get_current_user_from_multiple_auth),
) -> UserCreateResponse:
    """
    Register a new user.

    Parameters
    ----------
        user - User input data.
    Returns
    -------
        The user's details.
    """
    user.name = await get_updated_user_name_if_same_with_mail(user.name, user.email)
    _session: AsyncSession
    async with db_manager.get_session() as _session:
        db_user_by_email = await _session.scalar(
            select(User).where(User.email == user.email)
        )

        if db_user_by_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"email": "Email already in use. Try logging in instead."},
            )

        db_user_by_name = await _session.scalar(
            select(User).where(User.name == user.name)
        )

        if db_user_by_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"global": "User already exists. Try logging in instead."},
            )

    password_validation = is_valid_password(user.password, user.name, False, user.email)
    if password_validation is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"password": password_validation},
        )

    _session: AsyncSession
    async with db_manager.get_session() as _session:
        # create new user
        new_user: User = User(**user.dict(exclude={"hashed_password"}))
        new_user.auth_mode = AuthMode.LOCAL
        new_user.password = None
        new_user.email_token = secrets.token_urlsafe(32)
        new_user.token_timestamp = datetime.now()

        _session.add(new_user)

        if not new_user.groups:
            group: Group | None = None
            role = AuthRole.DATA_EXPLORER
            group = await _session.scalar(select(Group).filter_by(name=role))
            if group:
                # assign role to user
                new_user.groups.append(group)

        # Commit user to retrieve its id.
        await _session.commit()

        history_pass = encrypt_password(user.password)
        new_history_entry = PasswordHistory(
            user_id=new_user.id, encrypted_password=history_pass
        )
        _session.add(new_history_entry)

        await _session.commit()

    await send_email(
        f"its you {new_user.name} please verify", new_user.email_token, new_user.email
    )
    return new_user


@router.get("", response_model=PaginatedUserGet)
async def list_users(
    db_manager: dbManager,
    filter_by: str | None = None,
    order_by: str | None = None,
    group: GroupFilter | None = None,
    order: str = "asc",
    start: int = 0,
    limit: int = 1000,
    current_user: User = Depends(
        RoleAuthorization(
            [
                AuthRole.ADMIN,
            ],
            visible_roles=[AuthRole.ADMIN],
        )
    ),
    __=Depends(get_current_user_from_multiple_auth),
):
    """
    Return the list of all users.

    Parameters
    ----------
    filter_by - filter as dict e.g. {"name":"sample"}
    order_by - list of ordering fields e.g. ["name","id"]
    group - filter by group name
    order - default "asc", can apply "asc" and "desc"
    start - starting index for the users list
    limit - maximum number of users to return

    Returns
    -------
        a dictionary containing the list of users and pagination information
    """

    # load users
    _session: AsyncSession
    async with db_manager.get_session() as _session:
        # Update user.data_last_accessed for keeping track of inactivity
        await update_user_data_last_accessed(
            session=_session, current_user=current_user
        )

        # parse the filter_by and order_by parameters
        filter_dict = {}
        order_by_list = []
        if filter_by:
            try:
                filter_dict = json.loads(filter_by)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid filter_by format. Must be a valid JSON" " string."
                    ),
                ) from exc
        if order_by:
            try:
                order_by_list = json.loads(order_by)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid order_by format. Must be a valid JSON list of"
                        " strings."
                    ),
                ) from exc
        # load users

        query = select(User).options(selectinload(User.groups))
        # Filter by group if specified
        if group:
            query = query.join(User.groups).filter(Group.name == group)

        # apply filtering from filter_by query params
        if "name" in filter_dict:
            query = query.where(User.name.ilike(f"%{filter_dict['name']}%"))
        if "first_name" in filter_dict:
            query = query.where(User.first_name.ilike(f"%{filter_dict['first_name']}%"))
        if "last_name" in filter_dict:
            query = query.where(User.last_name.ilike(f"%{filter_dict['last_name']}%"))
        if "enabled" in filter_dict:
            try:
                enabled = filter_dict["enabled"].lower() == "true"
                query = query.where(User.enabled == enabled)
            except UnboundLocalError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid value for 'enabled'. Must be either 'true' or"
                        " 'false'."
                    ),
                ) from exc

        # order by query parameter
        for field in order_by_list:
            if field == "id":
                query = query.order_by(
                    User.id.asc() if order == "asc" else User.id.desc()
                )
            elif field == "name":
                query = query.order_by(
                    User.name.asc() if order == "asc" else User.name.desc()
                )
            elif field == "first_name":
                query = query.order_by(
                    User.first_name.asc() if order == "asc" else User.first_name.desc()
                )
            elif field == "last_name":
                query = query.order_by(
                    User.last_name.asc() if order == "asc" else User.last_name.desc()
                )
            elif field == "enabled":
                query = query.order_by(
                    User.enabled.asc() if order == "asc" else User.enabled.desc()
                )
            elif field == "created_on":
                query = query.order_by(
                    User.created_on.asc() if order == "asc" else User.created_on.desc()
                )
            elif field == "last_access":
                query = query.order_by(
                    User.last_access.asc()
                    if order == "asc"
                    else User.last_access.desc()
                )
            elif field == "email":
                query = query.order_by(
                    User.email.asc() if order == "asc" else User.email.desc()
                )

            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Invalid order_by value {field}. Must be id, name,"
                        " first_name, last_name, enabled, created_on, or"
                        " last_access"
                    ),
                )
        result = await _session.execute(query)
        records = result.scalars().all()

        # Use list comprehension to filter out records containing the prefix
        filtered_records = [
            record
            for record in records
            if not (record.email and record.email.startswith("deleted_"))
        ]

        # Get total number of records
        # pylint: disable=not-callable
        total_stmt = select(func.count()).select_from(User)
        total_result = await _session.execute(total_stmt)
        total = total_result.scalar_one()

    # Prepare response
    response = {
        "start": start,
        "end": start + len(records),
        "total": total,
        "items": filtered_records,
    }

    return response


@router.get("/current_user", response_model=UserGet)
async def get_current(
    db_manager: dbManager,
    current_user: User = Depends(get_current_user_from_multiple_auth),
):
    """
    Returns details of the current user.

    Returns
    -------
        current user data
    """
    _session: AsyncSession
    async with db_manager.get_session() as _session:
        # Update user.data_last_accessed for keeping track of inactivity
        await update_user_data_last_accessed(
            session=_session, current_user=current_user
        )
        # load current user
        user = await load_user(current_user.id, _session)

        return user


@router.get("/{user_id}", response_model=UserGet)
async def get_user(
    user_id: int,
    db_manager: dbManager,
    current_user: User = Depends(
        RoleAuthorization(
            [
                AuthRole.ADMIN,
            ],
            visible_roles=[AuthRole.ADMIN],
        )
    ),
    _: User = Depends(get_current_user_from_multiple_auth),
):
    """
    Return the details of a user

    Parameters
    ----------
        user_id - user identifier
    Returns
    -------
        user data
    """

    async with db_manager.get_session() as _session:
        # Update user.data_last_accessed for keeping track of inactivity
        await update_user_data_last_accessed(
            session=_session, current_user=current_user
        )
        user_data = await load_user(user_id, _session)

        return user_data


@router.delete("/{user_id}", response_model=UserDeleteResponse)
async def delete_user(
    db_manager: dbManager,
    user_id: int,
    current_user: User = Depends(
        RoleAuthorization(
            [
                AuthRole.ADMIN,
            ],
            visible_roles=[AuthRole.ADMIN],
        )
    ),
    _: User = Depends(get_current_user_from_multiple_auth),
):
    """
    Delete a user  delete all personal data from the user in our database

    Parameters
    ----------
    user_id: ID of the user to be deleted

    Returns
    -------
    The ID of the deleted user
    """
    _session: AsyncSession
    async with db_manager.get_session() as _session:
        # Update user.data_last_accessed for keeping track of inactivity
        await update_user_data_last_accessed(
            session=_session, current_user=current_user
        )

        db_user = await load_user(user_id, _session)
        # Begin replacing sensitive user data with generic data
        deleted_value = lambda: f"deleted_{str(uuid.uuid4())[:24]}"
        db_user.first_name = deleted_value()
        db_user.last_name = deleted_value()
        db_user.email = deleted_value()
        db_user.name = deleted_value()
        db_user.password = deleted_value()
        db_user.api_key = deleted_value()
        # Set the user to disabled
        db_user.enabled = False
        db_user.deleted = True
        # Update the user in the database
        _session.add(db_user)
        await _session.commit()
        # Return the updated deleted user info
        response_data: dict[str, int | bool] = {
            "id": db_user.id,
            "deleted": db_user.deleted,
        }
        return response_data


@router.patch("/{user_id}", response_model=UserUpdateResponse)
async def update_user(
    request: Request,
    user_id: int,
    user_data: UserUpdate,
    db_manager: dbManager,
    current_user: User = Depends(
        RoleAuthorization([AuthRole.ADMIN], visible_roles=[AuthRole.ADMIN])
    ),
    _: User = Depends(get_current_user_from_multiple_auth),
):
    """
    Update an existing user

    Parameters
    ----------
        user_id - identifier of the user we want to update
        user_data - user input data
    Returns
    -------
        the updated user
    """
    _session: AsyncSession
    if user_data.email is not None and current_user.groups:
        if current_user.groups[0].name == AuthRole.DATA_EXPLORER:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "user": (
                        f"User {current_user.name} is not allowed to update"
                        " user email"
                    )
                },
            )
    # If user is not requesting itself it needs to be an ADMIN.
    if current_user and current_user.id != user_id:
        await RoleAuthorization([AuthRole.ADMIN]).check_user_roles(
            db_manager=db_manager, request=request
        )

    # get token for email and password change
    _, token = request.headers["authorization"].split()
    refresh_token = None

    # load the existing user from the DB
    async with db_manager.get_session() as _session:
        # Update user.data_last_accessed for keeping track of inactivity
        await update_user_data_last_accessed(
            session=_session, current_user=current_user
        )
        db_user = await load_user(user_id, _session)

    # update user, groups and associations
    groups = []
    if db_user.auth_mode == AuthMode.LOCAL:
        # check current password matches with stored hash

        if user_data.current_password is not None:
            if not check_password(
                pwd=user_data.current_password, hashed_pwd=db_user.password
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "password": "Incorrect password. Please try again or reset your password."
                    },
                )
    if user_data.groups:
        if AuthRole.ADMIN not in [g.name for g in current_user.groups]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"user": "Only admin users are allowed to edit user groups."},
            )
        groups = list(user_data.groups)
        user_data.groups = []
        if groups:
            async with db_manager.get_session() as _session:
                db_user = await update_groups_association(groups, db_user, _session)

    # update password
    if user_data.current_password and user_data.new_password:
        # validate password complexity
        password_validation_error = is_valid_password(
            user_data.new_password.get_secret_value(),
            db_user.name,
            False,
            db_user.email,
        )

        if password_validation_error is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"new_password": password_validation_error},
            )

        # check that the new password doesn't match any of the previous ones
        async with db_manager.get_session() as _session:
            await check_password_history(
                user_id=user_id,
                new_password=user_data.new_password.get_secret_value(),
                session=_session,
            )

        token, refresh_token = await update_user_password(
            token=token,
            db_user=db_user,
            new_password=user_data.new_password,
            current_password=user_data.current_password,
            email=db_user.email,
        )
        # update user password history with hashed new password
        async with db_manager.get_session() as _session:
            await update_password_history(
                user_id=user_id,
                new_password=user_data.new_password.get_secret_value(),
                session=_session,
            )

    # set new values for user from update data
    user_update = user_data.dict(exclude_unset=True, exclude={"groups"})

    for key, value in user_update.items():
        setattr(db_user, key, value)
    # update user in DB
    async with db_manager.get_session() as _session:
        _session.add(db_user)
        await _session.commit()

    # set user response + tokens and lei
    user_update_response = UserGet.from_orm(db_user).dict() | {
        "token": token,
        "refresh_token": refresh_token,
    }

    return UserUpdateResponse(**user_update_response)


@router.get("/email/verification")
async def verify_user(db_manager: dbManager, email: str, token: str):
    _session: AsyncSession
    async with db_manager.get_session() as _session:
        result = await _session.execute(
            select(User)
            .where(User.email == email)
            .where(User.email_token == token)
            .options(selectinload(User.groups))
        )
        user = result.scalars().first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "User not found"},
            )

        elif user.email_verified is False:
            user.email_verified = True
            _session.add(user)

            await _session.commit()

    # Add your verification logic here
    return {"message": "Verification successful"}
