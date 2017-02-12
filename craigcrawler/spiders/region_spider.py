from scrapy import Spider
from scrapy.selector import Selector

import requests
from urlparse import urlparse, urljoin
import time
import random

import logging

# in case of a failed region name, the request for that region must have
# failed. Consult log file link to region.
logger = logging.getLogger()
logging.basicConfig(filename='spider_log', level=logging.WARNING)


class RegionSpider(Spider):
    name = "region_spider"
    allowed_urls = ["http://craigslist.org"]
    start_urls = ["http://craigslist.org/about/sites"]

    def __init__(self):
        pass

    def parse(self, response):
        usa_territories = self._parse_continent(response)

        num_regions = sum(map(lambda t: len(t[1]), usa_territories))
        print("Regions to scrape: {0:,}".format(num_regions))
        time.sleep(3)

        regions_scraped = 0
        regions_missed = 0
        for terr_name, region_links in usa_territories:
            for link in region_links:
                region = {"name": None, "posts": []}
                scraped = False
                attempts = 0
                # make three attempts to make scrape region
                while(~scraped and attempts <= 3):
                    try:
                        region = RegionSpider._get_posts(link)
                        scraped = True
                    except requests.ConnectionError:
                        logger.warn(
                            "Connection failure while requesting '%s'", link)
                        print "Waiting in response to connection failure..."
                        time.sleep(20)
                    attempts += 1
                if scraped:
                    regions_scraped += 1
                else:
                    regions_missed += 1
                print ("region {0:,}/{1:,} {2} at " +
                       "'{3}'").format(regions_scraped,
                                       num_regions,
                                       "scraped" if scraped else "missed",
                                       link)

                yield {"state": terr_name, "region": region}

        print ("\n\n{0:,}/{1,:} regions successfully " +
               "extracted. See logs for " +
               "failures.\n\n").format(regions_scraped, num_regions)

    @staticmethod
    def _get_posts(link):
        """
        Return the list of posts for the politics section for region at link.
        If region has subregions, return a list of results for those instead.
        """
        def structure((ps, sr_name)):
            return map(lambda p: {'entry': p, 'subregion': sr_name}, ps)

        region_banner = Selector(text=RegionSpider._get_content(link)).xpath(
            '//*[@id="topban"]/div[1]')
        region_name = region_banner.xpath('h2/text()')[0].extract()

        pol = urljoin(link, "/search/pol")
        subregions = region_banner.xpath('ul/li')
        if subregions:
            def make_link(ps):
                # there's definitely a cleaner way to build this url
                path = ps.xpath('a/@href').extract()[0].replace("/", "")
                return pol.replace("/search/", "/search/" + path + "/")

            def get_name(ps):
                return ps.xpath('a/@title').extract()[0]

            subregion_names = map(get_name, subregions)
            pol_links = map(make_link, subregions)
            postings = map(RegionSpider._grab_posts, pol_links)

            # flatten subregion postings
            posts = sum(map(structure, zip(postings, subregion_names)), [])
        else:
            posts = structure((RegionSpider._grab_posts(pol), None))

        return {'name': region_name, 'posts': posts}

    @staticmethod
    def _grab_posts(link):
        """
        Grab all the posts on a given page. Paginate if necessary.
        Returns a list of posts as time/title dictionaries.
        """
        print "grabbing posts at link: " + link
        content = RegionSpider._get_content(link)

        no_results = Selector(text=content).xpath(
            '//*[@id="sortable-results"]/ul/*[@class="noresults"]')
        if no_results:
            return []

        post_times = Selector(text=content).xpath(
            '//p/time/@datetime').extract()
        post_titles = Selector(text=content).xpath(
            '//p/a/text()').extract()

        posts = map(lambda (tm, tt): {"time": tm, "title": tt},
                    zip(post_times, post_titles))

        # probably a nicer way to paginate here, but whatever
        range_to = Selector(text=content).xpath(
            '//*[@id="searchform"]/div[3]/div[3]/span[2]/span[3]/span[1]/span[2]/text()').extract()[0]
        total = Selector(text=content).xpath(
            '//*[@id="searchform"]/div[3]/div[3]/span[2]/span[3]//*[@class="totalcount"]/text()').extract()[0]
        if range_to != total:
            next_page = Selector(text=content).xpath(
                '//*[@id="searchform"]/div[3]/div[3]/span[2]/a[3]/@href') \
                .extract()
            query = urlparse(str(next_page[0]))[4]
            next_page_link = urljoin(link, "?" + query)
            posts += RegionSpider._grab_posts(next_page_link)

        return posts

    @staticmethod
    def _get_content(link):
        """
        Politely request the page content at link.
        """
        content = requests.get(link).text

        x = 3 + 2 * random.random()
        time.sleep(x)

        return content

    @staticmethod
    def _parse_continent(site_page_response):
        """
        Parse a chunk of territories (i.e., parse a continent) on
        http://www.craigslist.org/about/sites, returning list of
        name/region_link tuple pairs.

        For now, parses only USA.
        """
        continent = site_page_response.xpath(
            '/html/body/article/section//*[@class="colmask"][1]')
        terr_names = map(str, continent.xpath('div/h4/text()').extract())
        territories = continent.xpath('div/ul')

        def grab_regions(territory):
            """
            Return a list of unique links for the given territory selector
            (state, washington DC, other US territory). Will trim off the
            subregion extensions when they occur. Sometimes CL will add these
            in the sites page.
            """
            regions_selector = territory.xpath('child::*/a')
            region_links = map(lambda l: l[:l.rfind(".org") + 4],
                               regions_selector.xpath('@href').extract())

            return list(set(region_links))

        return zip(terr_names, map(grab_regions, territories))
