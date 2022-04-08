#-*-coding:utf-8-*- 
# author lyl
import pandas as pd
import os, json
import math

class DataProcess:

    def __init__(self, data):
        self.data = data
        self.static_root = 'static'

    def to_json(self):
        path = os.path.join(self.static_root, "result.json")
        with open(path, "wt", encoding="utf-8") as f:
            f.write(json.dumps(self.data, ensure_ascii=False, indent=4))
        return path

    def to_xlsx(self):
        path = os.path.join(self.static_root, "result.xlsx")
        key = list(self.data.keys())[0]
        df = pd.DataFrame()
        for item in self.data.get(key):
            df = df.append([item])
        df.to_excel(path, index=False)
        return path

class Page:
    def __init__(self,
                 data: dict,
                 page_number,
                 page_size):
        """
        :param data: {"路透社": [{},{}]}
        """
        assert isinstance(data, dict) and len(data) == 1
        self.data = data
        self.key_name = list(self.data.keys())[0]
        self.totalRecord = len(self.data.get(self.key_name))
        self.page_number = page_number
        self.page_size = page_size

    def getTotalPage(self):
        return int(math.ceil(self.totalRecord / self.page_size))

    def getIndex(self):
        if self.page_number <= self.getTotalPage():
            return (self.page_number - 1)*self.page_size
        else:
            return (self.getTotalPage() - 1)*self.page_size

    def get_data(self):
        res_data = {self.key_name: self.data[self.key_name][self.getIndex():self.getIndex()+self.page_size]}
        return res_data