import logging

from aiohttp import ClientSession


class NettoAPI:
    def __init__(self, session: ClientSession, username: str, api_key: str, token: str):
        self.logger = logging.getLogger("Netto API")
        self.session = session
        self.username = username
        self.api_key = api_key
        self.token = token

    async def get_receipts(self, offset=0, limit=10):
        headers = {
            "x-netto-api-key": self.api_key,
            "authorization": self.token,
            "user-agent": "NettoApp/7.0.6 (Build: 7.0.6.6; Android 11)",
            "accept-encoding": "gzip"
        }
        url = f"https://www.clickforbrand.de/aia/api/v2/benutzerkonten/{self.username}/einkaufhistorie?skip={offset}&take={limit}"
        async with self.session.get(url, headers=headers) as r:
            receipts = await r.json()
            for receipt in receipts["Items"]:
                receipt['BonId'] = receipt["Url"].split("/")[-1]
            return receipts

    async def get_receipt(self, receipt_id: str):
        url = f"https://bon.netto-online.de/bon/api/Bon/body?bonId={receipt_id}"
        async with self.session.get(url) as r:
            return await r.json()
