
%matplotlib inline
import numpy as np
import scipy
from scipy import stats
import matplotlib as mpln
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd

from tabulate import tabulate

import pprint as pp
import pickle
import re

np.set_printoptions(suppress=True)

pd.options.display.max_colwidth = 1000


def print_df(df, headers="keys", rnd=100, dis_parse=False):
    """
    Pretty print DataFrame in an org table. Org tables are good.
    They also export nicely.
    """
    print(tabulate(df.round(rnd),
                   tablefmt="orgtbl",
                   headers=headers,
                   disable_numparse=dis_parse))

from os import path
from PIL import Image

from wordcloud import WordCloud, STOPWORDS

d = path.dirname(".")

plt.figure(num=None, figsize=(10, 8))

trump_mask = np.array(Image.open(path.join(d, "img/Trump_silhouette.png")))

wc = WordCloud(background_color="white", max_words=2000, mask=trump_mask)

wc.generate(posts_sum)

wc.to_file(path.join(d, "img/Trump_test.png"))

plt.imshow(wc)
plt.axis("off")
plt.figure()
plt.imshow(trump_mask, cmap=plt.cm.gray)
plt.axis("off")

plt.show()

usa_raw = pd.read_csv("data/us.csv", index_col=0)

post_count_total_raw = len(usa_raw)
post_count_by_state_raw = usa_raw.groupby(
    "state").count()["title"]  # .sort_values(ascending=False)
post_count_by_region_raw = usa_raw.groupby(
    "region").count()["title"]  # .sort_values(ascending=False)

print ("\n{0:,} total posts exctracted from {3:,} regions over {4} " +
       "state. The most popular\nstate was {1}, and the most " +
       "popular region was, surprisingly, {2}.").format(post_count_total_raw,
                                                        post_count_by_state_raw.index[
                                                            0],
                                                        post_count_by_region_raw.index[
                                                            0],
                                                        len(post_count_by_region_raw),
                                                        len(post_count_by_state_raw))

# Keys for geography stuff. Table is an index table.
# These keys are used as index for census table.
GEO_NAME = "GEO.display-label"
GEO_KEY = "GEO.id"

state_keys = pd.read_csv(
    "data/census/DEC_10_DP_G001_with_ann.csv")[1:].set_index(GEO_KEY)

state_keys = state_keys.filter([GEO_NAME])[:52]
state_keys = state_keys[state_keys[GEO_NAME] != "Puerto Rico"]

# keys for the census data. Only really care about two of them (there are
# hundreds):
TOT_NUM_ID = "HD01_S001"  # total number key
TOT_PER_ID = "HD02_S001"  # total percent key

census_all = pd.read_csv(
    "data/census/DEC_10_DP_DPDP1_with_ann.csv")[1:].set_index(GEO_KEY)

census_all = census_all.filter([TOT_NUM_ID])
census_all = census_all.join(state_keys, how="right")
census_all.columns = ["population", "state"]
census_all.set_index("state", inplace=True)


def correct_stat(s):
    """
    Some states have extra information for population. 
    Example: 25145561(r48514)
    """
    loc = s.find("(")
    return int(s[:loc] if loc > 0 else s)

census_all.population = census_all.population.apply(correct_stat)

census = census_all.drop("District of Columbia")

print_df(census.sample(4), rnd=3)

import requests
from scrapy import Selector

atlas_url = ("http://uselectionatlas.org/RESULTS/data.php?year" +
             "=2016&datatype=national&def=1&f=1&off=0&elect=0")
atlas_source = requests.get(atlas_url).text
select = Selector(text=atlas_source).xpath('//*[@id="datatable"]/tbody/tr')

convert = lambda s: int(s.replace(',', ''))
vote_names = map(str, select.xpath('td[3]/a/text()').extract())
# Correct name for DC
vote_names[8] = "District of Columbia"
clinton_votes = map(convert, select.xpath('td[17]/text()').extract())
trump_votes = map(convert, select.xpath('td[18]/text()').extract())

gen_votes = pd.DataFrame({"clinton": clinton_votes, "trump": trump_votes},
                         index=vote_names)

