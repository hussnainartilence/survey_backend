"""Database models"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from .database import Base


class AuthMode(str, Enum):
    """
    Authorization modes
    """

    LOCAL = "LOCAL"
    FIREBASE = "FIREBASE"


class AuthRole(str, Enum):
    """
    Authorization roles
    """

    ADMIN = "admin"
    DATA_EXPLORER = "data_explorer"


# many-to-many relationship between users and groups
user_group = Table(
    "wis_user_group",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("wis_user.id")),
    Column("group_id", Integer, ForeignKey("wis_group.id")),
    UniqueConstraint("user_id", "group_id", name="uq_user_group"),
)


class Group(Base):
    """
    Group model
    """

    __tablename__ = "wis_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[AuthRole] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    delegate_user_id: Mapped[int | None] = mapped_column(Integer)
    delegate_group_id: Mapped[int | None] = mapped_column(Integer)
    permissions = relationship(
        "Permission",
        lazy="select",
        backref=backref("permission_group", lazy="joined"),
    )

    def __repr__(self):
        return f"<Group {self.name}>"


class PasswordHistory(Base):
    """
    Table holding a user's five most recent passwords
    """

    __tablename__ = "wis_password_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer)
    encrypted_password: Mapped[str | None] = mapped_column(String(256))
    created_on: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    def __repr__(self):
        return f"<PasswordHistory {self.id}>"


class User(Base):
    """
    User account model
    """

    __tablename__ = "wis_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(256))
    email_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    api_key: Mapped[str | None] = mapped_column(String(256), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    password: Mapped[str | None] = mapped_column(String(256))
    created_on: Mapped[datetime] = mapped_column(default=datetime.now)
    last_access: Mapped[datetime | None] = mapped_column(DateTime)
    refresh_token_uid: Mapped[str | None] = mapped_column(default=str(uuid4()))
    token_iat: Mapped[datetime] = mapped_column(nullable=True)
    auth_mode: Mapped[str] = mapped_column(default=AuthMode.LOCAL.value)
    external_user_id: Mapped[str] = mapped_column(String(128), nullable=True)
    email_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    token_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    groups: Mapped[list[Group]] = relationship(
        "Group",
        lazy="select",
        secondary=user_group,
        backref=backref("users", lazy="joined"),
    )
    requests = relationship("UserPublisherRequest")
    data_last_accessed: Mapped[datetime | None] = mapped_column(default=datetime.now())
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)

    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    notifications: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self):
        return (
            f"<User {self.name}"
            f" email={self.email}"
            f" email_verified={self.email_verified}"
            f" first_name={self.first_name}"
            f" last_name={self.last_name}"
            f" enabled={self.enabled}"
            f" auth_mode={self.auth_mode}>"
        )


class Permission(Base):
    """
    Represent a permission for a user to access a resource
    """

    __tablename__ = "wis_permission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    set_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("wis_user.id"))
    group_id: Mapped[int | None] = mapped_column(ForeignKey("wis_group.id"))
    grant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    list: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    write: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Permission {self.id}>"


class UserPublisherStatusEnum(str, Enum):
    """
    Enum for user request status.
    """

    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"


class UserPublisherRequest(Base):
    """
    Table holding requests that users make (e.g. more privileges)
    """

    __tablename__ = "wis_user_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wis_user.id"), nullable=False
    )
    role: Mapped[str | None] = mapped_column(String)
    status: Mapped[UserPublisherStatusEnum] = mapped_column(
        nullable=False, default=UserPublisherStatusEnum.REQUESTED.value
    )
    linkedin_link: Mapped[str | None] = mapped_column(String)
    company_lei: Mapped[str] = mapped_column(String, nullable=False)
    company_type: Mapped[str | None] = mapped_column(String)
    company_website: Mapped[str | None] = mapped_column(String)


class Module(Base):
    """Module _summary_

    :param _type_ Base: _description_
    """

    __tablename__ = "wis_module"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("wis_user.id"))
    module_name: Mapped[str | None] = mapped_column(String)


class Values(str, Enum):
    """
    values of sme
    """

    GREATER_THEN_FIVE_NEGATIVE = "BY > 5%"
    BETWEEN_TWO_TO_FIVE_NEGATIVE = "BY 2-5%"
    BETWEEN_ZERO_TO_FIVE_NEGATIVE = "BY 0-5%"
    FLATE_SHARE = "FLATE_SHARE"
    BETWEEN_ZERO_TO_FIVE = " BY 0-5%"
    BETWEEN_TWO_TO_FIVE = " BY 2-5%"
    GREATER_THEN_FIVE = "BY > 5%"


class SME(Base):
    """SME _summary_

    :param _type_ Base: _description_
    """

    __tablename__ = "wis_sme"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    module_id: Mapped[int] = mapped_column(ForeignKey("wis_module.id"))
    heading: Mapped[str] = mapped_column(String)
    question: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String)
    selected_value: Mapped[int | None] = mapped_column(Integer)


class Startups(Base):
    """Startups _summary_

    :param _type_ Base: _description_
    """

    __tablename__ = "wis_startups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    module_id: Mapped[int] = mapped_column(ForeignKey("wis_module.id"))
    question: Mapped[str | None] = mapped_column(String)
    option_1: Mapped[str | None] = mapped_column(String)
    option_2: Mapped[str | None] = mapped_column(String)
    option_3: Mapped[str | None] = mapped_column(String)
    selected_option: Mapped[int | None] = mapped_column(Integer, default=0)


class CurrentStrategy(Base):
    """
    Table holding current strategy
    """

    __tablename__ = "wis_current_strategy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    module_id: Mapped[int] = mapped_column(ForeignKey("wis_module.id"))
    question: Mapped[str] = mapped_column(String)


class CurrentStrategyValue(Base):
    """
    Table holding current strategy
    """

    __tablename__ = "wis_current_strategy_value"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("wis_current_strategy.id"))
    strategy: Mapped[str] = mapped_column(String)


class CurrentSituation(Base):
    """Current Situation _summary_

    :param _type_ Base: _description_
    """

    __tablename__ = "wis_current_situation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    module_id: Mapped[int] = mapped_column(ForeignKey("wis_module.id"))
    heading: Mapped[str] = mapped_column(String)
    sub_heading: Mapped[str] = mapped_column(String)
    level_values: Mapped[str] = mapped_column(String)
    selected_value: Mapped[int | None] = mapped_column(Integer)
    descriptions: Mapped[str | None] = mapped_column(String)
