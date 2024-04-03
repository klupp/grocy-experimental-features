import asyncio
import base64
import json
import logging
import math
from datetime import datetime, date, timedelta
from typing import Callable, List

import requests
import time
from tqdm import tqdm

from grocy.api.grocy_api import USER_FILES, GrocyAPI
from integrations.offers.filters import GrocyQuOfferFilter
from offers.filters import BannedBrandsOfferFilter, SelectedStoresOfferFilter, TimeOfferFilter
from offers.preferences import BrandOfferPreference
from offers.services import OffersService
from products.services import ProductService
from stock.forecast.consumption.sarimax import SARIMAXConsumptionForecaster


class GrocyOfferIntegration:
    def __init__(self, grocy_api: GrocyAPI, offers_service: OffersService,
                 consumption_forecaster: SARIMAXConsumptionForecaster, product_service: ProductService,
                 grocy_qu_offer_filter: Callable[..., GrocyQuOfferFilter]):
        self.note_start = "=== offer start ===\n"
        self.grocy_api = grocy_api
        self.logger = logging.getLogger("GrocyOffers")
        self.grocy_qu_offer_filter = grocy_qu_offer_filter
        self.offers_service = offers_service
        self.consumption_forecaster = consumption_forecaster
        self.product_service = product_service

    async def __get_offer(self, product, conversions, shopping_time: date = datetime.now().date(),
                          stores_to_visit: List[str] = None):
        product_user_fields = product['userfields']

        preferred_brands = [brand for brand in (
            product_user_fields['preferredbrands'].split(',') if product_user_fields[
                                                                     'preferredbrands'] is not None else [])]
        banned_brands = [brand for brand in (
            product_user_fields['bannedbrands'].split(',') if product_user_fields['bannedbrands'] is not None else [])]

        name = product['name'].split("/")[1].strip()
        offers = self.offers_service.search(name)
        offers.add_preference(BrandOfferPreference(preferred_brands))
        offers.add_filter(TimeOfferFilter(shopping_time))
        offers.add_filter(BannedBrandsOfferFilter(banned_brands))
        offers.add_filter(await self.grocy_qu_offer_filter(allowed_qus=conversions))
        offers.add_filter(SelectedStoresOfferFilter(accepted_stores=stores_to_visit))
        offers.set_sort_order(key=lambda x: (x.preferences["brand"], x.reference_price))
        offer = offers.get_top_offer()

        if offer is not None:
            # If the offer is the same don't do anything just skip
            if product_user_fields['offername'] is not None:
                offer_name = json.loads(product_user_fields['offername'])
                if offer_name['link'] == str(offer.source_url):
                    return 1
            product_user_fields['offerstore'] = offer.store_name
            product_user_fields['offername'] = json.dumps(
                {"title": str(offer.get_name()), "link": str(offer.source_url)})
            product_user_fields['offerprice'] = offer.reference_price
            product_user_fields['offeramount'] = offer.price / offer.reference_price
            product_user_fields['offermemberrequired'] = offer.requires_membership
            product_user_fields['offerfrom'] = "{:%Y-%m-%d %H:%M:%S}".format(offer.valid_from)
            product_user_fields['offerto'] = "{:%Y-%m-%d %H:%M:%S}".format(offer.valid_to)
            product_user_fields['offernote'] = offer.description

            image_name = offer.source_name + offer.id + "." + offer.image_url.split("/")[-1].split(".")[-1]
            b64_image_name = base64.b64encode(bytes(image_name, 'utf-8')).decode("utf-8")
            offerpicture_name = b64_image_name + "_" + b64_image_name
            # Don't update the picture if it is the same picture by any chance
            if offerpicture_name != product_user_fields['offerpicture']:
                if product_user_fields['offerpicture'] is not None:
                    await self.grocy_api.delete_file(USER_FILES, product_user_fields['offerpicture'].split("_")[0],
                                                     base64_encoded=True)
                product_user_fields['offerpicture'] = offerpicture_name
                image = requests.get(offer.image_url).content
                await self.grocy_api.upload_file(USER_FILES, image, image_name)
        elif product_user_fields['offername'] is not None:
            # Clear the data if there was an offer before
            if product_user_fields['offerpicture'] is not None:
                await self.grocy_api.delete_file(USER_FILES, product_user_fields['offerpicture'].split("_")[0],
                                                 base64_encoded=True)
            product_user_fields['offerstore'] = None
            product_user_fields['offername'] = None
            product_user_fields['offerprice'] = None
            product_user_fields['offeramount'] = None
            product_user_fields['offermemberrequired'] = None
            product_user_fields['offerfrom'] = None
            product_user_fields['offerto'] = None
            product_user_fields['offernote'] = None
            product_user_fields['offerpicture'] = None
        else:
            return 0

        await self.grocy_api.update_user_fields("products", product["id"], product_user_fields)
        return 1

    async def get_offers(self, stores_to_visit: List[str] = None, shopping_time: date = datetime.now().date()):
        self.logger.info("search offers for each grocy product.")
        start = time.time()
        products, product_conversions = await asyncio.gather(self.grocy_api.get_products(),
                                                             self.grocy_api.get_to_price_conversions())
        result = await asyncio.gather(*[
            self.__get_offer(product=product, conversions=product_conversions[product['id']],
                             shopping_time=shopping_time, stores_to_visit=stores_to_visit) for product in products])
        num_offers = sum(result)
        self.logger.info(
            f"Processed {num_offers} out of {len(products)} in {time.time() - start} or {(num_offers / len(products)) * 100} have offers.")

    def __get_stock_days(self, shelf_life: float, max_stock_days: float = 180, save_percent: float | None = None):
        x = shelf_life
        a = max_stock_days
        b = 1.5
        if save_percent is not None and save_percent > 0:
            b -= save_percent
            b = max(b, 1.1)
        return a * math.tanh((1 / a) * x ** (1 / b))

    async def __collect_offer(self, product, already_in_shopping_list: set[int], max_stock_days: int = 180):
        target_list_id = 1
        if product['id'] in already_in_shopping_list:
            return 1
        product_user_fields = product['userfields']
        if product_user_fields['dontPurchase'] == "1":
            return 0
        product_details = await self.product_service.get_product(product['id'], stock_qu_id=product['qu_id_stock'])

        offer_price = product_user_fields['offerprice']

        factor = product_details.get_conversion(product_details.price_unit.id).factor

        if product_details.average_shelf_life_days == 0:
            self.logger.warning(f"{product_details.name}({product_details.id}) has average shelf life of 0.")
            return 0

        stock_days = min(max(2, round(
            product_details.average_shelf_life_days)) if product_details.average_shelf_life_days >= 0 else max_stock_days * 2,
                         max_stock_days * 2)

        if product_details.average_price is not None and offer_price is not None:
            average_price = product_details.average_price * factor
            save_percent = 1 - float(offer_price) / average_price
            stock_days = self.__get_stock_days(stock_days, max_stock_days=max_stock_days, save_percent=save_percent)
        else:
            stock_days = self.__get_stock_days(stock_days, max_stock_days=max_stock_days)

        end_date = date.today() + timedelta(days=stock_days)
        try:
            prediction = self.consumption_forecaster.get_forecast(product['id'], end_date)
        except:
            # self.logger.exception(f"{product_details.name}({product_details.id}) prediction failed.")
            return 0
        amount_to_buy = prediction - product_details.stock_amount
        if amount_to_buy <= 0:
            return 0
        if amount_to_buy <= product_details.min_unit_size / 2.0:
            return 0

        new_sl_item = await self.grocy_api.add_to_shopping_list(
            {"product_id": product['id'], "shopping_list_id": target_list_id, "amount": amount_to_buy,
             "qu_id": product["qu_id_purchase"], "note": ""})

        res = await self.grocy_api.update_user_fields("shopping_list", int(new_sl_item['created_object_id']), {"generated": True})

        print(res)
        return 1

    async def collect_interesting_offers(self, max_stock_days: int = 180):
        self.logger.info("Create offer shopping list")
        start = time.time()
        products, _ = await asyncio.gather(self.grocy_api.get_products(), self.grocy_api.clear_shopping_list(1))
        already_in_shopping_list = set([item['product_id'] for item in await self.grocy_api.get_shopping_list()])
        result = await asyncio.gather(
            *[self.__collect_offer(product, already_in_shopping_list, max_stock_days) for product in products])

        self.logger.info(f"Created shopping list with {sum(result)} items in {time.time() - start}")

    def __remove_note_residuals(self, note: str) -> str:
        if note is None:
            note = ""
        start = note.find(self.note_start)
        if start == -1:
            return note
        if start > 0:
            start -= 1
        return note[:start]

    async def __update_sl_item_notes(self, sl_item):
        product, fields = await asyncio.gather(self.grocy_api.get_product_details(sl_item['product_id']),
                                               self.grocy_api.get_user_fields('products', sl_item['product_id']))

        old_note = sl_item["note"]
        # Remove old offer residuals
        note = self.__remove_note_residuals(old_note)
        # Needed only for last and average price (Android app not working)

        if fields['offerprice'] is not None:
            if len(note) > 0:
                note += "\n"
            note += self.note_start

            name = json.loads(fields['offername'])['title']
            note += f"{name}: €{fields['offerprice']} per {product['quantity_unit_price']['name']} / {round(float(fields['offeramount']), 2)} {product['quantity_unit_price']['name'] if float(fields['offeramount']) == 1 else product['quantity_unit_price']['name_plural']} \n"
            note += f"{fields['offerstore']}: {str(fields['offerfrom'])} - {str(fields['offerto'])}\n"
            note += f"{fields['offernote']}"

        sl_item["note"] = note
        await self.grocy_api.update_shopping_list(sl_item)

    async def update_shopping_list_notes(self):
        self.logger.info("update grocy shopping lists notes.")
        start = time.time()
        shopping_list = await self.grocy_api.get_shopping_list()
        await asyncio.gather(*[self.__update_sl_item_notes(sl_item) for sl_item in shopping_list])
        self.logger.info(f"Updated shopping list notes in in {time.time() - start}")

    async def clear_shopping_list_notes(self):
        self.logger.info("Clear shopping list notes.")
        shopping_list = await self.grocy_api.get_shopping_list()
        for sl_item in tqdm(shopping_list):
            if sl_item['note'] is None or len(sl_item['note']) == 0:
                continue
            sl_item['note'] = None
            await self.grocy_api.update_shopping_list(sl_item)
