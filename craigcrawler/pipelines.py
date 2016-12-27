# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pickle


class PicklePipeline(object):
    """
    Backup pipeline because I'm getting tired of messing with pymongo, and I
    want this running in at the same time while I sleep.
    """

    filename = "data/us.pkl"

    def __init__(self):
        self.usa = dict()

    @staticmethod
    def save(usa):
        try:
            with open(PicklePipeline.filename, 'wb') as f:
                pickle.dump(usa, f, pickle.HIGHEST_PROTOCOL)
        except:
            # whatever
            pass

        with open("usa_bak.pkl", 'wb') as f:
            pickle.dump(usa, f, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load():
        with open(PicklePipeline.filename, 'rb') as f:
            return pickle.load(f)

    def _add_to_hashtable(self, region_entry):
        state = region_entry["state"]
        region = region_entry["region"]

        self.usa[state] = self.usa.get(state, []) + [region]

    def _add_to_database(self, region_entry):
        pass

    def process_item(self, item, spider):
        self._add_to_hashtable(item)
        self._add_to_database(item)

        return item

    def open_spider(self, spider):
        """
        Dont support loading.
        """
        self.usa = dict()

    def close_spider(self, spider):
        PicklePipeline.save(self.usa)
