#-*-coding:utf-8-*- 
# author lyl
import spacy
from mongo_util import MongoDB, MongoPipline
from search_util import SearchEngine
import re
import string
from concurrent.futures import ThreadPoolExecutor, as_completed

class Analysis:

    def __init__(self, data: dict):
        assert isinstance(data, dict) and len(data) == 1
        self.data = data
        self.key_name = list(self.data.keys())[0]
        self.stop_words = ["U S"]
        self.executor = ThreadPoolExecutor(max_workers=10)

    def _clean_text(self, text):
        text = re.sub('<.*?>+', ' ', text)
        text = re.sub('[%s]' % re.escape(string.punctuation), ' ', text)
        text = re.sub('\n', ' ', text)
        text = re.sub('\w*\d\w*', ' ', text)
        return text

    def __ner_for_aingle_text(self, model, content):
        doc = model(self._clean_text(content))
        ner_collection = {"Location": [], "Person": [], "Date": [], "Quantity": [], "Organisation": []}
        for ent in doc.ents:
            if str(ent.label_) == "GPE":
                ner_collection['Location'].append(ent.text)
            elif str(ent.label_) == "DATE":
                ner_collection['Date'].append(ent.text)
            elif str(ent.label_) == "PERSON":
                ner_collection['Person'].append(ent.text)
            elif str(ent.label_) == "ORG":
                ner_collection['Organisation'].append(ent.text)
            elif str(ent.label_) == "QUANTITY":
                ner_collection['Quantity'].append(ent.text)
            else:
                continue
        return ner_collection


    def ner(self):
        model = spacy.load('en_core_web_sm')
        all_task = []
        for article in self.data[self.key_name]:
            content = article.get("content", "")
            future = self.executor.submit(self.__ner_for_aingle_text, model=model, content=content)
            all_task.append(future)

        ner_collection = {"Location": [], "Person": [], "Date": [], "Quantity": [], "Organisation": []}
        for task in as_completed(all_task):
            data = task.result()
            for key, value in data.items():
                ner_collection[key].extend(data[key])

        for key, value in ner_collection.items():
            ner_collection[key] = self.__get_freq_dict(value)
        return ner_collection


    def __get_freq_dict(self, data: list):
        word_freq_dict = {}
        for word in data:
            if word not in self.stop_words:
                word_freq_dict[word] = word_freq_dict.get(word, 0) + 1
        word_freq_dict = sorted(word_freq_dict.items(), key=lambda x: x[1], reverse=True)[:8]

        return [list(t)for t in tuple(zip(*word_freq_dict))]



if __name__ == '__main__':
    mongo = MongoDB("RUNewsData", host="120.53.228.150", port=27017)
    mongo_pipline = MongoPipline(mongo)
    search_engine = SearchEngine(mongo_pipline)
    res = {"合众国际社": search_engine.find("合众国际社")["合众国际社"][:10]}
    ana = Analysis(res)
    print(ana.ner())

