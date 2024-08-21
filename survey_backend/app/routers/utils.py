"""Utility functions for routers"""

import re
import ssl
from datetime import datetime
from enum import Enum
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from fastapi import Depends, HTTPException, status
from email.mime.base import MIMEBase
from email import encoders
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload
from app import settings

from ..db.models import (
    Group,
    PasswordHistory,
    Permission,
    User,
)
from ..dependencies import get_current_user

from ..utils import check_password, encrypt_password



# pylint: disable = unsupported-binary-operation, not-callable


class ErrorMessage(str, Enum):
    """
    Error messages.
    """

    DUPLICATED_ATTRIBUTE = "Duplicated attribute."
    GROUP_NOT_FOUND_MESSAGE = "Group not found."
    PERMISSION_NOT_FOUND_MESSAGE = "Permission not found."
    USER_NOT_FOUND_MESSAGE = "User not found."
    USER_DOES_NOT_HAVE_PERMISSION = (
        "User does not have permission to perform this operation."
    )
    EMAIL_ADDRESS_REQUIRED = "Email address is required."
    EMAIL_DOES_NOT_BELONG_TO_FIREBASE_USER = (
        "The provided email address does not belong to any Firebase user."
    )
    PASSWORD_DOES_NOT_MATCH = (
        "The current password does not match with the password from the"
        " database."
    )
    NOT_ALLOWED = "You don't have permission for this action."






async def load_group(group_id: int, session: AsyncSession) -> Group:
    """
    Given a group ID, returns the corresponding record from the DB

    Parameters
    ----------
        group_id - group identifier
    Returns
    -------
        group data
    """
    # load group
    result = await session.execute(select(Group).where(Group.id == group_id))
    group = result.scalars().first()
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"group_id": ErrorMessage.GROUP_NOT_FOUND_MESSAGE},
        )

    return group


async def load_permission(
    permission_id: int, session: AsyncSession
) -> Permission:
    """
    Given a permission ID, returns the corresponding record from the DB

    Parameters
    ----------
        permission_id - permission identifier
    Returns
    -------
        permission data
    """
    # load permission
    result = await session.execute(
        select(Permission).where(Permission.id == permission_id)
    )
    permission = result.scalars().first()
    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "permission_id": ErrorMessage.PERMISSION_NOT_FOUND_MESSAGE
            },
        )

    return permission



async def load_user(user_id: int, session: AsyncSession):
    """
    Given a user ID, returns the corresponding record from the DB

    Parameters
    ----------
        user_id - user identifier
    Returns
    -------
        user data
    """
    # load user
    result = await session.execute(
        select(User)
        .options(selectinload(User.groups))
        .where(User.id == user_id)
    )
    user = result.scalars().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"user_id": ErrorMessage.USER_NOT_FOUND_MESSAGE},
        )

    return user


def get_url_from_session(session: AsyncSession):
    """
    Get currently used engine url

    Parameters
    ----------
    session - database session

    Returns
    -------
    current engine url
    """
    return session.get_bind().engine.url


def get_engine_from_session(session: AsyncSession):
    """
    Get currently used engine

    Parameters
    ----------
    session - database session

    Returns
    -------
    current engine
    """
    # get currently used engine url
    engine_url = get_url_from_session(session)
    # create engine
    engine = create_async_engine(engine_url)

    return engine


async def check_admin_access_rights(session: AsyncSession, current_user):
    """
    Checks if the current user has administrative access rights.
    """

    access_manager = AccessManager(session)
    is_admin = access_manager.is_admin(user=current_user)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"global": ErrorMessage.USER_DOES_NOT_HAVE_PERMISSION},
        )


async def check_access_rights(
    session: AsyncSession, entity, user, access_type, error_message
):
    """
    Checks if the current user has access rights to perform operation.
    """

    access_manager = AccessManager(session)
    granted = await access_manager.can_read_write(
        entity=entity, user=user, access_type=access_type
    )
    if not granted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message,
        )


async def update_user_data_last_accessed(
    session: AsyncSession, current_user: User = Depends(get_current_user)
):
    """
    Updates current user's "data_last_accessed" obj
    :param current_user: current user
    :return: the updated current user
    """
    if current_user is None:
        return None
    else:
        current_user.data_last_accessed = datetime.now()
        session.add(current_user)
        await session.commit()
    return current_user.data_last_accessed



async def user_existence(user_email: str, session: AsyncSession):
    """
    Given a user ID, returns the corresponding record from the DB

    Parameters
    ----------
        user_id - user identifier
    Returns
    -------
        user data
    """
    # load user
    result = await session.execute(
        select(User)
        .options(selectinload(User.groups))
        .where(User.email == user_email)
    )
    user = result.scalars().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"user_id": ErrorMessage.USER_NOT_FOUND_MESSAGE},
        )

    return user




