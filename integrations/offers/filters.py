from grocy.index import GrocyIndex
from offers.model import OfferFilter, Offer


class GrocyQuOfferFilter(OfferFilter):
    def __init__(self, grocy_index: GrocyIndex, allowed_qus):
        super().__init__()
        self.grocy_index = grocy_index
        self.allowed_qus = allowed_qus

    def filter(self, offer: Offer) -> bool:
        grocy_qus = self.grocy_index.query_qu_index(offer.qu)
        if len(grocy_qus) < 1:
            return False
        grocy_qu = grocy_qus[0]
        factor = self.allowed_qus.get(int(grocy_qu['id']), None)
        if factor is None:
            return False
        offer.price /= factor
        offer.reference_price /= factor
        return True
