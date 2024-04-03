import logging
import time
from html.parser import HTMLParser
from io import StringIO

from pint import UnitRegistry
from tqdm import tqdm
from whoosh import writing
from whoosh.analysis import KeywordAnalyzer, SimpleAnalyzer, LanguageAnalyzer
from whoosh.fields import Schema, TEXT, ID
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import MultifieldParser, OrGroup

from grocy.api.grocy_api import GrocyAPI
from utils.whoosh.tokenizers import LemmaTokenizer


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


class GrocyIndex:
    def __init__(self, grocy_api: GrocyAPI):
        self.logger = logging.getLogger("GrocyIndex")
        self.grocy_api = grocy_api
        self.en_analyser = LemmaTokenizer(lang="en")
        self.de_analyser = LemmaTokenizer(lang="de")
        self.mk_analyser = LanguageAnalyzer(lang="mk")
        self.qu_analyser = KeywordAnalyzer(lowercase=True)
        self.product_schema = Schema(name_en=TEXT(stored=True, analyzer=self.en_analyser),
                                     name_de=TEXT(stored=True, analyzer=self.de_analyser),
                                     name_mk=TEXT(stored=True, analyzer=self.mk_analyser),
                                     description=TEXT(stored=True, analyzer=self.en_analyser), id=ID(stored=True))
        if exists_in("index/products"):
            self.product_ix = open_dir("index/products", schema=self.product_schema)
        else:
            self.product_ix = create_in("index/products", schema=self.product_schema)
        self.qu_schema = Schema(name=TEXT(stored=True, analyzer=self.qu_analyser),
                                name_pl=TEXT(stored=True, analyzer=SimpleAnalyzer()), description=TEXT(stored=True),
                                id=ID(stored=True))
        if exists_in("index/qus"):
            self.qu_ix = open_dir("index/qus", schema=self.qu_schema)
        else:
            self.qu_ix = create_in("index/qus", schema=self.qu_schema)
        self.unit_parser = UnitRegistry().Unit

    def query_product_index(self, product_text: str):
        self.logger.debug(f"Querying product index with text: {product_text}")
        with self.product_ix.searcher() as searcher:
            query_parser = MultifieldParser(["name_en", "name_de", "name_mk", "description"], self.product_ix.schema,
                                            group=OrGroup)
            query = query_parser.parse(product_text)
            results = searcher.search(query, limit=1)
            return [dict(result) for result in results]

    def query_qu_index(self, qu_text: str):
        self.logger.debug(f"Querying qu index with text: {qu_text}")
        with self.qu_ix.searcher() as searcher:
            query_parser = MultifieldParser(["name", "name_pl", "description"], self.qu_ix.schema, group=OrGroup)
            query = query_parser.parse(qu_text)
            results = searcher.search(query, limit=1)
            if len(results) == 0:
                try:
                    query = query_parser.parse(str(self.unit_parser(qu_text)))
                    results = searcher.search(query, limit=1)
                except:
                    pass
            return [dict(result) for result in results]

    async def update_product_index(self):
        self.logger.info("Updating product index")
        writer = self.product_ix.writer()
        products = await self.grocy_api.get_products()
        for product in tqdm(products):
            name_en, name_de, name_mk = product['name'].split(" / ")
            if product['description'] is not None:
                description = strip_tags(product['description'])
                writer.add_document(name_en=name_en, name_de=name_de, name_mk=name_mk, description=description,
                                    id=str(product['id']))
            else:
                writer.add_document(name_en=name_en, name_de=name_de, name_mk=name_mk, id=str(product['id']))
        writer.commit(mergetype=writing.CLEAR)

    async def update_qu_index(self):
        self.logger.info("Updating qu index")
        writer = self.qu_ix.writer()
        qus = await self.grocy_api.get_qus()
        for qu in tqdm(qus):
            writer.add_document(name=qu['name'].lower(), id=str(qu['id']), name_pl=qu['name_plural'],
                                description=qu['description'])
        writer.commit(mergetype=writing.CLEAR)
