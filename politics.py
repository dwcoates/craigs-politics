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

usa_raw = pd.read_csv("data/us.csv", index_col=0)

post_count_total_raw = len(usa_raw)
post_count_by_state_raw = usa_raw.groupby("state").count()["title"].sort_values(ascending=False)
post_count_by_region_raw = usa_raw.groupby("region").count()["title"].sort_values(ascending=False)

print ("{0:,} total posts exctracted from {1:} regions over {2} "+
       "states. The most \nfrequented state was '{3}', and the most " +
       "frequented region was,\nsurprisingly, '{4}'.").format(post_count_total_raw,                                                          
                                                             len(post_count_by_region_raw),
                                                             len(post_count_by_state_raw),
                                                             post_count_by_state_raw.index[0],
                                                             post_count_by_region_raw.index[0],)

# This can fail because tabulate can't handle unicode.
# There's only about a 2.5% chance if fails on a given execution, though.
print_df(usa_raw.sample(3), rnd=3)

# Keys for geography stuff. Table is an index table.
# These keys are used as index for census table.
GEO_NAME = "GEO.display-label"
GEO_KEY = "GEO.id"

state_keys = pd.read_csv("data/census/DEC_10_DP_G001_with_ann.csv")[1:].set_index(GEO_KEY)

state_keys = state_keys.filter([GEO_NAME])[:52]
state_keys = state_keys[state_keys[GEO_NAME]!= "Puerto Rico"]

# keys for the census data. Only really care about two of them (there are hundreds):
TOT_NUM_ID = "HD01_S001" # total number key
TOT_PER_ID = "HD02_S001" # total percent key

cd_file = "data/census/DEC_10_DP_DPDP1_with_ann.csv"
census_all = pd.read_csv(cd_file)[1:].set_index(GEO_KEY)

census_states = census_all.filter([TOT_NUM_ID]).join(state_keys, how="right")
census_states.columns = ["population", "state"]
census_states.set_index("state", inplace=True)

def correct_stat(s):
    """
    Some states have extra information for population.
    Example: 25145561(r48514), should be 25145561.
    """
    loc = s.find("(")
    return int(s[:loc] if loc > 0 else s)

census_states.population = census_states.population.apply(correct_stat)

census = census_states.drop("District of Columbia")

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
trump_favor = pd.DataFrame(gen_votes["trump"]/gen_votes.sum(axis=1),
                           columns=["trumpism"],
                           index=vote_names)
voting = gen_votes.join(trump_favor).sort_values("trumpism", ascending=False)
voting = voting.drop("District of Columbia")

# for pretty printing
voting_space = pd.DataFrame([["------", "------", "------"]],index=["*SPACE*"],
                            columns=voting.columns)
print_df(pd.concat([voting[:3].round(3), voting_space, voting[-3:].round(3).sort_values("trumpism")]),
         rnd=3)

print "Data tests... \n\nAssertions Passed\n\n"

# Confirm all expected regions and states present
assert len(usa_raw["state"].unique()) == 52 # expected number of states (D.C., Territories)
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

# Drop empty regions. Some regions are too small to have any posts.
usa = usa_raw.dropna(subset=["title", "date"], how="any", axis=0)
assert len(postless_regions) == len(usa_raw)-len(usa)

# Get rid of territories (Guam, Puerto Rico).
usa = usa[usa["state"] != "Territories"]
# Get rid of "District of Columbia"
usa = usa[usa["state"] != "District of Columbia"]

# Confirm census data
assert set(usa.state.unique()) == set(census.index) and len(usa.state.unique() == len(census.index))

print "Census data complete"

# Confirm election data
assert set(usa.state.unique()) == set(voting.index) and len(usa.state.unique() == len(voting.index))

print "Voting data complete"

patronage = pd.DataFrame(usa.groupby('state').size(), columns=["patronage"]).sort_values(
    "patronage",ascending=False)

print("Top ten most frequented states:\n")
print_df(patronage[:10])

cl_by_state = patronage.join(census, how="inner")
usage = cl_by_state.apply(
    lambda df: df["patronage"] / float(df["population"]), axis=1)

