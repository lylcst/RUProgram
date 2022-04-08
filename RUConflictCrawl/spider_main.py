#-*-coding:utf-8-*- 
# author lyl
from newspider import AljazeeraSpider, DwSpider, ReutersSpider, UpiSpider, ChosunSpider
import configparser
from utils.config_util import Config
import datetime
import os


class SpiderProcessor:

    def __init__(self, setting_file="settings.ini"):
        ini_config = configparser.ConfigParser()
        ini_config.read(setting_file, encoding="utf-8")
        config = Config(ini_config)
        # 获取当前时间字符串
        # time_str_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # if os.path.isfile("record_date"):
        #     with open("record_date.txt", "rt", encoding="utf-8") as f:
        #         from_time = f.read().strip()
        #     if from_time:
        #         config.FROM_TIME = from_time
        # config.TO_TIME = time_str_now
        # with open("record_date.txt", "wt", encoding="utf-8") as f:
        #     f.write(time_str_now)

        # DwSpider(config) ReutersSpider(config) UpiSpider(config) AljazeeraSpider(config),
        self.spider_list = [AljazeeraSpider(config), ChosunSpider(config),DwSpider(config),
                            ReutersSpider(config), UpiSpider(config)]
        # self.spider_list = [ReutersSpider(config)]

    def run(self):
        for spider in self.spider_list:
            spider.run()


if __name__ == '__main__':
    SpiderProcessor().run()

