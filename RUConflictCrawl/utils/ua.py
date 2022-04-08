# -*-coding:utf-8-*-
# author lyl
import random


class FakeChromeUA:
    first_num = random.randint(55, 62)
    third_num = random.randint(0, 3200)
    fourth_num = random.randint(0, 140)
    os_type = [
        '(windows NT 6.1; WOW64)', '(windows NT 10.0; WOW64)', '(Windows NT 10.0; Win64; x64)'
        '(X11; Linux x86_64)', '(Macintosh; Intel Mac OS X 10_12_6)'
    ]
    chrome_version = 'Chrome/{}.0.{}.{}'.format(first_num, third_num, fourth_num)

    @classmethod
    def get_ua(cls):
        return ' '.join(['Mozilla/5.0', random.choice(cls.os_type), 'AppleWebKit/537.36', '(KHTML, like Gecko)',
                         cls.chrome_version, 'Safari/537.36'])