# Dub a states Rebublican vote rate "trumpism"
trump_favor = pd.DataFrame(gen_votes["trump"] / gen_votes.sum(axis=1),
                           columns=["trumpism"],
                           index=vote_names)
voting = gen_votes.join(trump_favor).sort_values("trumpism", ascending=False)
voting = voting.drop("District of Columbia")

# for pretty printing
voting_space = pd.DataFrame([["------", "------", "------"]], index=["*SPACE*"],
                            columns=voting.columns)
print_df(pd.concat([voting[:3].round(3), voting_space, voting[-3:].round(3).sort_values("trumpism")]),
         rnd=3)

print "Data tests... \n\nAssertions Passed\n\n"

# Confirm all expected regions and states present
# expected number of states (D.C., Territories)
assert len(usa_raw["state"].unique()) == 52
assert len(usa_raw["region"].unique()) == 416  # expected number of regions

# Confirm that there are no posts without regions/states. Not all CL
# regions have subregions, so it's okay for null subregions.
assert len(usa_raw[usa_raw["state"].isnull()].index) == 0
assert len(usa_raw[usa_raw["region"].isnull()].index) == 0

# Find regions/subregions for which there are no posts
postless_regions = usa_raw[usa_raw["title"].isnull()]
postless_regions_times = usa_raw[usa_raw["date"].isnull()]

# Not actually a good test, but good enough
assert len(postless_regions) == len(postless_regions_times)

print(("{0:,} regions/subregions over {1} states without " +
       "any posts.").format(len(postless_regions), postless_regions["state"].nunique()))

# Drop empty regions.
usa = usa_raw.dropna(subset=["title", "date"], how="any", axis=0)
assert len(postless_regions) == len(usa_raw) - len(usa)

# Get rid of territories (Guam, Puerto Rico).
usa = usa[usa["state"] != "Territories"]
# Get rid of "District of Columbia"
usa = usa[usa["state"] != "District of Columbia"]

assert set(usa.state.unique()) == set(census.index) and len(
    usa.state.unique() == len(census.index))

print "Census data complete"

assert set(usa.state.unique()) == set(voting.index) and len(
    usa.state.unique() == len(voting.index))

print "Voting data complete"

patronage = pd.DataFrame(usa.groupby('state').size(), columns=["patronage"]).sort_values(
    "patronage", ascending=False)

print("Top ten most frequented states:\n")
print_df(patronage[:10])

cl_by_state = patronage.join(census, how="inner")
usage = cl_by_state.apply(
    lambda df: df["patronage"] / float(df["population"]), axis=1)

# Weight for max = 1.000
usage_weighted = (usage - usage.min()) / (usage.max() - usage.min())
weighted_usage = pd.DataFrame((usage_weighted),
                              columns=["usage"])
state_usage = pd.concat([cl_by_state, weighted_usage],
                        axis=1).sort_values("usage",
                                            ascending=False)

# The range of fifty states (one to fifty, duh)
x = np.arange(len(state_usage))

ax = plt.subplot(111)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

plt.xlabel("States", fontsize=12)
plt.ylabel("Patronage", fontsize=12)

plt.suptitle('Patronage by state in order of population', fontsize=14)

plt.bar(x, state_usage.sort("population").patronage, color="#550000")

ax = plt.subplot(111)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

plt.xlabel("Usage", fontsize=12)
plt.ylabel("States", fontsize=12)

plt.suptitle('Politics Usage Distribution', fontsize=14)

plt.hist(state_usage.usage,
         color="#661111", bins=17)

norm_usage = (state_usage - state_usage.min()) / \
    (state_usage.max() - state_usage.min())
norm_usage.plot(
    kind="density", title="Normalized PDF estimations", sharey=True)

colors = cm.YlOrRd(state_usage.usage)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

plt.ylabel("Patronage", fontsize=12)
plt.xlabel("Population", fontsize=12)

plt.suptitle('Patronage vs Population, heatmapped by Usage', fontsize=12)


plt.scatter(state_usage.population, state_usage.patronage, color=colors)

print_df(states.filter(["patronage", "usage", "normalized", "trumpism"]).corr(),
         rnd=3,
         dis_parse=True)

