import logging

from tqdm import tqdm
from whoosh import writing
from whoosh.fields import Schema, TEXT, ID
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import MultifieldParser

from utils.whoosh.tokenizers import LemmaTokenizer


class OfferIndex:
    def __init__(self):
        self.logger = logging.getLogger('OfferIndex')
        self.my_analyser = LemmaTokenizer("de")
        # self.my_analyser = LanguageAnalyzer(lang='de')
        self.offer_schema = Schema(product_name=TEXT(stored=True, analyzer=self.my_analyser, field_boost=2),
                                   store_name=TEXT(stored=True, analyzer=self.my_analyser),
                                   brand_name=TEXT(stored=True, analyzer=self.my_analyser, field_boost=2),
                                   category=TEXT(stored=True, analyzer=self.my_analyser, field_boost=3),
                                   description=TEXT(stored=True, analyzer=self.my_analyser), id=ID(stored=True))
        if exists_in("index/offers"):
            self.offer_ix = open_dir("index/offers", schema=self.offer_schema)
        else:
            self.offer_ix = create_in("index/offers", self.offer_schema)

    def query_offer_index(self, product_text: str):
        self.logger.debug(f"Query: {product_text}")
        with self.offer_ix.searcher() as searcher:
            query_parser = MultifieldParser(["product_name", "brand_name", "store_name", "category"],
                                            self.offer_ix.schema)
            query = query_parser.parse(product_text)
            results = searcher.search(query, limit=None)
            return [dict(result) for result in results]

    def update_offer_index(self, offers):
        self.logger.info("Updating Index")
        writer = self.offer_ix.writer()
        for offer in tqdm(offers):
            writer.add_document(product_name=str(offer['product']['name'].lower()),
                                brand_name=str(offer['brand']['name']),
                                store_name=str(", ".join([adv['name'] for adv in offer['advertisers']])),
                                category=str(", ".join([cat['name'] for cat in offer['categories']])),
                                description=str(offer['description']), id=str(offer['id']))
        writer.commit(mergetype=writing.CLEAR)
