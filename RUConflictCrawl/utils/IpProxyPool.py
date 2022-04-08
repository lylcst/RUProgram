import codecs
import re
import time

import requests
import lxml.html
import lxml.etree as le
import random
from bs4 import BeautifulSoup
import csv
from .ua import FakeChromeUA


class IpProxyPool:
    def __init__(self):
        self.ip_pool = []
        self.proxy_pool = []
        self.headers = {
            'User-Agent': FakeChromeUA.get_ua()
        }

    def quality_test(self):
        pass_proxies = []
        for proxies in self.proxy_pool:
            try:
                requests.get('https://www.ip.cn/', headers=self.headers, proxies=proxies, timeout=2)
            except:
                pass
            else:
                pass_proxies.append(proxies)
        self.proxy_pool.clear()
        self.proxy_pool.extend(pass_proxies)

    def getproxies(self):
        return random.choice(self.proxy_pool) if self.proxy_pool else ''

    def _fetch_ips(self, num_page):
        raise NotImplementedError('')


class KuaidailiIpProxyPool(IpProxyPool):
    def __init__(self, num_page=2):
        super(KuaidailiIpProxyPool, self).__init__()
        self._fetch_ips(num_page)

    def _fetch_ips(self, num_page):
        # https://www.kuaidaili.com/free/inha/1/
        url_list = ['https://www.kuaidaili.com/free/inha/%s/' % str(i) for i in range(1, num_page+1)]
        for url in url_list:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            all_trs = soup.select('tbody > tr')
            for tr in all_trs:
                all_tds = tr.find_all('td')
                ip = all_tds[0].get_text()
                port = all_tds[1].get_text()
                http = all_tds[3].get_text().lower()
                proxies = {http: f"{http}://{ip}:{port}"}
                self.proxy_pool.append(proxies)


class ZhimaIpProxyPool(IpProxyPool):
    def __init__(self, num_page=2):
        super(ZhimaIpProxyPool, self).__init__()
        self._fetch_ips(num_page)

    def _fetch_ips(self, num_page):
        r = requests.get(url='http://webapi.http.zhimacangku.com/getip?num=30&type=1&pro=&city=0&yys=0&port=1&time=1&ts=0&ys=0&cs=0&lb=4&sb=0&pb=4&mr=1&regions=')
        ips = r.text.split('\n')
        for ip in ips:
            ip = ip.strip()
            self.ip_pool.append(ip)


class XiciIpProxyPool(IpProxyPool):
    def __init__(self, num_page=2):
        super(XiciIpProxyPool, self).__init__()
        self._fetch_ips(num_page)

    def _fetch_ips(self, page_num):
        for i in range(1, page_num+1):
            url = 'http://www.xiladaili.com/gaoni/%s/' % str(i)
            response = requests.get(url=url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            all_trs = soup.select('tbody > tr')
            for tr in all_trs:
                all_tds = tr.find_all('td')
                ip = all_tds[0].get_text()
                types = all_tds[1].get_text()
                http = types.split(',')[0] if ',' in types else ''.join(re.findall(r'[A-Za-z]', types))
                http = http.lower()
                proxies = {http: f'{http}://' + ip}
                self.proxy_pool.append(proxies)


if __name__ == '__main__':
    kuaidaili = KuaidailiIpProxyPool().getproxies()
    print(kuaidaili)