# Weight for max = 1.000
usage_weighted = (usage - usage.min())/(usage.max() - usage.min())
weighted_usage = pd.DataFrame((usage_weighted),
                               columns=["usage"])
state_usage = pd.concat([cl_by_state, weighted_usage],
                        axis=1).sort_values("usage",
                                            ascending=False)

# Just some printing

# Useful for displaying several splices of a dataframe as a concatenation
state_usage_space = pd.DataFrame([["------", "------", "------"]],index=["*SPACE*"],
                                 columns=state_usage.columns)

print_df(state_usage.sample(3))

states = state_usage.join(voting, how="left").sort_values("usage")

print(tabulate(states.sample(3), tablefmt="orgtbl", headers="keys"))

top_five = state_usage.sort_values("patronage")[-5:][::-1]
fig = plt.figure() # Create matplotlib figure

ax = fig.add_subplot(111) # Create matplotlib axes
ax2 = ax.twinx() # Create another axes that shares the same x-axis as ax.

width = 0.2

top_five.patronage.plot(kind='bar', color='#992255', ax=ax, width=width, position=1)
top_five.population.plot(kind='bar', color='#CC7733', ax=ax2, width=width, position=0)

ax.set_ylabel('Patronage')
ax2.set_ylabel('Population')

plt.show()

print("Patronage of Denver, Colorado: {}".format(len(usa[usa.region == "denver, CO"])))

# From census bureau, to the nearest 1000 people
pop_denver_proper = 649000.0 
pop_denver_metro = 2814000.0
pop_nyc_proper = 8550000.0  
pop_nyc_metro = 20200000.0

# Enumerate the NYC subregions. More than you might think.
nyc_subregions = usa.groupby("region").get_group(
    "new york city").subregion.unique().tolist()
num_nyc_posts = len(usa[usa.region == "new york city"])
num_denver_posts = len(usa[usa.region == "denver, CO"])

den_nyc_rat_prop =  (num_denver_posts/pop_denver_proper) /     \
                    (num_nyc_posts/pop_nyc_proper)

den_nyc_rat_metro =  (num_denver_posts/pop_denver_metro)/     \
                     (num_nyc_posts/pop_nyc_metro)

print(("{0} posts in NYC spread over:\n{1}" + 
      ",\nand {2}.").format(num_nyc_posts, 
                            ',\n'.join('{}'.format(r) for r in nyc_subregions[:-1]), 
                            nyc_subregions[-1]))
print(("\nConsidering city propers, we can say that Denver has ~{0:.1f}x the usage rate\nof " +
         "New York City. Adjusting for census estimates for metropolitan areas, it\nwould " + 
         "seem that Denver's usage is ~{1:.1f}x that of NYC's.").format(den_nyc_rat_prop, 
                                                                        den_nyc_rat_metro))

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

print_df(pd.concat([state_usage[:5].round(3),
                     state_usage_space,
                     state_usage[-5:].sort_values("usage").round(3)]))

ax = plt.subplot(111)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

plt.xlabel("Usage", fontsize=12)
plt.ylabel("States", fontsize=12)

plt.suptitle('Usage Distribution for CL politics board', fontsize=14)

plt.hist(state_usage.usage,
         color="#661111", bins=17)

# Plot normalized state usage measures
state_usage_min_zero = state_usage - state_usage.min()
state_usage_range = state_usage.max() - state_usage.min()
norm_usage = state_usage_min_zero / state_usage_range

norm_usage.plot(kind="density", 
                title="Normalized PDF estimations",
                sharey=True)

stats = pd.DataFrame({"mean": norm_usage.mean(),
                      "median": norm_usage.median()})
print("Mean/median of normalized state usage metrics:")

print_df(stats)

colors = cm.YlOrRd(state_usage.usage)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

plt.ylabel("Patronage", fontsize=12)
plt.xlabel("Population", fontsize=12)

plt.suptitle('Patronage vs Population, heatmapped by Usage', fontsize=12)


plt.scatter(state_usage.population, state_usage.patronage, color=colors)

