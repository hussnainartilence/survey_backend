""" Group schemas """
from pydantic import BaseModel


# pylint: disable = too-few-public-methods, unsupported-binary-operation


class GroupBase(BaseModel):
    """
    Base schema for Group
    """

    name: str
    description: str | None
    delegate_user_id: int | None
    delegate_group_id: int | None


class GroupCreate(GroupBase):
    """
    Create schema for Group
    """


class GroupGet(GroupBase):
    """
    Group schema
    """

    id: int

    class Config:
        """
        Schema configuration
        """

        orm_mode = True


class GroupUpdate(BaseModel):
    """
    Update schema for Group view
    """

    name: str | None
    description: str | None
    delegate_user_id: int | None
    delegate_group_id: int | None


class UserGroupResponse(BaseModel):
    """
    User group response
    """

    success: bool
