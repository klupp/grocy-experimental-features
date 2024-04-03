import os
from datetime import datetime
import time

from deep_translator import GoogleTranslator

from offers.index import OfferIndex
from offers.markt_guru.api.markt_guru import MarktGuruAPI
from offers.model import Offers, Offer
from offers.services import OffersService

import json


class MarktGuruOffersService(OffersService):
    def __init__(self, api: MarktGuruAPI, offer_index: OfferIndex):
        super().__init__("MarktGuru")
        self.api = api
        self.translator = GoogleTranslator(source='de', target='en')
        self.qus_cache = {}
        self.offer_index = offer_index
        refresh_scheduled = time.time() - os.path.getmtime("today_offers.json") > 86400
        if refresh_scheduled:
            offers = self.api.get_all_offers()
            self.offers = {offer['id']: offer for offer in offers}
            self.offer_index.update_offer_index(offers)
            with open("today_offers.json", "w") as fp:
                json.dump(offers, fp)
        else:
            with open("today_offers.json", "r") as fp:
                offers = json.load(fp)
                self.offers = {offer['id']: offer for offer in offers}
                # self.offer_index.update_product_index(offers)

    def get_qu(self, qu_name):
        qu = self.qus_cache.get(qu_name, None)
        if qu is not None:
            return qu
        qu = self.translator.translate(qu_name)
        self.qus_cache[qu_name] = qu
        return qu

    def map_offer(self, mg_offer):
        # Fix reference price if it is None
        if mg_offer["referencePrice"] is None:
            mg_offer["referencePrice"] = mg_offer["price"]
        for i in range(0, len(mg_offer["advertisers"])):
            advertiser = mg_offer["advertisers"][i]
            validity_dates = mg_offer["validityDates"][i]
            image_url = f"https://mg2de.b-cdn.net/api/v1/offers/{mg_offer['id']}/images/default/0/medium.webp"
            source_url = f"https://www.marktguru.de/offers/{mg_offer['id']}"
            brand_name = mg_offer["brand"]["name"]
            if brand_name == "thisisnobrand123":
                brand_name = None
            offer = Offer(
                id=str(mg_offer['id']),
                source_name=self.name,
                product_name=mg_offer["product"]["name"],
                brand_name=brand_name, store_name=advertiser["name"],
                price=mg_offer["price"],
                reference_price=mg_offer["referencePrice"], qu=self.get_qu(mg_offer["unit"]["shortName"]),
                valid_from=datetime.strptime(validity_dates["from"], "%Y-%m-%dT%H:%M:%SZ"),
                valid_to=datetime.strptime(validity_dates["to"], "%Y-%m-%dT%H:%M:%SZ"),
                requires_membership=mg_offer["requiresLoyalityMembership"], image_url=image_url,
                source_url=source_url, description=mg_offer["description"])
            yield offer

    def search(self, query: str) -> Offers:
        idx_results = self.offer_index.query_offer_index(query)
        offers = []
        for idx_result in idx_results:
            mg_offer = self.offers[int(idx_result['id'])]
            for offer in self.map_offer(mg_offer):
                offers.append(offer)
        return Offers(offers)
