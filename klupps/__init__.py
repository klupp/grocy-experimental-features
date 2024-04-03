import logging

from deep_translator import GoogleTranslator

from grocy import GrocyProductUpdateHandler
from grocy.api.grocy_api import GrocyAPI


class KluppsGrocyProductNameUpdateHandler(GrocyProductUpdateHandler):
    def __init__(self, grocy_api: GrocyAPI):
        self.logger = logging.getLogger("KluppsGrocyProductNameUpdateHandler")
        self.logger.info("Init")
        self.de_translate_api = GoogleTranslator(source='en', target='de')
        self.mk_translate_api = GoogleTranslator(source='en', target='mk')
        self.grocy_api = grocy_api

    async def update(self, product):
        old_name = product["name"]
        names = old_name.split('/')
        if len(names) == 3:
            return
        en_name = names[0].strip().lower()
        name = f"{en_name} / {self.de_translate_api.translate(en_name)} / {self.mk_translate_api.translate(en_name)}"
        product["name"] = name
        self.logger.info(f"Update {old_name} to {name}")
        return await self.grocy_api.update_product(product)

