#-*-coding:utf-8-*- 
# author lyl

import requests
import time
from lxml import etree
from bs4 import BeautifulSoup
import os, json, re
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
from threading import Thread, Lock
from urllib.parse import quote, unquote, urljoin
from utils.IpProxyPool import KuaidailiIpProxyPool, XiciIpProxyPool, ZhimaIpProxyPool
from utils.bloomfilter import MyBloomFilter
import hashlib
import shutil
from dateutil import parser
from utils.mongo_util import MongoDB

ip_proxies_map = {
    "KuaidailiIpProxyPool": KuaidailiIpProxyPool,
    "XiciIpProxyPool": XiciIpProxyPool,
    "ZhimaIpProxyPool": ZhimaIpProxyPool
}

class Spider:

    def __init__(self, config, headers=None, news_name=None, path=None, cache_dir=None):
        self.config = config
        self.headers = headers
        self.path = path
        self.news_name = news_name
        self.from_time = self.get_timestamp(self.config.FROM_TIME)
        self.to_time = self.get_timestamp(self.config.TO_TIME)
        self.bloom_cache_root = self.config.BLOOM_CACHE_DIR
        self.mutex = Lock()

        if self.bloom_cache_root and not os.path.exists(self.bloom_cache_root):
            os.makedirs(self.bloom_cache_root)
        if self.bloom_cache_root and cache_dir:
            self.bloom = MyBloomFilter(filename=os.path.join(self.bloom_cache_root, cache_dir),
                                       start_fresh=config.FROM_SCRATCH)
        else:
            self.bloom = MyBloomFilter(filename= cache_dir,
                                       start_fresh=config.FROM_SCRATCH)
        if config.FROM_SCRATCH and os.path.exists(self.get_save_path()):
            shutil.rmtree(self.get_save_path())

        # mongodb
        if hasattr(self.config, "MONGO_HOST"):
            logger.info("连接mongodb---host:{}, port: {}, db: {}".format(config.MONGO_HOST,
                                                                       config.MONGO_PORT,
                                                                       config.MONGO_DB_NAME))
            self.mongo = MongoDB(config.MONGO_DB_NAME, collection=self.news_name,
                                   host=config.MONGO_HOST, port=config.MONGO_PORT,
                                 user=config.MONGO_USER, password=config.MONGO_PASSWORD)

        # ip_proxies
        if hasattr(self.config, "PROXY_IP_SOURCE"):
            self.ip_generator = ip_proxies_map[self.config.PROXY_IP_SOURCE]()

    def md5_encode(self, key):
        md5 = hashlib.md5()
        md5.update(key.encode())
        return md5.hexdigest()

    def filter(self, item):
        assert "title" in item and "url" in item
        if not all([item["title"], item["url"], item["content"], item["url"]]):
            return False
        key = self.md5_encode(str(item["title"].strip()) + str(item["url"].strip()))
        if key not in self.bloom:
            self.bloom.add(key)
            return True
        return False

    def request(self, url, params=None, proxies=None):
        if not proxies and hasattr(self, "ip_generator"):
            proxies = self.ip_generator.getproxies()
        res = requests.get(url, params=params, headers=self.headers, proxies=proxies)
        if res.status_code == 200:
            return res

    def get_timestamp(self, time_str):
        return int(time.mktime(time.strptime(time_str, "%Y-%m-%d %H:%M:%S")))

    def get_save_path(self):
        date_from_path = ".".join(list(re.findall("^(\d+)-(\d+)-(\d+)\s(\d+):(\d+)", self.config.FROM_TIME)[0]))
        date_to_path = ".".join(list(re.findall("^(\d+)-(\d+)-(\d+)\s(\d+):(\d+)", self.config.TO_TIME)[0]))
        date_path = "-".join([date_from_path, date_to_path])
        return os.path.join(self.path, date_path)

    def save(self, ret):
        if isinstance(ret, tuple):
            data, keyword = ret
        else:
            data, keyword = ret.result()

        if data and self.filter(data):
            if self.config.TRANSFOR_TIME:
                data["time"] = self.transfer_time(data["time"])
            self.mutex.acquire()
            with open(os.path.join(self.get_save_path(), keyword+".jsl"), mode="at", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
            self.mutex.release()
            print("keyword:{}, title: {}, time: {}".format(keyword, data["title"], data["time"]))

            # 判断需不需要存到mongo数据库中
            if hasattr(self, "mongo"):
                data["keyword"] = keyword
                data["time"] = parser.parse(data["time"])
                self.save_to_mongo(data)

    def save_to_mongo(self, item):
        assert isinstance(item, dict), "data type must be dict"
        ret = self.mongo.insert(item)
        if not ret.acknowledged:
            logger.warning("data insert into mongo failed.")

    def transfer_time(self, time_str):
        raise NotImplementedError()

# 半岛新闻
class AljazeeraSpider(Spider):

    def __init__(self, config, cache_dir=None):

        self.base_url = "https://chinese.aljazeera.net"
        self.api = 'https://chinese.aljazeera.net/graphql?wp-site=chinese&operationName=SearchQuery&variables={"query":"俄罗斯","start":11,"sort":"relevance"}&extensions={}'
        self.headers = {
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en,zh-CN;q=0.9,zh;q=0.8",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "cookie": "ak_bmsc=EFE9C2CBDA01A805572AEC076DB821DF~000000000000000000000000000000~YAAQcw/dWDMK+2V/AQAA1M44bw/SpsSdaKp46mydYjb83aMGGTkX8K9x3xLf33Z6BdjbY8uIIb/rZbP+A7fW3DMed331mJ6seAbLOG0uZch33DZEB8Is7o040/7IfsB0g8wnJ1jOv6LLzhVdulcB2kXTSc/wij7CXW2uZgwwtIzq9o8jjvGzyYg37MAuVYAkOHJNUNHKqEnc9FYBqr7CTNZiHvKruSv7nhE6CQkUPsDr2Doofw9m/enBzAj1SKaG4NYtd1loF33UydQofQI51A3ArNgdAO5PwytTyALHiQzNhmmskmRNpC4VTR1O4bFMOvbHDu9jKgGZe6HLd02JURZYRpwjOazvyrKvUcp5xD0YSEkPlqKiFaR34xhW+Z09SahqNwNxPciOmTAA; _ga=GA1.2.740860849.16468384",
            "pragma": "no-cache",
            "referer": "https://chinese.aljazeera.net/search/%E4%BF%84%E7%BD%97%E6%96%AF",
            "sec-ch-ua": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"98\", \"Google Chrome\";v=\"98\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36",
            "wp-site": "chinese"
        }
        self.keywords = config.CH_KEYWORDS
        self.news_name = "半岛新闻"
        self.path = os.path.join(config.DATA_ROOT_PATH, self.news_name)
        self.dalone = lambda x: x[0] if x else x

        self.flag = True

        cache_dir = "AljazeeraSpider.cache"
        super().__init__(config, self.headers, self.news_name, self.path, cache_dir)
        if not os.path.exists(self.get_save_path()):
            os.makedirs(self.get_save_path())

    def transfer_time(self, time_str):
        """
        :param time_str: 2022年03月07日 00:00
        :return: 2022-03-07 00:00
        """

        tmp = list(re.findall("^(\d+)年(\d+)月(\d+)日\s(\d+):(\d+)", time_str + " 00:00")[0])
        result = "-".join(tmp[:3]) + " " + ":".join(tmp[3:]) + ":" + "00"

        return result

    def get_params(self, keyword, page):
        js = {"query": keyword, "start": page, "sort": "date"}
        params = {
            "wp-site": "chinese",
            "operationName": "SearchQuery",
            "variables": json.dumps(js),
            "extensions": ""
        }
        return params

    def get_news_content(self, url, title, keyword):
        content = self.request(url).text
        text = etree.HTML(content).xpath('//div[@class="wysiwyg wysiwyg--all-content css-grfpkn"]/p/text()')
        t_time = self.dalone(etree.HTML(content).xpath('//div[@class="article-dates"]/div/span[@aria-hidden="true"]/text()'))
        text = "\n".join([t.strip() for t in text if t])
        if not text or not t_time:
            return
        timeStamp = self.get_timestamp(self.transfer_time(t_time))
        if timeStamp >= self.from_time:
            if timeStamp <= self.to_time:
                data = {
                    "title": title,
                    "time": t_time,
                    "url": unquote(url),
                    "content": text
                }
                self.save((data, keyword))
        else:
            self.flag = False
            exit(-1)

    def get_news_list(self, keyword, page):

        try:
            json_data = self.request("https://chinese.aljazeera.net/graphql", params=self.get_params(keyword, page)).json().get("data")["searchPosts"]
            thread_list = []
            for item in json_data.get("items", []):
                link = item["link"]
                title = item["title"]
                t = Thread(target=self.get_news_content, args=(link, title, keyword))
                t.start()
                thread_list.append(t)
            for t in thread_list:
                t.join()
        except Exception as e:
            logger.error(e)


    def run(self):
        for keyword in self.keywords:
            logger.info("{}---keyword: {}".format(self.news_name, keyword))
            start_id = 1
            while True and self.flag:
                self.get_news_list(keyword, start_id)
                time.sleep(2)
                start_id += 10
            self.flag = True

# 德国之声
class DwSpider(Spider):

    def __init__(self, config, cache_dir=None):
        self.base_url = "https://www.dw.com/"
        self.api = "https://www.dw.com/search/"
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36",
        }
        self.keywords = config.EN_KEYWORDS
        self.news_name = "德国之声"
        self.path = os.path.join(config.DATA_ROOT_PATH, self.news_name)
        self.dalone = lambda x: x[0] if x else x

        self.thread_num = 20

        self.rules = {
            "title": '//div[@class="col3"]/h1/text()',
            "url": ".//a/@href",
            "content": '//div[@class="col3"]/div[@class="group"]/div[@class="longText"]/p//text()',
            "time": '//ul[@class="smallList"]/li[1]/text()'
        }
        cache_dir = "DwSpider.cache"
        super().__init__(config, self.headers, self.news_name, self.path, cache_dir)
        self.from_time = self.get_param_time(config.FROM_TIME)
        self.to_time = self.get_param_time(config.TO_TIME)
        if not os.path.exists(self.get_save_path()):
            os.makedirs(self.get_save_path())

    def get_param_time(self, time_str):
        tmp = list(re.findall("^(\d+)-(\d+)-(\d+)\s", time_str)[0])
        tmp.reverse()
        return ".".join(tmp)

    def transfer_time(self, time_str):
        '''
        :param time_str: 22.03.2022
        :return: 2022-03-22 00:00:00
        '''
        time_str_ls = time_str.split(".")
        time_str_ls.reverse()
        return "-".join(time_str_ls) + " 00:00:00"

    def get_params(self, keyword, page):
        params = {
            "languageCode": "en",
            "item": keyword,
            "searchNavigationId": "9097",
            "from": self.from_time,
            "to": self.to_time,
            "sort": "DATE",
            "resultsCounter": page
        }
        return params

    def get_news_content(self, url, title, keyword):
        try:
            content = self.request(url).text
            title = self.dalone(etree.HTML(content).xpath(self.rules["title"]))
            text = etree.HTML(content).xpath(self.rules["content"])
            t_time = self.dalone(etree.HTML(content).xpath(self.rules["time"]))
            text = "\n".join([t.strip() for t in text if t])

            if not text or not t_time or not title:
                return {},""
            t_time = t_time.strip()
            title = title.strip()
            data = {
                "title": title,
                "time": t_time,
                "url": url,
                "content": text
            }
            return data, keyword
        except Exception as e:
            logger.error(e)
            return {}, ""

    def get_news_list(self, keyword, page):

        res = self.request(self.api, params=self.get_params(keyword, page))
        item_list = etree.HTML(res.text).xpath("//div[@class='searchResult']")
        executor = ThreadPoolExecutor(max_workers=self.thread_num)
        for item in item_list:
            url = urljoin(self.base_url, self.dalone(item.xpath(self.rules["url"])))
            future = executor.submit(self.get_news_content, url=url, title="", keyword=keyword)
            future.add_done_callback(self.save)

    def run(self, thread_num=20):
        self.thread_num = thread_num
        for keyword in self.keywords:
            logger.info("{}---keyword: {}".format(self.news_name, keyword))
            self.get_news_list(keyword, 200)
            time.sleep(2)

