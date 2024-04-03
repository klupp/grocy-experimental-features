import asyncio
import logging
from abc import ABCMeta, abstractmethod
from datetime import timedelta


class ScheduledWorker(metaclass=ABCMeta):
    def __init__(self, period: timedelta, worker_name: str):
        self.period = period
        self.logger = logging.getLogger(worker_name)
        self.worker_task = None

    async def run(self):
        if self.worker_task is not None:
            await self.cancel()
        self.logger.info(f"Start every {self.period}.")
        self.worker_task = asyncio.create_task(self.__run_schedule())

    async def __run_schedule(self):
        while True:
            await asyncio.sleep(self.period.total_seconds())
            await self.run_once()

    async def cancel(self):
        self.logger.info(f"Cancelled.")
        self.worker_task.cancel()

    @abstractmethod
    async def run_once(self):
        """
        Implement this method which will run one iteration of the worker
        """