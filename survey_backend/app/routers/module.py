from fastapi import APIRouter, status, Depends, HTTPException
from app.schemas.sme import (
    ModuleResponse,
    SmeResponse,
    SmeRequest,
    SmeValueResponse,
    StartupRequest,
    StartupValueResponse,
    StartRequestData,
    StrategyValueResponse,
    SituationValueRequest,
)
from typing import List
from app.db.models import Startups, SME, Module, CurrentStrategyValue, CurrentSituation
from app.dependencies import dbManager, get_current_user_from_multiple_auth
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from app.routers.utils import ErrorMessage
from sqlalchemy import select


router = APIRouter(
    prefix="/module",
    tags=["module"],
    responses={status.HTTP_404_NOT_FOUND: {"description": "Not found."}},
)


@router.post("", response_model=ModuleResponse)
async def create_module(
    name: str,
    db_manager: dbManager,
    current_user=Depends(get_current_user_from_multiple_auth),
) -> ModuleResponse:
    """Create a new SME record in the database"""

    _session: AsyncSession
    async with db_manager.get_session() as _session:
        new_module = Module(user_id=current_user.id, module_name=name)

        _session.add(new_module)
        await _session.commit()

    return {"success": True, "id": new_module.id}


@router.post("/sme", response_model=SmeResponse)
async def create_sme(db_manager: dbManager, data: List[SmeRequest]) -> SmeResponse:
    """Create a new SME record in the database"""

    _session: AsyncSession
    async with db_manager.get_session() as _session:
        try:
            for sme_data in data:
                string_value = ", ".join(sme_data.values)
                new_sme = SME(
                    module_id=sme_data.module_id,
                    heading=sme_data.heading,
                    question=sme_data.question,
                    value=string_value,
                )

                _session.add(new_sme)

            await _session.commit()

        except SQLAlchemyError as e:
            await _session.rollback()  # Rollback in case of any errors
            raise HTTPException(status_code=500, detail=str(e))

    return {"success": True}


@router.get("/sme", response_model=List[SmeRequest])
async def list_sme(db_manager: dbManager, module_id: int) -> List[SmeRequest]:
    """Fetch all SME records from the database"""

    async with db_manager.get_session() as _session:
        try:
            result = await _session.execute(
                select(SME).where(SME.module_id == module_id)
            )
            sme_records = result.scalars().all()

            # Convert each SME object to SmeRequest Pydantic model

            sme_responses = [SmeRequest.from_orm(sme) for sme in sme_records]

            return sme_responses

        except SQLAlchemyError as e:
            await _session.rollback()  # Rollback in case of any errors
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/save_sme_value", response_model=SmeResponse)
async def save_sme_value(
    data: List[SmeValueResponse],
    db_manager: dbManager,
) -> SmeResponse:
    """Create a new SME record in the database"""
    _session: AsyncSession
    async with db_manager.get_session() as _session:
        for each in data:
            result = await _session.execute(select(SME).where(SME.id == each.sme_id))
            sme = result.scalars().first()

            if sme is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"sme_id": ErrorMessage.USER_NOT_FOUND_MESSAGE},
                )
            sme.selected_value = each.value
            _session.add(sme)
        await _session.commit()
    return {"success": True}


@router.post("/startup", response_model=SmeResponse)
async def create_startup(db_manager: dbManager, data: StartupRequest) -> SmeResponse:
    """Create a new startup record in the database"""

    _session: AsyncSession
    async with db_manager.get_session() as _session:
        try:
            for each in data.data:
                new_data = Startups(
                    module_id=data.module_id,
                    question=each.question,
                    option_1=each.option_1,
                    option_2=each.option_2,
                    option_3=each.option_3,
                )

                _session.add(new_data)

            await _session.commit()

        except SQLAlchemyError as e:
            await _session.rollback()  # Rollback in case of any errors
            raise HTTPException(status_code=500, detail=str(e))

    return {"success": True}


