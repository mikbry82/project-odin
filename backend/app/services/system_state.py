from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_state import SystemState


async def get_or_create_system_state(session: AsyncSession) -> SystemState:
    state = await session.get(SystemState, 1)
    if state is None:
        state = SystemState(id=1)
        session.add(state)
        await session.commit()
        await session.refresh(state)
    return state
