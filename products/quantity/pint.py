import logging

from dependency_injector.providers import Factory
from pint import UnitRegistry

from products.quantity import QuantityParser, Quantity


class PintQuantityParser(QuantityParser):
    def __init__(self, unit_registry: UnitRegistry, quantity_provider: Factory[Quantity]):
        super().__init__()
        self.logger = logging.getLogger("PintQuantityParser")
        self.registry = unit_registry
        self.registry.define("piece = dimensionless = pcs = stück = stk = st")
        self.quantity_parser = unit_registry.Quantity
        self.quantity_provider = quantity_provider

    def parse(self, quantity_str: str) -> Quantity:
        try:
            if quantity_str is None:
                quantity_str = "1"
            elif not isinstance(quantity_str, str):
                quantity_str = str(quantity_str)
            quantity_str = quantity_str.lower()
            # Empty strings not allowed
            if len(quantity_str) == 0:
                quantity_str = "1"
            if quantity_str.find("=") != -1:
                quantity_str = quantity_str.split("=")[1]
            quantity_str = quantity_str.replace('x', "*")

            qty = self.quantity_parser(quantity_str)
            unit_str = str(qty.units)
            if unit_str == 'dimensionless':
                unit_str = 'piece'
            if unit_str in ['liter', 'litre']:
                qty = qty.to('milliliter')
                unit_str = 'milliliter'
            if unit_str == 'kilogram':
                qty = qty.to('gram')
                unit_str = 'gram'
            return self.quantity_provider(amount=round(float(qty.magnitude), 7), unit=unit_str)
        except Exception as ex:
            self.logger.error(f"Error processing {quantity_str}")
            raise ex

