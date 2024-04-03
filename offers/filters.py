from datetime import date
from typing import List

from offers.model import OfferFilter, Offer


class SelectedStoresOfferFilter(OfferFilter):
    def __init__(self, accepted_stores: List[str] = None):
        super().__init__()
        if accepted_stores is not None:
            self.accepted_stores = [store.lower().strip() for store in accepted_stores]
        else:
            self.accepted_stores = None

    def filter(self, offer: Offer) -> bool:
        if self.accepted_stores is None or len(self.accepted_stores) == 0:
            return True
        for store in self.accepted_stores:
            if offer.store_name.lower().strip().find(store) != -1:
                return True
        return False


class BannedBrandsOfferFilter(OfferFilter):
    def __init__(self, banned_brands: List[str]):
        super().__init__()
        self.banned_brands = [brand.lower().strip() for brand in banned_brands]

    def filter(self, offer: Offer) -> bool:
        if offer.brand_name is None:
            return True
        if offer.brand_name.lower().strip() in self.banned_brands:
            return False
        return True


class TimeOfferFilter(OfferFilter):
    def __init__(self, time: date):
        super().__init__()
        self.time = time

    def filter(self, offer: Offer) -> bool:
        if self.time < offer.valid_from.date() or self.time > offer.valid_to.date():
            return False
        return True