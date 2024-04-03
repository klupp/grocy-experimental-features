from dataclasses import dataclass, field
from datetime import timedelta

from grocy.index import GrocyIndex
from integrations.offers import GrocyOfferIntegration
from stock.forecast.consumption.sarimax import SARIMAXConsumptionForecaster
from utils.workers import ScheduledWorker


@dataclass
class ShoppingListConfig:
    max_stock_days: int = 180
    stores_to_visit: list[str] = field(default_factory=list)


class ShoppingListWorker(ScheduledWorker):
    def __init__(self, grocy_offer_integration: GrocyOfferIntegration, grocy_index: GrocyIndex,
                 forecaster: SARIMAXConsumptionForecaster, period: timedelta = timedelta(hours=12),
                 config: ShoppingListConfig = ShoppingListConfig()):
        super().__init__(period, "ShoppingListWorker")
        self.grocy_offer_integration = grocy_offer_integration
        self.grocy_index = grocy_index
        self.forecaster = forecaster
        self.config = config

    async def run_once(self):
        await self.grocy_index.update_product_index()
        await self.grocy_index.update_qu_index()
        await self.forecaster.create_models()
        await self.grocy_offer_integration.get_offers(stores_to_visit=self.config.stores_to_visit)
        await self.grocy_offer_integration.collect_interesting_offers(max_stock_days=self.config.max_stock_days)
        await self.grocy_offer_integration.update_shopping_list_notes()