post_politics = usa.join(states.trumpism, how="outer", on="state")
post_politics.trumpism.plot(kind="hist", bins=20, color=["#FF9911"], 
                            title="Distribution of posts by politics")

avg_post_trumpism = post_politics.trumpism.mean()
trump_votes = voting.trump.sum()
clinton_votes = voting.clinton.sum()
national_trumpism = trump_votes/float((trump_votes + clinton_votes))

# Some printing
print(("Mean trumpism: {:.2f} Trump voters seem to show " + 
       "{:+.2f}% representation\non CL politics vs General " + 
       "Election results.").format(
           (avg_post_trumpism*100), 
           (avg_post_trumpism/national_trumpism)*100-100))

post_trumpism_tot = post_politics.trumpism.plot(
    kind="density", 
    title="PDF estimation of Trumpism w/ mean",
    sharey=True)
plt.axvline(post_politics.trumpism.mean(), color='r', linestyle='dashed', linewidth=.5)

corr = states.filter(["patronage", "usage", "trumpism", "population"]).corr()
fig, ax = plt.subplots(figsize=(4, 4))
ax.matshow(corr, cmap=plt.cm.seismic)
plt.xticks(range(len(corr.columns)), corr.columns);
plt.yticks(range(len(corr.columns)), corr.columns);

print_df(corr, rnd=3)

pop_english_words = ["the", "re", "a", "s",
                     "t", "i", "of", "to",
                     "and", "and", "in", "is",
                     "it", "you", "that", "he",
                     "was", "for", "on", "are",
                     "with", "as", "I", "his",
                     "they", "be", "at", "one",
                     "have", "this", "from", "or",
                     "had", "by", "hot", "but",
                     "some", "what", "there", "we",
                     "can", "out", "other", "were",
                     "all", "your", "shit", "when",
                     "up", "use", "word", "how",
                     "said", "an", "each", "she",
                     "which", "do", "their", "time",
                     "if", "will", "way", "about", "thought"
                     "many", "fuck", "then", "them",
                     "would", "write", "like", "so",
                     "these", "her", "long", "make",
                     "thing", "see", "him", "two",
                     "has", "look", "more", "day",
                     "could", "go", "come", "did",
                     "my", "sound", "no", "most",
                     "number", "who", "over", "know",
                     "water", "than", "call", "first",
                     "people", "may", "down", "side",
                     "been", "now", "find"]

from collections import Counter

def post_words(df, no_pop=False):
    wds = re.findall(r'\w+', df.title.apply(lambda x: x + " ").sum())
    if no_pop:
        # pop_english_words is a list of the most popular (and boring) English
        # words. E.g., "and", "to", "the", etc.
        wds = [word for word in wds if word.lower() not in pop_english_words]
    return  wds

def words(df=usa, no_pop=False):
    # word counts across all posts
    wds = post_words(df, no_pop)
    word_counts = Counter([word.lower() for word in wds])
    wd_counts = zip(*[[word, count] for word, count in word_counts.iteritems()])
    corpus = pd.Series(wd_counts[1], index=wd_counts[0]).rename("counts")

    return corpus.sort_values(ascending=False)

# Probably don't care about stupid common words.
# `words' function grabs all the words from df, with option to exclude popular words
posts_corpus = words(df=usa, no_pop=True)

usa_words_full = post_words(df=usa)
usa_words = post_words(df=usa, no_pop=True)

posts_sum = " ".join(usa_words) # good estimate of sum of all posts, minus popular words

#
# Find substrings in posts
#

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

    proper = findings.apply(lambda x: find(s[0].upper() + s[1:].lower(), x)).rename("proper")
    cap = findings.apply(lambda x: find(s.upper(), x)).rename("uppercase")
    low = findings.apply(lambda x: find(s.lower(), x)).rename("lower")

    return pd.concat([proper, cap, low], axis=1)

def eval_strs(string, df=usa):
    findings = find_strs(string, df)
    return categ_strs(findings).join(findings)

