#-*-coding:utf-8-*- 
# author lyl
import bloom_filter

class MyBloomFilter:

    def __init__(self,
                 max_elements=10000,
                 error_rate=0.1,
                 filename=None,
                 start_fresh=False):
        self.bloom = bloom_filter.BloomFilter(max_elements=max_elements,
                                              error_rate=error_rate,
                                              filename=filename,
                                              start_fresh=start_fresh)
    def add(self, key):
        self.bloom.add(key)

    def __contains__(self, item):
        return item in self.bloom



