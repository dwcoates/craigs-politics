# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymongo
import pickle

from scrapy.conf import settings
from scrapy.exceptions import DropItem
from scrapy import log


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
        with open(PicklePipeline.filename, 'wb') as f:
            pickle.dump(usa, f, pickle.HIGHEST_PROTOCOL)

        with open("/home/dodge/usa_bak.pkl", 'wb') as f:
            pickle.dump(usa, f, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load():
        with open(PicklePipeline.filename, 'rb') as f:
            return pickle.load(f)

    def process_item(self, item, spider):
        state = item["state"]
        region = item["region"]

        self.usa[state] = self.usa.get(state, []) + [region]

        return item

    def open_spider(self, spider):
        """
        Dont support loading.
        """
        self.usa = dict()

    def close_spider(self, spider):
        PicklePipeline.save(self.usa)


class MongoDBPipeline(object):

    def __init__(self):
        settings["CLOSESPIDER_ERRORCOUNT"] = 1  # DEBUG. CHANGE THIS BEFORE RUN

        connection = pymongo.MongoClient(
            settings['MONGODB_SERVER'],
            settings['MONGODB_PORT']
        )

        db = connection[settings['MONGODB_DB']]
        self.collection = db[settings['MONGODB_COLLECTION']]

    def process_item(self, region_entry, spider):
        for data in region_entry:
            if not data:
                raise DropItem("Missing {0}!".format(data))

        state = region_entry["state"]
        region = region_entry["region"]

        cur = self.collection.find({"state": state})
        if cur.count() == 1:
            try:
                self.collection.update_one(
                    {"state": state}, {"$push": {"regions": region}})
            except:
                raise("failed to update regions")
        elif cur.count() < 1:
            try:
                self.collection.insert_one(
                    {"state": state, "regions": [region]})
            except:
                raise DropItem("failed to insert state")
        else:
            raise DropItem(
                "Mongodb collection has more than one entry for a state")

        log.msg("Region added for a state...",
                level=log.DEBUG, spider=spider)

        return region_entry
