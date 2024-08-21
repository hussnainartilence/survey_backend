"""CLI commands for database management"""

import asyncio

import typer
from alembic import config
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from typing_extensions import Annotated

from app import settings
from app.db import models
from app.db.database import DBManager
from app.db.models import (
    AuthRole,
    Group,
    User,
    Module,
    SME,
    Startups,
    CurrentStrategy,
    CurrentSituation,
)
from app.routers.utils import get_engine_from_session
from app.utils import encrypt_password
from cli.manage_forms import async_create

# create CLI app
app = typer.Typer()


async def async_create_groups_and_vault() -> None:
    """
    Asynchronous create_groups_and_vault.
    """

    db_manager = DBManager()
    async with db_manager.get_session() as session:
        # create default roles
        groups = [
            Group(name=AuthRole.ADMIN, description="Administrators"),
            Group(name=AuthRole.DATA_EXPLORER, description="Data explorers"),
        ]
        session.add_all(groups)

        await session.commit()


async def async_create_modules(names: list) -> None:
    """
    Asynchronous create_modules.
    """

    db_manager = DBManager()
    async with db_manager.get_session() as session:
        # create default roles
        for name in names:
            new_module = Module(user_id=1, module_name=name)
            session.add(new_module)

        await session.commit()


async def async_create_current_strategy(module_id: int, question: str) -> None:
    """
    Asynchronous create_modules.
    """

    db_manager = DBManager()
    async with db_manager.get_session() as session:
        # create default roles
        new_strategy = CurrentStrategy(module_id=module_id, question=question)
        session.add(new_strategy)

        await session.commit()


async def async_create_sme() -> None:
    """
    Asynchronous create_sme.
    """

    data = [
        {
            "module_id": 1,
            "heading": "CONSUMER VALUE",
            "question": "Has your company's market share grown in the last 12 months (L12M) in your country/region?",
            "values": "BY > 5%,By 2-5%,By 0-5%,FLAT SHARE,By 0-5%,By 2-5%,BY > 5%",
        },
        {
            "module_id": 1,
            "heading": "CONSUMER VALUE",
            "question": "Are you winning versus your key competition? (Your company share vs key competition in L12M",
            "values": "BY > 5%,By 2-5%,By 0-5%,FLAT SHARE,By 0-5%,By 2-5%,BY > 5%",
        },
        {
            "module_id": 1,
            "heading": "COSTUMER VALUE",
            "question": "Have you grown share with your key customers in the last 12 months?",
            "values": "BY > 5%,By 2-5%,By 0-5%,FLAT SHARE,By 0-5%,By 2-5%,BY > 5%",
        },
        {
            "module_id": 1,
            "heading": "COSTUMER VALUE",
            "question": "Is your company out performing your key competition at your top customers? (Sales versus your competition in L1M2)",
            "values": "BY > 5%,By 2-5%,By 0-5%,FLAT SHARE,By 0-5%,By 2-5%,BY > 5%",
        },
        {
            "module_id": 1,
            "heading": "COMPANY/SHAREHOLDERS VALUE",
            "question": "Have your company or divisions profits grown versus a year ago?",
            "values": "BY > 5%,By 2-5%,By 0-5%,FLAT SHARE,By 0-5%,By 2-5%,BY > 5%",
        },
        {
            "module_id": 1,
            "heading": "COMPANY/SHAREHOLDERS VALUE",
            "question": "Is your company or divisions profit growth higher than key competition? (Growth gap versus key competitor)",
            "values": "BY > 5%,By 2-5%,By 0-5%,FLAT SHARE,By 0-5%,By 2-5%,BY > 5%",
        },
    ]

    db_manager = DBManager()
    async with db_manager.get_session() as session:
        # create default roles
        for sme_data in data:
            new_sme = SME(
                module_id=sme_data["module_id"],
                heading=sme_data["heading"],
                question=sme_data["question"],
                value=sme_data["values"],
            )

            session.add(new_sme)

        await session.commit()


