from typing import List, Dict

from offers.model import OfferPreference, Offer


class BrandOfferPreference(OfferPreference):
    def __init__(self, preferred_brands: Dict[str, float] | List[str]):
        super().__init__()
        if type(preferred_brands) is list:
            self.preferred_brands = {brand.lower().strip(): 1.0 for brand in preferred_brands}
        elif type(preferred_brands) is dict:
            self.preferred_brands = {brand[0].lower().strip(): brand[1] for brand in preferred_brands}
        else:
            raise Exception("invalid type of preferred_brands. Allowed types List[str] and Dict[str,float]")

    def get_preference(self, offer: Offer) -> float:
        if offer.brand_name is None:
            return 2.0
        return self.preferred_brands.get(offer.brand_name.lower().strip(), 2.0)

    def get_preference_name(self):
        return "brand"