# 路透社
class ReutersSpider(Spider):

    def __init__(self, config, cache_dir=None):
        self.base_url = "https://www.reuters.com"
        self.api = 'https://www.reuters.com/pf/api/v3/content/fetch/articles-by-search-v2'
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36",
        }
        self.keywords = config.EN_KEYWORDS
        self.news_name = "路透社"
        self.path = os.path.join(config.DATA_ROOT_PATH, self.news_name)

        self.flag = True
        self.thread_num = 20

        self.rules = {
            "content": '//div[@class="article-body__content__3VtU3 paywall-article"]/p[contains(@data-testid, "paragraph")]/text()',
        }
        cache_dir = "ReutersSpider.cache"
        super().__init__(config, self.headers, self.news_name, self.path, cache_dir)
        if not os.path.exists(self.get_save_path()):
            os.makedirs(self.get_save_path())

    def transfer_time(self, time_str):
        return time_str

    def get_params(self, keyword, offset=0):
        # query = {"keyword":keyword, "offset":offset, "orderby":"display_date:desc", "size":100, "website":"reuters"}
        # params = {
        #     "query": json.dumps(query),
        #     "d": 79,
        #     "_website": "reuters"
        # }
        params = '?query={"keyword":"%s","offset":%d,"orderby":"display_date:desc","size":100,"website":"reuters"}&d=82&_website=reuters' % (keyword, offset)
        return params

    def get_news_content(self, url, **kwargs):
        try:
            content = self.request(url).text
            text = etree.HTML(content).xpath(self.rules["content"])
            t_time = kwargs.pop("time", "")
            title = kwargs.pop("title", "")
            keyword = kwargs.pop("keyword", "")
            text = "\n".join([t.strip() for t in text if t])

            if not text or not t_time or not title:
                return {},""
            assert keyword
            data = {
                "title": title,
                "time": t_time,
                "url": url,
                "content": text
            }
            return data, keyword
        except Exception as e:
            logger.error(e)
            return {}, ""

    def get_news_list(self, keyword, offset):
        try:
            res = self.request(self.api + self.get_params(keyword, offset))
            item_list = res.json().get("result")
            executor = ThreadPoolExecutor(max_workers=self.thread_num)
            for item in item_list.get("articles", []):
                title = item.get("title")
                url = urljoin(self.base_url, item.get("canonical_url", ""))
                # 2022-03-10T04:40:32.398Z
                updated_time = item.get("updated_time").split(".")[0].replace("T", " ")
                time_stamp = self.get_timestamp(updated_time)
                if time_stamp >= self.from_time:
                    if time_stamp <= self.to_time:
                        future = executor.submit(self.get_news_content, url=url, title=title, keyword=keyword, time=updated_time)
                        future.add_done_callback(self.save)
                else:
                    self.flag = False
                    break
        except Exception as e:
            logger.error(e)

    def fetch(self, keyword):
        offset = 0
        while True and self.flag:
            self.get_news_list(keyword, offset)
            time.sleep(2)
            offset += 10
        return None

    def run(self, thread_num=10):
        self.thread_num = thread_num
        for keyword in self.keywords:
            logger.info("{}---keyword: {}".format(self.news_name, keyword))
            self.fetch(keyword)

