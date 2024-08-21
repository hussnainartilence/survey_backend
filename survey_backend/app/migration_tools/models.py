from datetime import datetime

from pydantic import BaseModel

from app.db.models import AuthMode, AuthRole

class WisGroupDataModel(BaseModel):
    id: int
    name: AuthRole
    description: str | None = None
    delegate_user_id: int | None = None
    delegate_group_id: int | None = None


class WisUserDataModel(BaseModel):
    id: int
    name: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    api_key: str | None = None
    enabled: bool
    password: str | None = None
    created_on: datetime = datetime.now()
    last_access: datetime | None = None
    refresh_token_uid: str | None = None
    token_iat: datetime | None = None
    auth_mode: AuthMode
    email_token: str | None = None
    token_timestamp: datetime | None = None
    data_last_accessed: datetime | None = None
    failed_login_attempts: int

    deleted: bool
    notifications: bool


class WisUserGroupDataModel(BaseModel):
    user_id: int | None = None
    group_id: int | None = None