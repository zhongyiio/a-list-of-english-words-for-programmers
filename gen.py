import logging
import random
import sqlite3
from abc import ABCMeta, abstractmethod
from urllib.parse import urlparse, urljoin

import genanki
import nltk
import requests
from bs4 import BeautifulSoup
from nltk import word_tokenize
from nltk.corpus import stopwords
from nltk.corpus import words


class Crawler(metaclass=ABCMeta):
    result = []
    see = set()

    @abstractmethod
    def craw(self, url, deep=0):
        pass


class Parser(metaclass=ABCMeta):
    tokens = []

    @abstractmethod
    def parse(self, content):
        pass


class Freq(metaclass=ABCMeta):
    result = None

    @abstractmethod
    def freq(self, tokens):
        pass


class Generator(metaclass=ABCMeta):
    name = ""

    @abstractmethod
    def generate(self, words):
        pass


class GenericCrawler(Crawler):
    deep = 0

    def __init__(self, deep=1):
        self.deep = deep

    @staticmethod
    def find_current_page_urls(soup):
        urls = set()
        for link in soup.find_all('a'):
            urls.add(link.get('href'))
        return urls

    @staticmethod
    def parse_domain(url):
        return urlparse(url).netloc

    def craw(self, url, deep=0):
        if deep > self.deep:
            return

        deep = deep + 1
        resp = requests.get(url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            self.result.append(resp.text)
            urls = self.find_current_page_urls(soup)
            domain = self.parse_domain(url)
            for _url in urls:
                if not _url:
                    continue
                if not _url.startswith("http"):
                    _url = urljoin(url, _url)
                _domain = self.parse_domain(_url)
                if _url not in self.see and _domain == domain:
                    self.craw(_url, deep)
                    self.see.add(_url)
                else:
                    logging.info("Skip url: %s}", _url)

        else:
            logging.warning("Craw url: %s failed", url)


class HtmlParser(Parser):
    dict_en = set(words.words())
    stopwords_en = set(stopwords.words('english'))

    @staticmethod
    def remove_html_tags(soup):
        return soup.get_text()

    def batch_parse(self, html_list):
        for html in html_list:
            self.parse(html)

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        text = self.remove_html_tags(soup)
        tokens = word_tokenize(text)
        tokens = self.filter_by_dict(tokens)
        tokens = self.filter_by_stopwords(tokens)
        self.tokens += tokens

    def filter_by_stopwords(self, ftokens):
        return [w for w in ftokens if not w in self.stopwords_en]

    def filter_by_dict(self, tokens):
        return [t.lower() for t in tokens if t.lower() in self.dict_en]


class GenericFreq(Freq):

    def freq(self, tokens):
        text = nltk.Text(tokens)
        self.result = nltk.FreqDist(text)


class AnkiGenerator(Generator):
    name = "AnkiGenerator"
    con = sqlite3.connect("./dict/stardict.db")
    cur = con.cursor()
    model = genanki.Model(
        random.randint(100000000, 200000000),
        'Simple Model',
        fields=[
            {'name': 'Word'},
            {'name': 'Phonetic'},
            {'name': 'Translation'},
            {'name': 'Definition'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': '''
        <div class="back">
            <div class="word">{{Word}}</div>
        </div>
          ''',
                'afmt': '''
        <div class="back">
            <div class="word">
                {{Word}} <span class="phonetic">{{Phonetic}}</span>
            </div>
            <div class="translation">
                {{Translation}}
            </div>
            <div class="definition">
                {{Definition}}
            </div>
        </div>
          ''',
            },
        ],
        css='''
            .back {
                height: 100vh;
                width: 100%;
                margin: auto;
                font-family: "Arial", serif;
                display: block;
                font-size: 22px;
                border-radius: 8px;
            }

            .back .word {
                font-size: 2em;
                text-align: center;
                padding: 30px;
            }

            .back .phonetic {
                font-size: 0.5em;
                font-style: italic;
            }

            .back .translation {
                font-family: "Fira Code", serif;
                padding: 5px 30px 5px 30px;
            }

            .back .definition {
                padding: 5px 30px 5px 30px;
            }

            p {
                margin: 10px;
            }
          '''
    )

    def __init__(self, name):
        self.name = name

    def generate(self, freq):
        deck = genanki.Deck(random.randint(100000000, 200000000), self.name)

        for word in list(freq):
            w = self.cur.execute("SELECT * FROM stardict WHERE word = '%s'" % word).fetchone()
            if not w:
                continue
            idx = w[0]
            word = w[1]
            sw = w[2]
            phonetic = w[3] if w[3] else ""
            definition = w[4] if w[4] else ""
            translation = w[5] if w[5] else ""
            pos = w[6]
            collins = w[7]
            oxford = w[8]
            tag = w[9]
            bnc = w[10]
            frq = w[11]
            exchange = w[12]
            detail = w[13]
            audio = w[14]

            note = genanki.Note(model=self.model,
                                fields=[word, phonetic, self.write_html_p(translation), self.write_html_p(definition)])
            deck.add_note(note)
        genanki.Package(deck).write_to_file(self.name + '.apkg')

    @staticmethod
    def write_html_p(s):
        result = ""
        template = "<p>{}</p>\n"
        for p in s.split('\n'):
            result += template.format(p.strip())
        return result


class BBDCGenerator(Generator):
    name = "BBDCGenerator"

    def __init__(self, name):
        self.name = name

    def generate(self, freq):
        with open(self.name + ".txt", "w+") as f:
            for word in list(freq):
                f.write(word + '\n')


if __name__ == '__main__':
    crawler = GenericCrawler(deep=2)
    parser = HtmlParser()
    freqer = GenericFreq()
    # generater1 = BBDCGenerator("SpringFramework")
    # generater2 = AnkiGenerator("SpringFramework")
    # crawler.craw("https://docs.spring.io/spring-framework/docs/current/reference/html/index.html")

    generater1 = BBDCGenerator("SpringBoot")
    generater2 = AnkiGenerator("SpringBoot")
    crawler.craw("https://docs.spring.io/spring-boot/docs/current/reference/html/index.html")

    # generater1 = BBDCGenerator("SpringCloud")
    # generater2 = AnkiGenerator("SpringCloud")
    # crawler.craw("https://docs.spring.io/spring-cloud/docs/current/reference/html/index.html")
    parser.batch_parse(crawler.result)
    freqer.freq(parser.tokens)
    generater1.generate(freqer.result)
    generater2.generate(freqer.result)
