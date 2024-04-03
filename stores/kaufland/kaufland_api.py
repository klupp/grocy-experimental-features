import logging

from aiohttp import ClientSession


class KauflandApi:
    def __init__(self, session: ClientSession, user_id: str):
        self.logger = logging.getLogger("Kaufland API")
        self.session = session
        self.user_id = user_id

    async def get_receipts(self, offset=0, limit=10):
        url = f"/api/v2/customers/{self.user_id}/transactions?country=de&limit={limit}&start={offset}"
        async with self.session.get(url) as r:
            return await r.json()
