from typing import Protocol


class RunEvents(Protocol):
    async def run_created(self, run_id: str) -> None:
        """Сообщает раннерам, что в очереди появился новый прогон."""
