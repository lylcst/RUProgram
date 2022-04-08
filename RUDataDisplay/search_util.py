#-*-coding:utf-8-*- 
# author lyl

class SearchEngine:

    def __init__(self, mongo_pipline):
        self.mongo_pipline = mongo_pipline

    def find_by_time(self, from_time: str, to_time: str, collection_key=None, do_filter=False):
        condition = {"time": {"from_time": from_time, "to_time": to_time}}
        result = self.mongo_pipline.load_data_from_mongo(keyword=collection_key, conditions=condition, do_filter=do_filter)
        return result

    def find_by_keyword(self, keyword, collection_key=None, do_filter=False):
        condition = {"keyword": keyword}
        result = self.mongo_pipline.load_data_from_mongo(keyword=collection_key, conditions=condition, do_filter=do_filter)
        return result

    def find(self, collection_key=None, conditions=None, single=False, sort=None, do_filter=False):
        result = self.mongo_pipline.load_data_from_mongo(keyword=collection_key, conditions=conditions, single=single, sort=sort, do_filter=do_filter)
        return result


