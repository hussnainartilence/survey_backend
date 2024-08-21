""" Test main package """


import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuthRole, Group, User
from app.utils import encrypt_password


class TestMain:
    """
    Unit tests for main APIs
    """

    user_name: str = "testuser"
    user_pass: str = "T3stpassw0rd"
    user_email: str = "test@mail.com"

    @pytest.mark.asyncio
    async def test_get_token(self, client: AsyncClient, session: AsyncSession):
        """
        Test "Get Token" API
        """
        # create test user
        encrypted_pwd = encrypt_password(self.user_pass)
        user = User(name=self.user_name, password=encrypted_pwd)
        session.add(user)
        await session.commit()

        # request a token for user
        response = await client.post(
            "/token",
            data={"username": self.user_name, "password": self.user_pass},
        )

        assert response.status_code == 200, response.text
        j_resp = response.json()
        assert j_resp["access_token"]
        assert j_resp["refresh_token"]
        assert j_resp["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_token_local(
        self, client: AsyncClient, session: AsyncSession
    ):
        """
        Test refresh token API for local users.
        """
        # arrange
        # create test user
        encrypted_pwd = encrypt_password(self.user_pass)
        user = User(name=self.user_name, password=encrypted_pwd)
        group = Group(name=AuthRole.DATA_EXPLORER)
        session.add(group)
        await session.flush()
        user.groups.append(group)
        session.add(user)
        await session.commit()

        # request a token for user
        login = await client.post(
            "/token",
            data={"username": self.user_name, "password": self.user_pass},
        )

        assert login.status_code == 200, login.text
        j_resp = login.json()
        assert j_resp["access_token"]
        assert j_resp["refresh_token"]
        assert j_resp["token_type"] == "bearer"

        refresh_token = j_resp["refresh_token"]

        # act
        refresh = await client.post(
            url="/token/refresh", json={"refresh_token": refresh_token}
        )

        # assert
        assert refresh.status_code == status.HTTP_200_OK, refresh.text
        j_resp = refresh.json()
        assert j_resp["access_token"]
        assert j_resp["refresh_token"]
        assert j_resp["token_type"] == "bearer"

   