@router.post("/save_startup_value", response_model=SmeResponse)
async def save_startup_value(
    data: List[StartupValueResponse],
    db_manager: dbManager,
) -> StartupValueResponse:
    """Create a new SME record in the database"""
    _session: AsyncSession
    async with db_manager.get_session() as _session:
        for each in data:
            result = await _session.execute(
                select(Startups).where(Startups.id == each.startup_id)
            )
            startup = result.scalars().first()

            if startup is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"startup_id": ErrorMessage.USER_NOT_FOUND_MESSAGE},
                )
            startup.selected_option = each.value
            _session.add(startup)
        await _session.commit()
    return {"success": True}


@router.get("/startup", response_model=List[StartupRequest])
async def list_startup(db_manager: dbManager, module_id: int) -> List[StartupRequest]:
    """Fetch all STARTUP records from the database"""

    async with db_manager.get_session() as _session:
        try:
            result = await _session.execute(
                select(Startups).where(Startups.module_id == module_id)
            )
            startup_records = result.scalars().all()

            # Convert each SME object to SmeRequest Pydantic model

            start_up_data = []
            mod_id = 0
            for data in startup_records:
                mod_id = data.module_id
                start_up_data.append(
                    StartRequestData(
                        question=data.question,
                        option_1=data.option_1,
                        option_2=data.option_2,
                        option_3=data.option_3,
                        selected_option=data.selected_option,
                    )
                )
            startup_responses = [StartupRequest(module_id=mod_id, data=start_up_data)]

            return startup_responses

        except SQLAlchemyError as e:
            await _session.rollback()  # Rollback in case of any errors
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/save_strategy_value", response_model=SmeResponse)
async def save_current_strategy_value(
    data: List[StrategyValueResponse],
    db_manager: dbManager,
) -> StartupValueResponse:
    """Create a new strategy values in the database"""
    _session: AsyncSession

    async with db_manager.get_session() as _session:
        try:
            for each in data:
                new_data = CurrentStrategyValue(
                    strategy_id=each.strategy_id, strategy=each.strategy
                )

                _session.add(new_data)

            await _session.commit()

        except SQLAlchemyError as e:
            await _session.rollback()  # Rollback in case of any errors
            raise HTTPException(status_code=500, detail=str(e))

    return {"success": True}


@router.get(
    "/strategy_value",
)
async def list_strategy(db_manager: dbManager, strategy_id: int):
    """Fetch all STARTUP records from the database"""

    async with db_manager.get_session() as _session:
        try:
            result = await _session.execute(
                select(CurrentStrategyValue).where(
                    CurrentStrategyValue.strategy_id == strategy_id
                )
            )
            startup_records = result.scalars().all()

            # Convert each SME object to SmeRequest Pydantic model

            strategy_data = []

            if startup_records:
                for data in startup_records:
                    strategy_data.append(
                        StrategyValueResponse(
                            strategy_id=data.strategy_id, strategy=data.strategy
                        )
                    )

                return strategy_data

        except SQLAlchemyError as e:
            await _session.rollback()  # Rollback in case of any errors
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/save_situation_value", response_model=SmeResponse)
async def save_current_situation_value(
    data: List[SituationValueRequest],
    db_manager: dbManager,
) -> SituationValueRequest:
    """Create a new situation values in the database"""
    _session: AsyncSession

    async with db_manager.get_session() as _session:
        try:
            for each in data:
                result = await _session.execute(
                    select(CurrentSituation).where(
                        CurrentSituation.id == each.situation_id
                    )
                )
                situation = result.scalars().first()

                if situation is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail={"situation_id": ErrorMessage.USER_NOT_FOUND_MESSAGE},
                    )
                situation.selected_value = each.selected_value
                situation.descriptions = each.descriptions
                _session.add(situation)
            await _session.commit()

        except SQLAlchemyError as e:
            await _session.rollback()  # Rollback in case of any errors
            raise HTTPException(status_code=500, detail=str(e))

    return {"success": True}