def check_ascii(post):
    """
    Determines whether a title is encodable as ascii
    """
    try:
        post.encode('ascii')
        return True
    except UnicodeError:
        return False
ascii_posts = usa[usa.title.apply(check_ascii)]
nonascii_posts = usa[~usa.title.apply(check_ascii)]
distinct_states = nonascii_posts["state"].unique()

print ("{0:,} of {1:,} total posts were non-ascii ({2:.2f}%), confined to {3} "
       + "states.").format(len(nonascii_posts),
                       len(usa),
                       len(nonascii_posts)/float(len(usa)) * 100,
                       len(distinct_states))

pennsylvania = nonascii_posts[nonascii_posts["state"] == "Pennsylvania"]
pennsylvania.groupby("region").count()
penn_lenn = float(len(pennsylvania.title))
post_uniqueness = (penn_lenn-pennsylvania.title.nunique())/penn_lenn * 100

import itertools
from difflib import SequenceMatcher
def avg_similarity(posts):
  def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()
  sim_sum = 0
  title_product = itertools.product(posts.title, posts.title)
  for title_pair in title_product:
    sim_sum += similarity(*title_pair)
  avg_sim = sim_sum/(len(posts)**2)
  return avg_sim

print(("The average similarity of all non-ascii posts is " +
       "{:.2f}, while that \nof only those in Pennsylvania is " +
       "{:.2f}. The average for all posts in\nall regions is " +
       "{:.2f}.")).format(avg_similarity(nonascii_posts),
                          avg_similarity(pennsylvania),
                          avg_similarity(usa.sample(200)))

# Grab some words
lib_words = words(df=post_politics[post_politics.trumpism < .45],
                  no_pop=True).rename("libs")
conserv_words = words(df=post_politics[post_politics.trumpism > .55],
                      no_pop=True).rename("conservs")

# THIS IS BROKEN AND BAD. Placeholder code
rat = lambda df: df.libs/df.conservs
ratio = pd.DataFrame().join([lib_words[lib_words >= 10],
                             conserv_words[conserv_words >= 10]],
                            how="outer").apply(rat, axis=1).dropna()
ratio = ratio.rename("dem/rep ratio")

lib_con_ratio = pd.DataFrame(posts_corpus).join(ratio.sort_values(ascending=False),
                                                how="inner")

lib_con_ratio[:10]

print_df(pd.DataFrame(pd.concat([find_strs("tax"),
                                 find_strs("speech"),
                                 find_strs("russian")]).rename(
                                     "title")).sample(5), 
         rnd=3)

p = posts_corpus[:25].sort_values(ascending=True)

ax = p.plot(kind="bar", color="#662200", grid=True)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

plt.ylabel("Occurences", fontsize=12)

plt.suptitle('Word usages', fontsize=14)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

# Splitting a series into chunks such that values.sum() = val (or as close
# as possible, greedily) so we can wee how the diversity of words is
# distributed:
def splicer(ss, val):
  indices = ss.index.tolist()
  if len(indices) <= 1:
    return pd.Series(ss[index[0]], index=[[indices[0]]])
  left = [ss.index[0]]
  right = ss.index[1:].tolist()
  s = ss[left[0]]
  while s < val and len(right) > 0:
    i = right.pop(0)
    left.append(i)
    s += ss[i]
  return [ss.filter(left)] + (splicer(ss.filter(right), val) if len(right) > 0 else [])

chunks = splicer(posts_corpus, posts_corpus.iloc[0])
ax = plt.subplot()

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

plt.ylabel("", fontsize=12)
plt.suptitle('', fontsize=14)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

plt.bar(np.arange(0, len(chunks)), np.array([len(c) for c in chunks]))

trumps = eval_strs("trump").join(usa.state, how="inner")
trumps_by_state = trumps.groupby("state").count().join(states).drop(["clinton", "trump"], axis=1)
up_over_trumps = (trumps_by_state.uppercase/trumps_by_state["*trump*"]).rename("uppercase usage")
prop_over_trumps = (trumps_by_state.proper/trumps_by_state["*trump*"]).rename("propercase usage")
trumps_over_pat = (trumps_by_state["*trump*"]/trumps_by_state.patronage).rename("trumps usage")
trumps_by_state = trumps_by_state.join([prop_over_trumps, up_over_trumps, trumps_over_pat], how="outer")

