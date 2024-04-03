import logging
from typing import Optional

import scrape_schema_recipe
from aiohttp import ClientSession
from dependency_injector import containers, providers, resources
from dependency_injector.resources import T
from lidlplus import LidlPlusApi
from openfoodfacts import API, Country, Flavor, APIVersion, Environment
from pint import UnitRegistry
from starlette.templating import Jinja2Templates

from grocy import GrocyProductUpdateHandlerComposite
from grocy.api.grocy_api import GrocyAPI
from grocy.index import GrocyIndex
from grocy.product_data_update import GrocyDataUpdateProductAndBarcodeHandler
from integrations.offers import GrocyOfferIntegration, GrocyQuOfferFilter
from klupps import KluppsGrocyProductNameUpdateHandler
from offers.index import OfferIndex
from offers.markt_guru import MarktGuruAPI, MarktGuruOffersService
from offers.services import CompositeOffersService
from products.data.model import ProductDataSource, CompositeProductDataSource
from products.data.off import OFFProductDataSource
from products.quantity import Quantity, QuantityParser
from products.quantity.pint import PintQuantityParser
from products.services import ProductService, GrocyProductService
from recipes.meal_paln.meal_plan_service import MealPlanService
from recipes.meal_paln.workers import MealPlanWorker
from recipes.services import RecipeService
from shopping_list.workers import ShoppingListWorker
from stock.forecast.consumption.sarimax import SARIMAXConsumptionForecaster
from stores.kaufland.kaufland_api import KauflandApi
from stores.kaufland.service import KauflandCounter
from stores.lidl.service import LidlCounter
from stores.netto.netto_api import NettoAPI
from stores.netto.service import NettoCounter
from stores.rewe.rewe_api import ReweAPI
from stores.rewe.service import ReweCounter
from stores.services import StoreService, GrocyStoreService


class AIOClientSession(resources.AsyncResource):
    async def init(self, **kwargs):
        return ClientSession(**kwargs)

    async def shutdown(self, session):
        await session.close()


class WorkerResource(resources.AsyncResource):
    async def init(self, worker_class, **kwargs):
        worker = worker_class(**kwargs)
        await worker.run()
        return worker

    async def shutdown(self, worker):
        await worker.cancel()