# 合众国际社
class UpiSpider(Spider):

    def __init__(self, config, cache_dir=None):
        self.base_url = "https://www.upi.com"
        self.api = 'https://www.upi.com/search/'
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36",
            "cookie": 'agent_id=1ff83a03-a2fc-4769-9174-ba640c7c39d5; session_id=1209d5a1-9d8d-48c5-9fdd-c11e60e7a031; session_key=d6c691f2e746712990a5fdf5ac06398b968e6634; gatehouse_id=1a73a2be-e69f-4c5e-8612-60c49c552bfe; geo_info={"countryCode":"FR","country":"FR","field_d":"c-dedie.net","field_n":"cp","trackingRegion":"Europe","cacheExpiredTime":1647589765536,"region":"Europe","fieldN":"cp","fieldD":"c-dedie.net"}|1647589765536; _sp_v1_uid=1:525:2a225c84-f9a2-44e6-9588-396517f0fa95; _sp_v1_csv=null; _sp_v1_lt=1:; ccpaUUID=c32a6f33-1231-4bb9-815d-84e0fa86c884; dnsDisplayed=true; ccpaApplies=true; signedLspa=false; _reg-csrf=s:-mp8sUbR4akPmZi-zJf_thtL.r6EGVi4HDmZ7Wutx14GqtFu6rxP5IFxoXefbbywVWP4; _user-status=anonymous; pxcts=cb02568e-a10f-11ec-9b81-574c4b4a6d76; _pxvid=cb024bc3-a10f-11ec-9b81-574c4b4a6d76; _sp_krux=true; consentUUID=52c3a722-4780-41bd-903e-a5d676fc2927_5; euconsent-v2=CPVrfb_PVrfb_AGABCENCGCgAP_AAGPAAAqIH9oB9CpGCTFDKGh4AIsAEAQXwBAEAOAAAAABAAAAAAgQAIwCAEASAACAAAACAAAAIAIAAAAAEAAAAEAAQAAAAAFAAAAEAAAAAAAAAAAAAAAAAAAAAIEAAAAAAUAAABAAgEAAABIAQAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgYtARAAcACEAHIAPwAvgCOAIHAQcBCACIgEWALqAYEA14B1AFlALzAYsAUMgCABMAEcARwBeYSAqAAsACoAGQAOAAgABkADSAIgAigBMACeAH4AQgAjgBSgDKAHeAPYAjgBKQDiAMkFQBQAmACOAI4ApsBeY6AyAAsACoAGQAOAAgABcADIAGkARABFACYAE8AMQAfgBHACYAFGAKUAZQA7wB7AEcAJSAcQA6gDJBwAEAC5CAUAAsADIALgAmABiAEcAO8AjgBKQDqEoBgACwAMgAcACIAEwAMQAjgBRgClAHeARwA6hIACABcpATAAWABUADIAHAAQAAyABpAEQARQAmABPADEAH4AUYApQBlADvAI4ASkBkhQACABc.YAAAAAAAAAAA; _sp_v1_opt=1:login|true:last_id|11:; bbgconsentstring=req1fun1pad1; bdfpc=004.9520457485.1646984986040; _gcl_au=1.1.588929971.1646984986; consentUUID=52c3a722-4780-41bd-903e-a5d676fc2927_5; __gads=ID=8d005339cf4cedad:T=1646984987:S=ALNI_Mbu438ghoat8O0aQzJjdiJszbnDjw; _ga=GA1.2.1907031709.1646984987; _gid=GA1.2.2006757276.1646984988; _cc_id=6fb28b279c88af9b4e952eb6b8fd351e; _rdt_uuid=1646984999426.9666e7f1-49fb-40e1-9620-73b00a53d909; _li_dcdm_c=.bloomberg.com; _lc2_fpi=b1166d620485--01fxvz9rw8wfak2rv2jbxp7qgf; _sp_v1_ss=1:H4sIAAAAAAAAAItWqo5RKimOUbLKK83J0YlRSkVil4AlqmtrlXRIVRZNJCMPxDCojcVlJD0ksDkbnzdHDaLEoFgAzRDu9nMCAAA=; _sp_v1_consent=1!1:1:1:0:0:0; optimizelyEndUserId=oeu1646985018026r0.4445593921187527; _scid=766fd56b-8060-4051-a307-d96ad0fff9b6; _parsely_session={"sid":1,"surl":"https://www.bloomberg.com/europe","sref":"","sts":1646985024866,"slts":0}; _parsely_visitor={"id":"pid=256c4892666dfe1a2c622bbdee11591e","session_count":1,"last_session_ts":1646985024866}; _fbp=fb.1.1646985026036.980128035; __sppvid=40f9064b-cce9-4ce2-b6da-9a2f1339f6ba; _tb_sess_r=https://www.bloomberg.com/europe; _sp_v1_data=2:439307:1646984967:0:6:0:6:0:0:_:-1; panoramaId_expiry=1647072056716; _tb_t_ppg=https://www.bloomberg.com/news/articles/2022-03-10/russia-ukraine-war-key-developments-in-the-ongoing-conflict; _reg-csrf-token=Gx3kxqkO-BuHpSGtV0J6aDa9Na2t_q-qtpq0; _last-refresh=2022-3-11 8:3; _uetsid=d5f9e920a10f11eca10cc191b2fee319; _uetvid=d5fbbe20a10f11ecbe29539c9c026427; trc_cookie_storage=taboola%20global%3Auser-id=fabf096f-05b1-4bad-ac0f-b9c2a10e30cc-tuct81ce3f4; _px3=dd358baf062534a5f8bacf63b9c0e1a47d0f699b68a652930564c9797e063847:7+4uskvI9AC7Py5fhRXTrFAGQg3PNTg7wC2eWU7D0IImDwfGJL86BhZj9w70AY1QDQtCGnyV9k4AJL5CHY24+Q==:1000:G5l3aWfvQitH7mElBidbefzLuRCLY5Akgdte19KffWh60GkKhnD8Oy+UVtCSP2wK6JBG/QJ5tiIr7Q3sGsmtT/xFoCb5BbG/apIG2aGcCG2g9tkMiBZISCar9L01+jrBP9zTfOVtTwC1RZ50YlaLEkEoYpwpyQsiQSUA7qIKlXvVlRI+mgaAm8CAsI4LsInaBV8e5sJgeR/6nMosUYqT6A==; _px2=eyJ1IjoiZjMyZWJhNzAtYTEwZi0xMWVjLWE5YzgtNDkyNjRiYTY1ODM1IiwidiI6ImNiMDI0YmMzLWExMGYtMTFlYy05YjgxLTU3NGM0YjRhNmQ3NiIsInQiOjE2NDY5ODY3NzU3ODAsImgiOiI3NGQyODQ2MDFlN2YxNjRiZDA0ZGIwNDM1NGQyMmNjMTQ2YjZkZWM2NjhmNGFhMTRiOTg5OWUwMjhhMTU2MTZiIn0=; _pxde=0dd202c12c0efc87be51e59b825c2fa6dd8af4a6a2f679505b7b9c8c0a91cb62:eyJ0aW1lc3RhbXAiOjE2NDY5ODY0NzU3ODAsImZfa2IiOjAsImlwY19pZCI6W119; _gat_UA-11413116-1=1'
        }
        self.keywords = config.EN_KEYWORDS
        self.news_name = "合众国际社"
        self.path = os.path.join(config.DATA_ROOT_PATH, self.news_name)

        self.dalone = lambda x: x[0] if x else ""

        self.flag = 10
        self.thread_num = 20

        self.rules = {
            "title": './/div[@class="title"]/text()',
            "url": ".//a/@href",
            "time": '//div[@class="article-date"]/text()',
            "content": '//article[@itemprop="articleBody"]/p/text()'
        }
        cache_dir = "UpiSpider.cache"
        super().__init__(config, self.headers, self.news_name, self.path, cache_dir)
        if not os.path.exists(self.get_save_path()):
            os.makedirs(self.get_save_path())

    def get_params(self, keyword, offset=1):
        # ss=russia&s_l=articles&offset=1&sort=date
        params = {
            "ss": keyword,
            "s_l": "articles",
            "offset": offset,
            "sort": "date"
        }
        return params

    def transfer_time(self, time_str):
        if not time_str.strip():
            return ""
        # March 10, 2022 / 4:09 PM
        month_map = {
            "JAN.": "01",
            "FEB.": "02",
            "MARCH": "03",
            "APRIL": "04",
            "MAY": "05",
            "JUNE": "06",
            "JULY": "07",
            "AUG.": "08",
            "SEPT.": "09",
            "OCT.": "10",
            "NOV.": "11",
            "DEC.": "12"
        }
        time_str = time_str.upper()
        for key, value in month_map.items():
            if key in time_str:
                time_str = time_str.replace(key, value)
                break
        # 03 10, 2022 / 11:23

        tmp = re.findall("(\d+)\s(\d+), (\d+) / (\d+):(\d+)", time_str)[0]
        if len(tmp) != 5:
            return ""
        new_time_str = tmp[2] + "-" + tmp[0] + "-" + tmp[1] + " " + tmp[3] + ":" + tmp[4]
        return new_time_str + ":00"

    def get_news_content(self, url, **kwargs):
        content = self.request(url).text
        t_time = self.dalone(etree.HTML(content).xpath(self.rules["time"])).strip()
        # text = etree.HTML(content).xpath(self.rules["content"])
        text = [p.get_text() for p in BeautifulSoup(content, "html.parser").find("article", {"itemprop": "articleBody"}).find_all("p")]
        title = kwargs.pop("title", "")
        keyword = kwargs.pop("keyword", "")
        text = "\n".join([t.strip() for t in text if t.strip()])
        if not text or not t_time or not title:
            return {}, ""
        assert keyword
        if self.get_timestamp(self.transfer_time(t_time)) >= self.from_time:
            if self.get_timestamp(self.transfer_time(t_time)) <= self.to_time:
                data = {
                    "title": title,
                    "time": t_time,
                    "url": url,
                    "content": text
                }
                return data, keyword
        else:
            self.flag -= 1
        return {}, ""

    def get_news_list(self, keyword, offset):
        try:
            res = self.request(self.api, params=self.get_params(keyword, offset))
            item_list = etree.HTML(res.text).xpath('//div[@class="row story list"]/div')
            executor = ThreadPoolExecutor(max_workers=self.thread_num)
            for item in item_list:
                title = self.dalone(item.xpath(self.rules["title"]))
                url = self.dalone(item.xpath(self.rules['url']))
                future = executor.submit(self.get_news_content, url=url, title=title, keyword=keyword)
                future.add_done_callback(self.save)
        except Exception as e:
            logger.error(e)

    def run(self, thread_num=5):
        self.thread_num = thread_num
        for keyword in self.keywords:
            logger.info("{}---keyword: {}".format(self.news_name, keyword))
            page = 1
            while self.flag > 0:
                self.get_news_list(keyword, page)
                page += 1
            self.flag = 10

