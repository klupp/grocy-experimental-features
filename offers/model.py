import abc
import datetime
from abc import ABC
from typing import List, Callable, Any


class Offer:
    def __init__(self, id: str, source_name: str, product_name: str, brand_name: str, store_name: str, price: float,
                 reference_price: float, qu: str, valid_from: datetime.datetime, valid_to: datetime.datetime,
                 requires_membership: bool, image_url: str, source_url: str, description: str):
        self.id = id
        self.source_name = source_name
        self.product_name = product_name
        self.brand_name = brand_name
        self.store_name = store_name
        self.price = price
        self.reference_price = reference_price
        self.qu = qu
        self.valid_from = valid_from
        self.valid_to = valid_to
        self.requires_membership = requires_membership
        self.image_url = image_url
        self.source_url = source_url
        self.description = description
        self.preferences = {}

    def get_name(self) -> str:
        note = ""
        if self.brand_name is not None:
            note = self.brand_name + " "
        note += f"{self.product_name}"
        return note


class OfferFilter(ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def filter(self, offer: Offer) -> bool:
        pass

    def __call__(self, *args, **kwargs):
        self.filter(*args, **kwargs)


class OfferPreference:
    def __init__(self):
        pass

    def get_preference(self, offer: Offer) -> float:
        pass

    def get_preference_name(self):
        pass


class Offers:
    def __init__(self, offers: List[Offer] = None, filters: List[OfferFilter] = None,
                 preferences: List[OfferPreference] = None):
        if offers is None:
            offers = []
        self.offers = offers
        if filters is None:
            filters = []
        self.filters = filters
        if preferences is None:
            preferences = []
        self.preferences = preferences
        self.sort_key = None
        self.sort_reverse = False

    def append(self, offer: Offer):
        self.offers.append(offer)

    def join(self, offers):
        self.offers.extend(offers.offers)
        self.filters.extend(offers.filters)

    def add_filter(self, new_filter: OfferFilter):
        self.filters.append(new_filter)

    def add_preference(self, new_preference: OfferPreference):
        self.preferences.append(new_preference)

    def set_sort_order(self, key: Callable[[Offer], Any], reverse: bool = False):
        self.sort_key = key
        self.sort_reverse = reverse

    def get_final_offers(self) -> list[Offer]:
        result = self.offers
        for offer in result:
            for preference in self.preferences:
                offer.preferences[preference.get_preference_name()] = preference.get_preference(offer)

        for f in self.filters:
            result = filter(f.filter, result)

        result = sorted(result, key=self.sort_key, reverse=self.sort_reverse)

        return result

    def get_top_offer(self) -> Offer | None:
        offers = self.get_final_offers()
        if len(offers) > 0:
            return offers[0]
        return None