pop_english_words = ["the", "re", "a", "s", "t", "i", "of", "to", "and", "and", "in", "is", "it", "you", "that", "he", "was", "for", "on", "are", "with", "as", "I", "his", "they", "be", "at", "one", "have", "this", "from", "or", "had", "by", "hot", "but", "some", "what", "there", "we", "can", "out", "other", "were", "all", "your", "shit", "when", "up", "use", "word", "how", "said", "an", "each", "she",
                     "which", "do", "their", "time", "if", "will", "way", "about", "many", "fuck", "then", "them", "would", "write", "like", "so", "these", "her", "long", "make", "thing", "see", "him", "two", "has", "look", "more", "day", "could", "go", "come", "did", "my", "sound", "no", "most", "number", "who", "over", "know", "water", "than", "call", "first", "people", "may", "down", "side", "been", "now", "find"]

from collections import Counter


def post_words(df, no_pop=False):
    wds = re.findall(r'\w+', df.title.apply(lambda x: x + " ").sum())
    if no_pop:
        # pop_english_words is a list of the most popular (and boring) English
        # words. E.g., "and", "to", "the", etc.
        wds = [word for word in wds if word.lower() not in pop_english_words]
    return wds


def words(df=usa, no_pop=False):
    # word counts across all posts
    wds = post_words(df, no_pop)
    word_counts = Counter([word.lower() for word in wds])
    wd_counts = zip(*[[word, count]
                      for word, count in word_counts.iteritems()])
    corpus = pd.Series(wd_counts[1], index=wd_counts[0]).rename("counts")

    return corpus.sort_values(ascending=False)

# words function grabs all the words from df, with option to exclude
# popular words
posts_corpus = words(df=usa, no_pop=True)

usa_words_full = post_words(df=usa)
usa_words = post_words(df=usa, no_pop=True)

# good estimate of sum of all posts, minus popular words
posts_sum = " ".join(usa_words)


def find_strs(substr, df=usa):
    """
    Get all titles from usa that have substr in their post title. Add some data on capitalization.
    """

    find = lambda s: (1 if re.search(substr, s, re.IGNORECASE) else np.nan)

    return df.title[df.title.map(find) == 1].rename("*" + substr + "*", inplace=True)


def categ_strs(findings):
    """
    Return a list of 
    """
    s = findings.name[1:-1]
    find = lambda sub, string: (1 if re.search(sub, string) else np.nan)

    proper = findings.apply(lambda x: find(
        s[0].upper() + s[1:].lower(), x)).rename("proper")
    cap = findings.apply(lambda x: find(s.upper(), x)).rename("uppercase")
    low = findings.apply(lambda x: find(s.lower(), x)).rename("lower")

    return pd.concat([proper, cap, low], axis=1)


def eval_strs(string, df=usa):
    findings = find_strs(string, df)
    return categ_strs(findings).join(findings)

trumps = eval_strs("trump").join(usa.state, how="inner")
trumps_by_state = trumps.groupby("state").count().join(
    states).drop(["clinton", "trump"], axis=1)
up_over_trumps = (trumps_by_state.uppercase /
                  trumps_by_state["*trump*"]).rename("uppercase usage")
prop_over_trumps = (trumps_by_state.proper /
                    trumps_by_state["*trump*"]).rename("propercase usage")
trumps_over_pat = (trumps_by_state["*trump*"] /
                   trumps_by_state.patronage).rename("trumps usage")
trumps_by_state = trumps_by_state.join(
    [prop_over_trumps, up_over_trumps, trumps_over_pat], how="outer")

trumps_vs_trumpism = trumps_by_state.filter(["trumpism",
                                             "propercase usage",
                                             "uppercase usage",
                                             "trumps usage"]).sort_values(
                                                 "trumps usage", ascending=True)[1:]

pd.DataFrame.hist(trumps_vs_trumpism, bins=50)
#plt.hist([prop_over_cap.trumpism, prop_over_cap[""]], bins=30)

pennsylvania = nonascii_posts[nonascii_posts["state"] == "Pennsylvania"]
pennsylvania.groupby("region").count()
penn_lenn = float(len(pennsylvania.title))

post_uniqueness = (penn_lenn - pennsylvania.title.nunique()) / penn_lenn * 100

print("{:.2f}% of non-ascii posts are completely unique.".format(post_uniqueness))
