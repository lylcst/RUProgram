#-*-coding:utf-8-*- 
# author lyl

'''
DATA_ROOT_PATH = data
BLOOM_CACHE_DIR = cache_dir
FROM_TIME = 2022-03-20 00:00:00
TO_TIME = 2022-03-22 23:59:59
CH_KEYWORDS = ["俄罗斯 乌克拉"]
EN_KEYWORDS = ["Russia Ukraine"]

'''

class Config:

    def __init__(self, config):
        self.config = config
        # 基础配置
        self.DATA_ROOT_PATH = config.get("base_info", "DATA_ROOT_PATH")
        self.BLOOM_CACHE_DIR = config.get("base_info", "BLOOM_CACHE_DIR")
        self.FROM_TIME = config.get("base_info", "FROM_TIME")
        self.TO_TIME = config.get("base_info", "TO_TIME")
        self.CH_KEYWORDS = eval(config.get("base_info", "CH_KEYWORDS"))
        self.EN_KEYWORDS = eval(config.get("base_info", "EN_KEYWORDS"))
        self.TRANSFOR_TIME = True if config.get("base_info", "TRANSFOR_TIME") == "true" else False

        # 增量爬取配置
        assert config.get("incremental", "FROM_SCRATCH") in ["true", "false"]
        self.FROM_SCRATCH = True if config.get("incremental", "FROM_SCRATCH") == "true" else False

        # monogo数据库配置
        if "mongodb" in config.sections() and config.get("mongodb", "ENABLE") == "true":
            self.MONGO_HOST = config.get("mongodb", "HOST")
            self.MONGO_PORT = int(config.get("mongodb", "PORT"))
            self.MONGO_DB_NAME = config.get("mongodb", "DB_NAME")
            self.MONGO_USER = config.get("mongodb", "USER")
            self.MONGO_PASSWORD = config.get("mongodb", "PASSWORD")

        # ip代理配置
        if "ip_proxies" in config.sections() and config.get("ip_proxies", "ENABLE") == "true":
            self.PROXY_IP_SOURCE = config.get("ip_proxies", "PROXY_IP_SOURCE")

