from app.workers.service import DeepResearchService


class DeepResearchWorker:
    """Worker entry point; Redis/ARQ can call the same run-once boundary."""

    def __init__(self, service: DeepResearchService) -> None:
        self.service = service

    async def run_once(self) -> bool:
        return await self.service.run_once()
