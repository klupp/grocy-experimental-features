import logging

import requests

from api.api import API


class MarktGuruAPI(API):
    def __init__(self, host: str, port: int, api_key: str, client_key: str, zip_code: int):
        super().__init__(host, port)
        self.logger = logging.getLogger("MarktGuruAPI")
        self.api_key = api_key
        self.client_key = client_key
        self.zip_code = zip_code

    def get_url(self):
        url = super().get_url()
        url += '/api/v1'
        return url

    def get_headers(self):
        return {"x-clientkey": self.client_key, "x-apikey": self.api_key}

    def search_offers(self, query):
        self.logger.info(f"getting all offers for \"{query}\".")
        response = self.search_offers_paged(query)
        num_results = len(response["results"])
        offset = 24
        while num_results < response["totalResults"]:
            new_response = self.search_offers_paged(query, offset=offset)
            response["results"] += new_response["results"]
            offset += 24
            num_results += len(new_response["results"])
        return response["results"]

    def search_offers_paged(self, query, limit=24, offset=0):
        self.logger.info(f"getting {limit} offers for \"{query}\" on page {offset/limit}.")
        url = self.get_url() + "/offers/search"
        params = {"as": "web", "limit": limit, "offset": offset, "q": query, "zipCode": self.zip_code}
        response = requests.get(url=url, headers=self.get_headers(), params=params)
        return response.json()

    def get_offers_paged(self, limit=500, offset=0):
        self.logger.info(f"getting {limit} offers for page {offset/limit}.")
        url = self.get_url() + "/offers"
        params = {"as": "web", "limit": limit, "offset": offset, "zipCode": self.zip_code}
        response = requests.get(url=url, headers=self.get_headers(), params=params)
        return response.json()

    def get_all_offers(self):
        self.logger.info("getting all offers.")
        page_size = 500
        response = self.get_offers_paged(limit=page_size)
        num_results = len(response["results"])
        offset = page_size
        while num_results < response["totalResults"]:
            new_response = self.get_offers_paged(offset=offset, limit=page_size)
            response["results"] += new_response["results"]
            offset += page_size
            num_results += len(new_response["results"])
        return response["results"]
