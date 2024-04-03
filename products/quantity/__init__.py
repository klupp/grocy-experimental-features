from abc import abstractmethod, ABC


class Quantity:
    def __init__(self, amount: float, unit: str):
        self.amount = amount
        self.unit = unit

    def __str__(self):
        return str(self.__dict__)


class QuantityParser(ABC):
    @abstractmethod
    def parse(self, quantity_str: str) -> Quantity:
        """

        :param quantity_str:
        :return:
        """
