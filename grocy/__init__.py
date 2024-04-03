import asyncio
from abc import ABC, abstractmethod
from typing import List


class GrocyProductUpdateHandler(ABC):
    @abstractmethod
    async def update(self, product):
        pass


class GrocyProductUpdateHandlerComposite(GrocyProductUpdateHandler):
    def __init__(self, handlers: List[GrocyProductUpdateHandler]):
        self.handlers = handlers

    async def update(self, product):
        return await asyncio.gather(*[handler.update(product) for handler in self.handlers])