async def async_create_situation() -> None:
    """
    Asynchronous create_situation.
    """
    data = [
        {
            "module_id": 4,
            "heading": "Differentiation",
            "sub_heading": "Brand Equity",
            "level_values": "Competitive Disadvantage,Parity,Competitive Advantage",
        },
        {
            "module_id": 4,
            "heading": "Differentiation",
            "sub_heading": "Technology",
            "level_values": "Competitive Disadvantage,Parity,Competitive Advantage",
        },
        {
            "module_id": 4,
            "heading": "Differentiation",
            "sub_heading": "Go to Market",
            "level_values": "Competitive Disadvantage,Parity,Competitive Advantage",
        },
        {
            "module_id": 4,
            "heading": "Differentiation",
            "sub_heading": "Target Market",
            "level_values": "Competitive Disadvantage,Parity,Competitive Advantage",
        },
        {
            "module_id": 5,
            "heading": "Cost",
            "sub_heading": "Technology",
            "level_values": "Competitive Disadvantage,Parity,Competitive Advantage",
        },
        {
            "module_id": 5,
            "heading": "Cost",
            "sub_heading": "Scale",
            "level_values": "Competitive Disadvantage,Parity,Competitive Advantage",
        },
        {
            "module_id": 5,
            "heading": "Cost",
            "sub_heading": "Sourcing/Supply Chain",
            "level_values": "Competitive Disadvantage,Parity,Competitive Advantage",
        },
        {
            "module_id": 5,
            "heading": "Cost",
            "sub_heading": "Operating Efficiency",
            "level_values": "Competitive Disadvantage,Parity,Competitive Advantage",
        },
        {
            "module_id": 5,
            "heading": "Cost",
            "sub_heading": "Others (Specify",
            "level_values": "Competitive Disadvantage,Parity,Competitive Advantage",
        },
        {
            "module_id": 6,
            "heading": "Operating Efficiency",
            "sub_heading": "Capability",
            "level_values": "Week,Average,Strong",
        },
        {
            "module_id": 6,
            "heading": "Operating Efficiency",
            "sub_heading": "Corporate Structure",
            "level_values": "Week,Average,Strong",
        },
        {
            "module_id": 6,
            "heading": "Operating Efficiency",
            "sub_heading": "Governance",
            "level_values": "Week,Average,Strong",
        },
        {
            "module_id": 6,
            "heading": "Operating Efficiency",
            "sub_heading": "Decision Making",
            "level_values": "Week,Average,Strong",
        },
        {
            "module_id": 6,
            "heading": "Operating Efficiency",
            "sub_heading": "Processes/Systems",
            "level_values": "Week,Average,Strong",
        },
        {
            "module_id": 6,
            "heading": "Operating Efficiency",
            "sub_heading": "Speed to market",
            "level_values": "Week,Average,Strong",
        },
        {
            "module_id": 6,
            "heading": "Operating Efficiency",
            "sub_heading": "Others (Specify",
            "level_values": "Week,Average,Strong",
        },
    ]

    db_manager = DBManager()
    async with db_manager.get_session() as session:
        # create default roles
        for situation_data in data:
            new_sme = CurrentSituation(
                module_id=situation_data["module_id"],
                heading=situation_data["heading"],
                sub_heading=situation_data["sub_heading"],
                level_values=situation_data["level_values"],
            )

            session.add(new_sme)

        await session.commit()


async def async_create_startup() -> None:
    """
    Asynchronous create_startup.
    """
    data = {
        "module_id": 2,
        "data": [
            {
                "question": "How well does your product or service meet the needs of your target customers compared to the competition?",
                "option_1": "Significantly better than competition: we have clear, validated proof of superior customer satisfaction",
                "option_2": "Better than competition; some validation but room for improvement",
                "option_3": "Comparable or worse than competition; limited or no validation",
            },
            {
                "question": "How do you create value for your customers?",
                "option_1": "We solve a critical problem or fulfil an essential need with a unique solution",
                "option_2": "we provide a useru solution that imoroves uoon existing ootyns",
                "option_3": "Our value proposition is not clearly differentiated from comoetitors",
            },
            {
                "question": "How do you make money and grow margins?",
                "option_1": "Clear and profitable business model with multiple revenue streams and high margin crowth potential",
                "option_2": "Glear ousiness mode wth a solid olan tor revenue and margin Growin",
                "option_3": "Unclear or unproven business model with uncertain marain growth",
            },
            {
                "question": "What is your competitive advantage?",
                "option_1": "Strong, defensible competitive advantage (ea. proprietary technology, strona brand, unique partnerships)",
                "option_2": "Some competitive advantages, but potentially replicable by competitors",
                "option_3": "Weak or no competitive advantaae",
            },
            {
                "question": "Do you have the funding necessary to achieve your next major milestones, and how long will it last?",
                "option_1": "Yes. fullv furdied for the rext 184 months",
                "option_2": "Yes but only for the next 6-18 months",
                "option_3": "No. funding is insufficient or uncertain for the next 6 months",
            },
            {
                "question": "How scalable is your business model?",
                "option_1": "Highly scalable with clear pathways to scale quickly and efficiently",
                "option_2": "Moderately scalable with some potential obstacles",
                "option_3": "Limited scalability due to inherent business model constraints",
            },
        ],
    }

    db_manager = DBManager()
    async with db_manager.get_session() as session:
        for each in data["data"]:
            new_data = Startups(
                module_id=data["module_id"],
                question=each["question"],
                option_1=each["option_1"],
                option_2=each["option_2"],
                option_3=each["option_3"],
            )

            session.add(new_data)

        await session.commit()


