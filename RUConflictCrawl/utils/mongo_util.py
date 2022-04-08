#-*-coding:utf-8-*- 
# author lyl
import pymongo
import os
import json
import hashlib
from datetime import datetime
from urllib.parse import quote_plus


DIR_PATH = os.path.dirname(os.path.abspath(__name__))
DB_MAP = {"半岛新闻": "半岛新闻", "路透社": "路透社",
          "德国之声": "德国之声", "朝鲜日报": "朝鲜日报", "合众国际社": "合众国际社"}


class MongoDB:

    def __init__(self,
                 database,
                 collection=None,
                 host='localhost',
                 port = 27017,
                 user=None,
                 password=None):
        # 建立连接
        if not user or not password:
            self.client = pymongo.MongoClient(host, port)
        else:
            assert user and password
            uri = \
                "mongodb://%s:%s@%s:%d" % (
                    quote_plus(user), quote_plus(password), host, port)

            self.client = pymongo.MongoClient(uri)
        # 指定数据库
        self.db = self.client[database]
        # 指定集合
        if collection:
            self.collection = self.db[collection]
        else:
            self.collection = None

    def change_collection(self, collection):
        self.collection = self.db[collection]

    def insert(self, *data):
        if len(data) == 0:
            return
        if isinstance(data[0], list):
            assert len(data) == 1
            data = data[0]
        return self.collection.insert_many(data)

    def find(self, data=None, conditions=None, single=False):
        """
            {"time": {"from_time": "2022-3-10 00:00:00",
                    "to_time": "2022-3-22 00:00:00"}
            }
        """
        if not data:
            data = {}
        if conditions:
            for key, item in conditions.items():
                if key == "time":
                    con = {}
                    if item.get("from_time", "").strip():
                        try:
                            from_time = datetime.strptime(item.get("from_time"), "%Y-%m-%d %H:%M:%S")
                        except:
                            from_time = datetime.strptime(item.get("from_time"), "%Y-%m-%dT%H:%M")
                        con["$gte"] = from_time
                    if item.get("to_time", "").strip():
                        try:
                            to_time = datetime.strptime(item.get("to_time"), "%Y-%m-%d %H:%M:%S")
                        except:
                            to_time = datetime.strptime(item.get("to_time"), "%Y-%m-%dT%H:%M")
                        con["$lt"] = to_time
                    if con:
                        data["time"] = con
                elif key == "keyword":
                    data["keyword"] = item
        # 返回列表
        if single:
            cur = [self.collection.find_one(data, {"_id": 0})]
        else:
            cur = list(self.collection.find(data, {"_id": 0}))
            for i in range(len(cur)):
                cur[i]["time"] = cur[i]["time"].strftime("%Y-%m-%d %H:%M:%S")
        return cur

    def update(self, data, new_data, single=False):
        if single:
            self.collection.update_one(data, {'$set': new_data})
        else:
            self.collection.update_many(data, {'$set': new_data})

    def delete(self, data, single=False):
        if single:
            self.collection.delete_one(data)
        else:
            self.collection.delete_many(data)

    def __del__(self):
        self.client.close()


class MongoPipline:
    def __init__(self, db):
        self.dir_path = DIR_PATH
        self.db_map = DB_MAP
        self.db = db

    @classmethod
    def json_load(cls, path):
        with open(path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
        return data

    def writer_json_to_mongo(self, keyword=None, do_filter=False):
        if keyword is None:
            keyword = self.db_map.keys()
        elif isinstance(keyword, str):
            keyword = [keyword]
        for key in keyword:
            self.db.change_collection(self.db_map[key])
            data_path = os.path.join(self.dir_path, 'data', key, 'json')
            json_files = os.listdir(data_path)
            for json_file in json_files:
                data = self.json_load(os.path.join(data_path, json_file))[key]
                if do_filter:
                    self.db.insert(self.filter(data))
                else:
                    self.db.insert(data)

    def load_data_from_mongo(self, keyword=None, conditions=None, do_filter=False):
        if keyword is None:
            keyword = self.db_map.keys()
        elif isinstance(keyword, str):
            keyword = [keyword]
        result = {}
        for key in keyword:
            self.db.change_collection(self.db_map[key])
            tmp = self.db.find(conditions=conditions)
            tmp = tmp if not do_filter else self.filter(tmp)
            result[key] = tmp
        return result

    def clear_mongo_data(self, keyword=None):
        # assert self.db.collection, "MongoDB database collection must be specified"
        if keyword is None:
            keyword = self.db_map.keys()
        elif isinstance(keyword, str):
            keyword = [keyword]
        for key in keyword:
            self.db.change_collection(self.db_map[key])
            self.db.delete({})

    def writer_data_to_mongo(self, data: list, collection: str, do_filter=False):
        self.db.change_collection(collection)
        data = self.filter(data) if do_filter else data
        self.db.insert(data)

    def filter(self, data):
        result = []
        visited_dict = {}
        for item in data:
            info_id = item['title'].strip().lower() + str(item['url']).strip()
            m = hashlib.md5()
            m.update(info_id.encode('utf-8'))
            if not visited_dict.get(m.hexdigest(), None):
                result.append(item)
                visited_dict[m.hexdigest()] = 1
        return result