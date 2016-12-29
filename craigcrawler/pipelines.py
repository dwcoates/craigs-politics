# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pickle
import pandas as pd
import numpy as np


class PickledPandaPipeline(object):
    """
    Backup pipeline because I'm getting tired of messing with pymongo, and I
    want this running in at the same time while I sleep.
    """

    pickle_filename = "data/us.pkl"
    csv_filename = "data/us.csv"

    def __init__(self):
        self.usa_dict = dict()

    @staticmethod
    def save(usa_dict):
        # save the dict as a pickle. This is a backup.
        try:
            with open(PickledPandaPipeline.pickle_filename, 'wb') as f:
                pickle.dump(usa_dict, f, pickle.HIGHEST_PROTOCOL)
        except:
            pass

        # build the dataframe to be stored in csv file
        usa_array = []
        for state in usa_dict:
            for region in usa_dict[state]:
                def build_post_item(title, time, subregion):
                    return [[title,
                             time,
                             state,
                             region["name"],
                             subregion]]

                posts = region["posts"]
                if posts:
                    for post in posts:
                        usa_array += build_post_item(post["entry"]["title"],
                                                     post["entry"]["time"],
                                                     post["subregion"])
                else:
                    usa_array += build_post_item(None, None, None)
        usa_scraped = pd.DataFrame(np.array(usa_array),
                                   columns=["title", "date", "state", "region", "subregion"])
        usa_db = pd.read_csv("data/us.csv", index_col=0)

        usa = pd.merge(usa_db, usa_scraped, how="outer")
        usa.to_csv(PickledPandaPipeline.csv_filename, encoding='utf-8')

    @staticmethod
    def load():
        with open(PickledPandaPipeline.pickle_filename, 'rb') as f:
            return pickle.load(f)

    def process_item(self, item, spider):
        """
        Build table in memory
        """
        state = item["state"]
        region = item["region"]

        self.usa_dict[state] = self.usa_dict.get(state, []) + [region]

        return item

    def open_spider(self, spider):
        """
        Dont support loading.
        """
        self.usa_dict = dict()
        self.usa_df = pd.DataFrame(
            columns=["title", "date", "state", "region", "subregion"])

    def close_spider(self, spider):
        """
        Save table as pickle and as csv
        """
        PickledPandaPipeline.save(self.usa_dict)
