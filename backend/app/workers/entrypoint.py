"""ARQ-compatible worker entry point for Linux deployment."""

import os
from uuid import UUID

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.db.session import Database
from app.deep_research.factory import build_runtime_deep_research_graph
from app.models.enums import ResearchTaskStatus
from app.repositories.research_report import ResearchReportRepository
from app.repositories.research_task import ResearchTaskRepository
from app.schemas.deep_research import ResearchStage

logger = get_logger(__name__)


async def run_deep_research(
    _ctx: dict[str, object],
    task_id: str,
    ticker: str,
    question: str,
    *,
    request_id: str,
) -> None:
    settings = get_settings()
    database = Database(settings.database_url)
    parsed_task_id = UUID(task_id)
    try:
        async with database.transaction() as session:
            task = await ResearchTaskRepository(session).get(parsed_task_id)
            if task is None:
                raise AppError(
                    ErrorCode.DATABASE_ERROR,
                    "Research task does not exist.",
                    status_code=500,
                )
            if task.status == ResearchTaskStatus.COMPLETED:
                return
            await ResearchTaskRepository(session).mark_running(task)

        async def update_stage(stage: ResearchStage) -> None:
            async with database.transaction() as stage_session:
                current_task = await ResearchTaskRepository(stage_session).get(
                    parsed_task_id
                )
                if current_task is not None and current_task.status not in (
                    ResearchTaskStatus.COMPLETED,
                    ResearchTaskStatus.FAILED,
                ):
                    await ResearchTaskRepository(stage_session).mark_stage(
                        current_task, stage
                    )

        logger.info(
            "deep_research_worker_started",
            extra={"request_id": request_id, "task_id": task_id},
        )
        report = await build_runtime_deep_research_graph().ainvoke(
            ticker,
            question,
            request_id=request_id,
            stage_callback=update_stage,
        )
        async with database.transaction() as session:
            task = await ResearchTaskRepository(session).get(parsed_task_id)
            if task is None:
                raise AppError(
                    ErrorCode.DATABASE_ERROR,
                    "Research task disappeared during execution.",
                    status_code=500,
                )
            await ResearchReportRepository(session).create_deep_research(
                task=task, report=report
            )
            await ResearchTaskRepository(session).mark_completed(task)
        logger.info(
            "deep_research_worker_completed",
            extra={"request_id": request_id, "task_id": task_id},
        )
    except Exception as exc:
        error_code = (
            exc.code.value
            if isinstance(exc, AppError)
            else ErrorCode.INTERNAL_ERROR.value
        )
        async with database.transaction() as session:
            task = await ResearchTaskRepository(session).get(parsed_task_id)
            if task is not None and task.status != ResearchTaskStatus.COMPLETED:
                await ResearchTaskRepository(session).mark_failed(
                    task,
                    error_code=error_code,
                    error_message="Deep research worker failed.",
                )
        logger.exception(
            "deep_research_worker_failed",
            extra={"request_id": request_id, "task_id": task_id},
        )
        raise
    finally:
        await database.dispose()


class WorkerSettings:
    functions = [run_deep_research]
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", get_settings().redis_url)
    )
