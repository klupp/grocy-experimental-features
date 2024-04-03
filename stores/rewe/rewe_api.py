import logging

import requests
from aiohttp import ClientSession


class ReweAPI:
    def __init__(self, session: ClientSession):
        self.logger = logging.getLogger("REWE_API")
        self.session = session
        self.logger.info("REWE API initialized.")
        self.token = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJhZXMxOTIiOiI5MDIyYWUzZmZiNzcwZTllZWMyNGU4NTI0ZGI1Mzk1ZmJjN2U4MzE4N2M2OWM1NzdmN2EwZmZjNDIzZTVkNTBhODdiNWNkY2ZmZTRlOTQ3YmM0ZGJiMTQ0OWVjNDBmMzViYTZjYTQyMGE0ZjEzMDdkOWVmMDY0Yzk4MmY0NTMzMGU3NWRiMGMyNjU1ZmE3ZDhiODBiODBkNjc1OWUwNWJiZGIzOTY5YzViYzg5N2Q0MTZhYWEwN2M1MzJhZmQ0NmNiMmU1OWJlMTJmNWRkNmY1YmFlNDVhMmMyODJlM2E4ZWI4ZDRiNWQzOTVjNmY0MTdlNTgzZTRlOTlhMjBkODA2MzQ2YjE0MTQyNmNkZmI3NjEzNzllODNhMjZjZmFjZDAxMDY4MmZmZjJkMmMwZjZiMTNhNDBmNTMxNjY5ZDU0ODU2MDZmN2M2MjhlNTg2YTk0NDcwNzE5N2FjN2Y3MTcwYWI3ZDgxMDZiODRiZGYxMzI2OTE1ODZkYWQ3MDVmNWJlNWZlZTQ4Njk5ODFmMDBlMWZmY2E0ZmIxMGYwZDUyM2U1YWEyNGIwOWUwYTU4ZmMyODUzODZmYzBhMjg0YTk3IiwiZXhwIjoxNzA4ODU1NTU1LCJpYXQiOjE3MDg4NTQ5NTV9.PHXXJxfGW7Rxb9S56EvZMGtYSikZ-7Ba63me2OIpNbwr8iaCO3hC3uTp9Ns82rYxk5MDYZ8JI3P9d8Ravm_EpA"

    async def get_receipts(self):
        url = "/api/receipts/"
        async with self.session.get(url) as r:
            return await r.json()
        # return requests.get("https://shop.rewe.de/api/receipts", cookies={"rstp": self.token}, timeout=10).json()

    async def get_receipt(self, receipt_id: str):
        url = f"/api/receipts/{receipt_id}"
        # async with self.session.get(url) as r:
        #     return await r.text()
        return requests.get(f"https://shop.rewe.de{url}", cookies={"rstp": self.token}, timeout=10)
