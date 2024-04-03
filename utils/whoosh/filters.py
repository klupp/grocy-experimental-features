import spacy
from whoosh.analysis import Filter


class LemmatizationFilter(Filter):
    def __init__(self, lang='en'):
        if lang == 'de':
            self.nlp = spacy.load('de_core_news_md')
        else:
            self.nlp = spacy.load('en_core_web_sm')
        self.cache = {}

    def __call__(self, tokens):
        for tok in tokens:
            if tok.text in self.cache:
                yield self.cache[tok.text]
                continue
            doc = self.nlp(tok.text)
            for doc_token in doc:
                tok.text = doc_token.lemma_
                self.cache[tok.text] = tok
                yield tok