def is_valid_password(password, username, is_level2=False, email=None):
    """
    Validates a password according to specific rules and returns an error message if it's invalid.

    Args:
    - password: The password to validate.
    - username: The username associated with the account.
    - is_level2: True for Level 2 accounts, False for Level 1 accounts.

    Returns:
    - If the password is valid, returns None.
    - If the password is invalid, returns an error message describing the issue.
    """

    # Check if the password is at least 12 characters long
    if len(password) < 12:
        return "Password must be at least 12 characters long."

    # Check if the password is the same as the username
    if password == username:
        return "Password must not be the same as the username."

    if password == email:
        return "Password must not be the same as the email."

    # # Define patterns that should not be present in the password
    # prohibited_patterns = [
    #     r"(\w)\1{2,}",  # Three or more consecutive repeated characters
    #     r"q[weerty]+|w[qwerty]+|e[qwerty]+|r[qwerty]+|t[qwerty]+|y[qwerty]+",  # Simple keyboard patterns
    #     r"z[xcvbnmas]+|x[zcvbnmas]+|c[xcvbnmas]+|v[xcvbnmas]+|b[xcvbnmas]+|n[xcvbnmas]+|m[xcvbnmas]+",  # Simple keyboard patterns
    #     r"(\d)\1{2,}",  # Three or more consecutive repeated digits
    # ]

    # # Check if the password contains prohibited patterns
    # for pattern in prohibited_patterns:
    #     if re.search(pattern, password, re.IGNORECASE):
    #         return "Password contains prohibited patterns."

    # Check if the password contains at least 2 of the following character classes (Level 1)
    # or at least 3 of the following character classes (Level 2)
    character_classes = 0
    if re.search(r"[A-Z]", password):
        character_classes += 1
    if re.search(r"[a-z]", password):
        character_classes += 1
    if re.search(r"\d", password):
        character_classes += 1
    if re.search(r'[!@#\$%^&*(),.?":{}|<>]', password):
        character_classes += 1

    if is_level2:
        if character_classes < 3:
            return (
                "Password should contain two of the following: "
                "uppercase letter, lowercase letter, "
                "number or punctuation marks."
            )
    else:
        if character_classes < 2:
            return (
                "Password should contain two of the following: "
                "uppercase letter, lowercase letter, "
                "number or punctuation marks."
            )

    # If none of the validation rules triggered, the password is valid
    return None


async def retrieve_user_password_history(user_id: int, session: AsyncSession):
    history_query = (
        select(PasswordHistory)
        .filter_by(user_id=user_id)
        .order_by(desc(PasswordHistory.created_on))
        .limit(5)
    )
    password_history = await session.execute(history_query)
    password_history_list = password_history.scalars().all()

    return password_history_list


async def check_password_history(
    user_id: int, new_password: str, session: AsyncSession
):
    password_history_list = await retrieve_user_password_history(
        user_id, session
    )

    # Check if the new password matches any of the recent passwords.
    for history_entry in password_history_list:
        if check_password(new_password, history_entry.encrypted_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "new_password": (
                        "The new password you entered is the same as one of"
                        " your previous five passwords. Please enter a"
                        " different password."
                    )
                },
            )


async def update_password_history(
    user_id: int, new_password: str, session: AsyncSession
):
    password_history_list = await retrieve_user_password_history(
        user_id, session
    )

    # If the password history is already at the maximum limit, replace
    # the oldest entry
    if len(password_history_list) >= 5:
        oldest_password_entry = min(
            password_history_list, key=lambda entry: entry.created_on
        )
        await session.delete(oldest_password_entry)
    # hash new password
    new_hashed_pass = encrypt_password(new_password)
    # Add the new password to the history
    new_history_entry = PasswordHistory(
        user_id=user_id, encrypted_password=new_hashed_pass
    )
    session.add(new_history_entry)

    await session.commit()


async def get_updated_user_name_if_same_with_mail(name: str, email: str):
    """
    return split name if same as email
    """

    if name == email:
        return email.split("@")[0]
    return name


async def send_email(subject, verification_token, email):
    try:
        print("sendings email")
        sender_email = settings.EMAIL_FROM
        print("Sender email", sender_email)
        password = settings.EMAIL_PASS
        # for email in receiver_emails:
        # Create a multipart message and set headers
        print(f"Sending email to {email}")
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = ', '.join(email)
        message["Subject"] = subject
        # Recommended for mass emails
        # message["Bcc"] = "any_mail"
        body = f"Click the following link to verify your email: http://127.0.0.1:8000/users/verify?email={email}&token={verification_token}"

        # Add body to email
        message.attach(MIMEText(body, "plain"))

        text = message.as_string()

        # Log in to server using secure context and send email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, email, text)
            print(f"Email Send : {email}")
    except Exception as e:
        print(f'Exception as {e}')


async def time_difference(saved_time):

    end_time = datetime.now()  # Example end time (current time)

    # Calculate the time difference
    time_difference = end_time - saved_time

    # Return the time difference
    return(time_difference)