async def async_create_all() -> None:
    """
    Asynchronous create_all.
    """
    db_manager = DBManager()
    async with db_manager.get_session() as session:
        engine = get_engine_from_session(session)
        async with engine.begin() as conn:
            # create database tables
            await conn.run_sync(models.Base.metadata.create_all)

    await async_create_groups_and_vault()
    await async_create_user(
        name="testadmin", password="testpass", superuser="true", role=" --superuser"
    )
    await async_create_modules(
        [
            "sme",
            "startup",
            "current_strategy",
            "current_sitution",
            "customer",
            "channels",
        ]
    )
    await async_create_sme()
    await async_create_startup()
    await async_create_current_strategy(
        module_id=3, question="What are your current strategies"
    )
    await async_create_situation()


async def async_create_role(name: str, description: str = "") -> None:
    """
    Asynchronous create_role.
    """

    db_manager = DBManager()
    async with db_manager.get_session() as session:
        # check if group exists
        group = await session.scalar(select(Group).filter_by(name=name))
        if not group:
            # create group
            group = Group(name=name, description=description)
            session.add(group)
            await session.commit()


async def async_delete_role(name: str) -> None:
    """
    Asynchronous delete_role.
    """

    db_manager = DBManager()
    async with db_manager.get_session() as session:
        # load group
        group = await session.scalar(select(Group).filter_by(name=name))
        if group:
            # delete group
            await session.delete(group)
            await session.commit()


async def async_delete_user(name: str) -> None:
    """
    Asynchronous delete_user.
    """

    db_manager = DBManager()
    async with db_manager.get_session() as session:
        # load user
        user = await session.scalar(select(User).filter_by(name=name))
        if user:
            # delete user
            await session.delete(user)
            await session.commit()


async def async_create_user(
    name: str, password: str, superuser: bool, role: AuthRole | None = None
) -> None:
    """
    Asynchronous create_user.
    """

    # create database session
    db_manager = DBManager()
    async with db_manager.get_session() as session:
        # check if user exists
        user = await session.scalar(
            select(User).filter_by(name=name).options(selectinload(User.groups))
        )
        if not user:
            # encrypt password
            encrypted_pwd = encrypt_password(password)
            # create user
            user = User(name=name, password=encrypted_pwd, external_user_id=None)
            session.add(user)
            await session.flush()
            # reload user with groups
            user = await session.scalar(
                select(User).filter_by(name=name).options(selectinload(User.groups))
            )
            assert user

            # check if role specified for user
            group: Group | None = None
            if superuser:
                role = AuthRole.ADMIN
            if role:
                # load role
                group = await session.scalar(select(Group).filter_by(name=role))

            if group:
                # assign role to user
                user.groups.append(group)

            # commit the transaction
            await session.commit()
        else:
            raise ValueError("User already exists.")


async def async_drop_all() -> None:
    """
    Asynchronous drop_all.
    """

    table_names: list[str] = []

    # need to create a new session otherwise drop_all hangs if
    # called on the same session instance of select(TableDef)
    db_manager = DBManager()
    async with db_manager.get_session() as session:
        engine = get_engine_from_session(session)
        async with engine.begin() as conn:
            if table_names:
                # drop submission tables
                drop_sql = f"drop table if exists {','.join(table_names)};"
                await conn.execute(text(drop_sql))
                # await conn.commit()

            # drop other tables in model
            await conn.run_sync(models.Base.metadata.drop_all)


@app.command()
def create_all() -> None:
    """
    Create database tables
    """

    asyncio.run(async_create_all())


# pylint: disable = invalid-name
@app.command()
def drop_all(y: Annotated[bool, typer.Option("-y")] = False) -> None:
    """
    Delete all tables from database
    """

    if not y:
        confirm = input("Confirm dropping all tables from database? (y/N) ")
        if confirm:
            y = confirm.upper() == "Y"

    if y:
        asyncio.run(async_drop_all())


@app.command()
def create_user(
    name: str,
    password: str,
    superuser: bool = False,
    role: AuthRole = typer.Argument(None),
) -> None:
    """
    Create a new user
    """

    asyncio.run(
        async_create_user(name=name, password=password, superuser=superuser, role=role)
    )


@app.command()
def delete_user(name: str) -> None:
    """
    Delete a user
    """

    confirm = input(f"Confirm deleting user '{name}'? (y/N) ")
    if confirm and confirm.upper() == "Y":
        asyncio.run(async_delete_user(name=name))


if __name__ == "__main__":
    # start CLI App
    app()
