from offers.model import Offer


class GrocyOffer:
    def __init__(self, grocy_product, grocy_stores, offer: Offer):
        self.grocy_product = grocy_product
        self.grocy_shopping_lists = grocy_stores
        self.offer = offer

    def get_target_shopping_list(self):
        for sl in self.grocy_shopping_lists:
            if self.offer.store_name.lower().strip().find(sl['name'].lower().strip()) != -1:
                return sl
        return None

    def get_description(self):
        note = self.offer.store_name + "\n"
        note += f"{self.offer.get_name()}\n{self.offer.valid_from} - {self.offer.valid_to}\nOffer: €{self.offer.reference_price} per {self.offer.qu}"
        if self.offer.requires_membership:
            note += " members only"
        return note
