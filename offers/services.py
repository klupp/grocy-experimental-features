from typing import List

from offers.model import Offers


class OffersService:
    def __init__(self, name):
        self.name = name

    def search(self, query: str) -> Offers:
        pass


class CompositeOffersService(OffersService):
    def __init__(self, services: List[OffersService]):
        super().__init__(", ".join([service.name for service in services]))
        self.services = services

    def search(self, query: str) -> Offers:
        all_offers = Offers()
        for service in self.services:
            offers = service.search(query)
            all_offers.join(offers)
        return all_offers
