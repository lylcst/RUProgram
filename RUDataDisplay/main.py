#-*-coding:utf-8-*- 
# author lyl
from mongo_util import MongoDB, MongoPipline
from search_util import SearchEngine
from pymongo import MongoClient
from datetime import datetime


if __name__ == '__main__':
    mongo = MongoDB("RUNewsData", host="10.1.10.12", port=27019)
    mongo_pipline = MongoPipline(mongo)
    search_engine = SearchEngine(mongo_pipline)

    # res = search_engine.find_by_time("2022-3-19 00:00:00", "2022-3-22 00:00:00")
    # res = search_engine.find_by_keyword("俄罗斯 乌克拉")
    conditions = {'time': {"from_time": "2022-3-19 00:00:00"}}
    res = search_engine.find(conditions=conditions)
    print(res)