# 朝鲜日报
class ChosunSpider(Spider):

    def __init__(self, config, cache_dir=None):
        self.base_url = "http://english.chosun.com/"
        self.api = 'http://english.chosun.com/svc/list_in/search.html'
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36",
        }
        self.keywords = config.EN_KEYWORDS
        self.news_name = "朝鲜日报"
        self.path = os.path.join(config.DATA_ROOT_PATH, self.news_name)

        self.flag = True
        self.thread_num = 20

        self.rules = {
            "title": './/dt/a/text()',
            "url": './/dt/a/@href',
            "time": './/span[@class="date"]//text()',
            "content": '//div[@class="par"]/p/text()'
        }
        self.dalone = lambda x: x[0] if x else ""
        self.item_key = ""

        cache_dir = "ChosunSpider.cache"
        super().__init__(config, self.headers, self.news_name, self.path, cache_dir)
        if not os.path.exists(self.get_save_path()):
            os.makedirs(self.get_save_path())

    def get_params(self, keyword, page=1):
        # query=russia&sort=1&pn=2
        params = {
            "query": keyword,
            "page": page,
            "sort": 1
        }
        return params

    def transfer_time(self, time_str):
        '''
        :param time_str: %Y/%m/%d %H:%M
        :return: %Y-%m-%d %H:%M:%S
        '''
        time_str = time_str.replace("/", "-")
        time_str += ":00"
        return time_str

    def get_news_content(self, url, **kwargs):
        content = self.request(url).text
        text = etree.HTML(content).xpath(self.rules["content"])
        t_time = kwargs.pop("time", "")
        title = kwargs.pop("title", "")
        keyword = kwargs.pop("keyword", "")
        text = "\n".join([t.strip() for t in text if t])

        if not text or not t_time or not title:
            return {}, ""
        assert keyword

        data = {
            "title": title,
            "time": t_time,
            "url": url,
            "content": text
        }
        return data, keyword

    def get_news_list(self, keyword, page):
        try:
            res = self.request(self.api, params=self.get_params(keyword, page))
            item_list = etree.HTML(res.text).xpath('//div[@id="list_area"]/dl')

            item_key = ""
            for item in item_list:
                title = self.dalone(item.xpath(self.rules["title"])).strip()
                t_time = " ".join(item.xpath(self.rules["time"]))
                url = self.dalone(item.xpath(self.rules["url"]))
                item_key += title.strip()
                # logger.info("时间: {}, title: {}".format(t_time, title))
                time_stamp = self.get_timestamp(self.transfer_time(t_time))
                executor = ThreadPoolExecutor(max_workers=self.thread_num)
                if time_stamp >= self.from_time:
                    if time_stamp <= self.to_time:
                        future = executor.submit(self.get_news_content, url=url, title=title, keyword=keyword, time=t_time)
                        future.add_done_callback(self.save)
                else:
                    self.flag = False
            if item_key == self.item_key:
                self.flag = False
            self.item_key = item_key
        except Exception as e:
            logger.info(e)

    def run(self, thread_num=5):
        self.thread_num = thread_num
        for keyword in self.keywords:
            logger.info("{}---keyword: {}".format(self.news_name, keyword))
            page = 1
            while self.flag:
                self.get_news_list(keyword, page)
                page += 1
            self.flag = True