trumps_vs_trumpism = trumps_by_state.sort_values(
    "trumpism", ascending=True).filter(["propercase usage",
                        "uppercase usage"])

trumps_vs_trumpism.plot(kind="bar", stacked=True, figsize=(10, 5))

ax = plt.subplot()

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

plt.xlabel("States, in order of trumpism")

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

post_politics.trumpism.plot(kind="density", linewidth=0.8)

ax = plt.subplot()

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

plt.ylabel("Occurences", fontsize=12)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

trumps_trumpism = trumps.join(post_politics.trumpism)

trumps_trumpism.trumpism.plot(kind="density", 
                              title="PDF of trumpism for "  +  
                              "posts containing 'Trump'",
                              linewidth=2)
plt.axvline(trumps_trumpism.trumpism.mean(), color='r',
            linestyle='dashed', linewidth=.5)

cap_trumps = trumps_trumpism[trumps_trumpism.uppercase > 0]

ax = plt.subplot()

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()

cap_trumps.trumpism.plot(kind="density", 
                         title="PDF of trumpism for posts " \
                         "containing 'TRUMP'",
                         color='blue', linewidth=1.5)
plt.axvline(cap_trumps.trumpism.mean(), color='r',
            linestyle='dashed', linewidth=.5)

liberal_sample = trumps_trumpism[trumps_trumpism.trumpism < .45].sample(5)

print("Selecting states that are espectially " \
      "anti-trump:\n")
print_df(pd.DataFrame(liberal_sample["*trump*"]))

print("Politically liberal states composing " +
      "the above sampling:\n{}.".format(
           ", ".join("{}".format(r) for r in liberal_sample.state.unique())))

liberal = float(posts_corpus["liberal"])
liberal_p = float(posts_corpus["liberals"])
conserv = float(posts_corpus["conservative"])
conserv_p = float(posts_corpus["conservatives"])

print ("liberal/conservative: {0:.2f}\n" +
       "liberals/conservatives: {1:.2f}\n" +
       "liberal(s)/conservative(s): {2:.2f}" +
       "") .format(liberal/conserv,
                   liberal_p/conserv_p,
                   (liberal+liberal_p)/(conserv+conserv_p))

print("*singular/plural*\n" +
      "'conservative': {0:.3f}\n" +
      "'liberal': " +
      "{1:.3f}").format(posts_corpus["conservative"]/float(posts_corpus["conservatives"]),
                        posts_corpus["liberal"]/float(posts_corpus["liberals"]))

libs = eval_strs("liberal").sum(numeric_only=True)
conservs = eval_strs("conservative").sum(numeric_only=True)

lib_con_rates = (libs/libs.sum()) / (conservs/conservs.sum())
lib_con_rates.rename("'liberal'/'conservative' usage", inplace=True)

lib_con_cap_rat = pd.DataFrame([(libs/conserv).rename(
    "# 'liberal' per 'conservative'"), lib_con_rates])

print_df(pd.DataFrame(lib_con_cap_rat))

from textblob import TextBlob

def semants(text):
    blob = TextBlob(text)
    ss = 0
    for sentence in blob.sentences:
        ss += sentence.sentiment.polarity
    return float(ss)/len(blob.sentences)

# package does not like non-ascii encodings
trumps_ascii = trumps[trumps["*trump*"].apply(check_ascii)]


usa_sentiment = post_politics.join(ascii_posts.title.apply(
    semants).rename("sentiment"))
trumps_sentiment = usa_sentiment.filter(trumps_ascii.index, axis=0)

zero_sents = len(usa_sentiment[usa_sentiment.sentiment == 0])
print(('Number of posts with 0 sentiment: {0:,} ' + 
       '({1:.2f}%).').format(zero_sents, 
                             float(zero_sents)/len(usa_sentiment)*100))

from os import path
from PIL import Image

from wordcloud import WordCloud

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