def get_base_url(host: str, port: int):
    url = host
    if port not in [80, 443]:
        url += ":" + str(port)
    return url


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(yaml_files=["config.yml"])

    logging = providers.Resource(
        logging.basicConfig,
        level=logging.INFO
    )

    grocy_client_session = providers.Resource(
        AIOClientSession,
        base_url=providers.Singleton(
            get_base_url,
            host=config.grocy.host,
            port=config.grocy.port
        ),
        headers=providers.Dict({
            "accept": "application/json",
            "Content-Type": "application/json",
            "GROCY-API-KEY": config.grocy.api_key
        })
    )

    templates = providers.ThreadSafeSingleton(
        Jinja2Templates,
        directory="templates"
    )

    grocy_api = providers.ThreadSafeSingleton(
        GrocyAPI,
        session=grocy_client_session
    )

    grocy_index = providers.ThreadSafeSingleton(
        GrocyIndex,
        grocy_api=grocy_api
    )

    quantity_provider = providers.Factory(
        Quantity
    ).provider

    pint_registry = providers.ThreadSafeSingleton(
        UnitRegistry
    )

    quantity_parser: providers.Provider[QuantityParser] = providers.ThreadSafeSingleton(
        PintQuantityParser,
        unit_registry=pint_registry,
        quantity_provider=quantity_provider
    )

    markt_guru_api = providers.ThreadSafeSingleton(
        MarktGuruAPI,
        host=config.markt_guru.host,
        port=config.markt_guru.port,
        api_key=config.markt_guru.api_key,
        client_key=config.markt_guru.client_key,
        zip_code=config.markt_guru.zip_code
    )

    offer_index = providers.ThreadSafeSingleton(
        OfferIndex
    )

    markt_guru_service = providers.ThreadSafeSingleton(
        MarktGuruOffersService,
        api=markt_guru_api,
        offer_index=offer_index
    )

    offers_service = providers.ThreadSafeSingleton(
        CompositeOffersService,
        services=providers.List(markt_guru_service)
    )

    grocy_qu_offer_filter = providers.Factory(
        GrocyQuOfferFilter,
        grocy_index=grocy_index
    )

    product_service: providers.Provider[ProductService] = providers.ThreadSafeSingleton(
        GrocyProductService,
        grocy_api=grocy_api,
        grocy_index=grocy_index
    )

    consumption_forecaster = providers.ThreadSafeSingleton(
        SARIMAXConsumptionForecaster,
        grocy_api=grocy_api
    )

    offer_integration = providers.ThreadSafeSingleton(
        GrocyOfferIntegration,
        grocy_api=grocy_api,
        offers_service=offers_service,
        grocy_qu_offer_filter=grocy_qu_offer_filter.provider,
        product_service=product_service,
        consumption_forecaster=consumption_forecaster
    )

    scrape_recipe = providers.Callable(
        scrape_schema_recipe.scrape_url
    )

    recipe_service = providers.ThreadSafeSingleton(
        RecipeService,
        scrape_recipe=scrape_recipe.provider,
        grocy_index=grocy_index,
        grocy_api=grocy_api,
        product_service=product_service
    )

    meal_plan_service = providers.ThreadSafeSingleton(
        MealPlanService,
        grocy_api=grocy_api
    )

    meal_plan_worker = providers.Resource(
        WorkerResource,
        worker_class=MealPlanWorker,
        grocy_api=grocy_api,
        mp_service=meal_plan_service
    )

    shopping_list_worker = providers.Resource(
        WorkerResource,
        worker_class=ShoppingListWorker,
        grocy_offer_integration=offer_integration,
        grocy_index=grocy_index,
        forecaster=consumption_forecaster
    )

    lidl = providers.ThreadSafeSingleton(
        LidlPlusApi,
        language=config.lidl.language,
        country=config.lidl.country,
        refresh_token=config.lidl.token
    )

    lidl_counter = providers.ThreadSafeSingleton(
        LidlCounter,
        api=lidl,
        qu_parser=quantity_parser
    )


    rewe_client_session = providers.Resource(
        AIOClientSession,
        base_url="https://shop.rewe.de/",
        cookies=providers.Dict({
            "rstp": config.rewe.token
        })
    )

    rewe_api = providers.ThreadSafeSingleton(
        ReweAPI,
        session=rewe_client_session
    )

    rewe_counter = providers.ThreadSafeSingleton(
        ReweCounter,
        api=rewe_api
    )

    netto_client_session = providers.Resource(
        AIOClientSession
    )

    netto_api = providers.ThreadSafeSingleton(
        NettoAPI,
        session=netto_client_session,
        username=config.netto.username,
        api_key=config.netto.api_key,
        token=config.netto.token
    )

    netto_counter = providers.ThreadSafeSingleton(
        NettoCounter,
        api=netto_api
    )

    kaufland_client_session = providers.Resource(
        AIOClientSession,
        base_url="https://p.crm-dynamics.schwarz/",
        headers=providers.Dict({
            "client-id": config.kaufland.client_id,
            "Authorization": config.kaufland.token
        })
    )

    kaufland_api = providers.ThreadSafeSingleton(
        KauflandApi,
        session=kaufland_client_session,
        user_id=config.kaufland.user_id
    )

    kaufland_counter = providers.ThreadSafeSingleton(
        KauflandCounter,
        api=kaufland_api,
        qu_parser = quantity_parser
    )

    off_api = providers.ThreadSafeSingleton(
        API,
        username=config.open_facts.username,
        password=config.open_facts.password,
        country=Country.world,
        flavor=Flavor.off,
        version=APIVersion.v2,
        environment=Environment.org
    )

    off_datasource: providers.Provider[ProductDataSource] = providers.ThreadSafeSingleton(
        OFFProductDataSource,
        api=off_api,
        quantity_parser=quantity_parser
    )

    product_datasource: providers.Provider[ProductDataSource] = providers.ThreadSafeSingleton(
        CompositeProductDataSource,
        sources=providers.List(
            off_datasource
        )
    )

    product_and_barcode_update_handler = providers.ThreadSafeSingleton(
        GrocyDataUpdateProductAndBarcodeHandler,
        grocy_api=grocy_api,
        grocy_index=grocy_index,
        product_datasource=product_datasource
    )

    klupps_product_name_update_handler = providers.ThreadSafeSingleton(
        KluppsGrocyProductNameUpdateHandler,
        grocy_api=grocy_api
    )

    product_updater = providers.ThreadSafeSingleton(
        GrocyProductUpdateHandlerComposite,
        handlers=providers.List(
            product_and_barcode_update_handler,
            klupps_product_name_update_handler
        )
    )

    store_service: providers.Provider[StoreService] = providers.ThreadSafeSingleton(
        GrocyStoreService,
        grocy_api=grocy_api,
        grocy_index=grocy_index,
        lidl_api=lidl,
        product_db=product_datasource,
        product_service=product_service,
        lidl_counter=lidl_counter,
        kaufland_counter=kaufland_counter,
        netto_counter=netto_counter,
        rewe_counter=rewe_counter
    )
