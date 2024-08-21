""" User schemas """

from datetime import datetime
from enum import Enum
from typing import List

from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field, SecretStr

from app.db.models import AuthMode, AuthRole

from . import group

# pylint: disable = too-few-public-methods, unsupported-binary-operation


class UserBase(BaseModel):
    """
    Base schema for User
    """

    name: str
    first_name: str | None
    last_name: str | None


class UserCreate(UserBase):
    """
    Create schema for User
    """

    email: EmailStr
    password: str
    hashed_password: str = Field(alias="password", default=None)

class UserIdOnly(BaseModel):
    """
    User schema for returning ID only.
    """

    id: int
    class Config:
        """
        Schema configuration.
        """

        orm_mode = True

class UserCreateResponse(BaseModel):
    """
    Create schema for User response
    """

    id: int
    message: str = "User created successfully please check your email addresss to verify your account."
    class Config:
        """
        Schema configuration.
        """

        orm_mode = True




class UserGet(UserBase, UserIdOnly):
    """
    User schema
    """

    email: str | None
    enabled: bool = False
    created_on: datetime = datetime.now()
    last_access: datetime | None
    data_last_accessed: datetime | None
    groups: list[group.GroupGet]
    auth_mode: AuthMode = AuthMode.LOCAL


class PaginatedUserGet(BaseModel):
    """
    User schema
    """

    start: int
    end: int
    total: int
    items: List[UserGet]


class GroupFilter(str, Enum):
    admin = AuthRole.ADMIN.value
    data_explorer = AuthRole.DATA_EXPLORER.value

class UserLoginDataModel(BaseModel):
    """
    User login schema
    """

    username: str = ""
    email: EmailStr = EmailStr("")
    password: str


class UserUpdate(BaseModel):
    """
    Update schema for User
    """

    name: str | None
    email: EmailStr | None
    enabled: bool | None
    current_password: str | None
    new_password: SecretStr | None
    groups: list[group.GroupBase] | None


class UserApiCreateResponse(BaseModel):
    """
    Create API user response
    """

    id: int
    auth_mode: AuthMode
    external_user_id: str


class UserStandalone(UserIdOnly):
    """
    User schema for standalone api.
    """

    name: str
    first_name: str
    last_name: str
    enabled: bool


class UserPublisherRequest(BaseModel):
    """
    Schema for request payload in request-publisher-access endpoint
    """

    role: str | None
    linkedin_link: AnyHttpUrl | None
    company_lei: str
    company_type: str | None
    company_website: AnyHttpUrl | None


class UserApiKeyUpdate(BaseModel):
    """
    Update schema for User api_key
    """

    access_key: str | None


class UserListResponse(BaseModel):
    items: List[UserGet]
    total: int


class UserDeleteResponse(BaseModel):
    """
    Schema for response after deleting a user
    """

    id: int
    deleted: bool


class UserUpdateResponse(UserGet):
    """
    Schema for reponse of update user API.
    """

    token: str
    refresh_token: str | None


class NotificationSignupResponse(BaseModel):
    """
    Response Schema for Notification Sign up API
    """

    user_id: int
    notifications: bool


class UserAdminGrant(BaseModel):
    """
    UserAdminGrant schema for update role
    """

    email: EmailStr


class UserAdminGrantResponse(BaseModel):
    """
    UserAdminGrant schema for update role response
    """

    user_id: list[int] = []
    role: str | None


class AdminRevokeRequest(BaseModel):
    """
    AdminRevokeRequest schema for revoke
    """

    user_id: list[int] = []


class AdminRevokeResponse(BaseModel):
    """
    AdminRevokeResponse schema for revoke
    """

    success: bool | None


class ApiKeyResponse(BaseModel):
    """
    ApiKeyResponse schema for api key
    """

    api_key_success: str


class PaginatedUserGet(BaseModel):
    """
    User schema
    """

    start: int
    end: int
    total: int
    items: List[UserGet]


class GroupFilter(str, Enum):
    admin = AuthRole.ADMIN.value
    data_explorer = AuthRole.DATA_EXPLORER.value
