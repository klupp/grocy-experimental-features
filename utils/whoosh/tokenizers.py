import spacy
from whoosh.analysis import Tokenizer, Token


class LemmaTokenizer(Tokenizer):
    def __init__(self, lang='en'):
        if lang == 'de':
            self.nlp = spacy.load('de_core_news_md')
        else:
            self.nlp = spacy.load('en_core_web_sm')

    def __call__(self, value, positions=False, chars=False, keeporiginal=False, removestops=True, start_pos=0,
                 start_char=0, tokenize=True, mode='', **kwargs):
        t = Token(positions, chars, removestops=removestops, mode=mode, **kwargs)
        for pos, spacy_token in enumerate(self.nlp(value)):
            if spacy_token.is_punct or spacy_token.is_stop or spacy_token.is_digit:
                continue
            word = str(spacy_token.lemma_.lower())
            if len(word) < 2:
                continue
            t.text = word
            t.boost = 1.0
            if keeporiginal:
                t.original = t.text
            t.stopped = False
            if positions:
                t.pos = start_pos + pos
            if chars:
                t.startchar = start_char + word.start()
                t.endchar = start_char + word.end()
            yield t
