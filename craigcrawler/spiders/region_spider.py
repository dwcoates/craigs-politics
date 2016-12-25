from scrapy import Spider
from scrapy.selector import Selector

import requests
from urlparse import urlparse, urljoin
import time
import random


class RegionSpider(Spider):
    name = "region_spider"
    allowed_urls = ["http://craigslist.org"]
    start_url = ["http://craigslist.org/about/sites"]

    def __init__(self):
        self.regions_scraped = 0

    def parse(self, response):
        usa_territories = self._parse_continent(response)

        for terr_name, terr_regions in usa_territories.iteritems():
            for link in terr_regions.iteritems():
                yield {"state": terr_name,
                       "region": self._get_posts(link)}
                self.regions_scraped += 1
                print "region #%f scraped at '%s'" % (self.regions_scraped,
                                                      link)

    # replace regionspider with self
    def _get_posts(self, link):
        """
        Return the list of posts for the politics section for region at link.
        If region has subregions, return a list of results for those instead.
        """
        def structure((n, p)):
            return {'name': n, 'posts': p}

        region_banner = Selector(text=self._get_content(link)).xpath(
            '//*[@id="topban"]/div[1]')
        region_name = str(region_banner.xpath('h2/text()')[0].extract())

        pol = urljoin(link, "/search/pol")
        subregions = region_banner.xpath('ul/li')
        if subregions:
            def make_link(ps):
                # there's definitely a cleaner way to build this url
                path = str(ps.xpath('a/@href').extract()[0].replace("/", ""))
                return pol.replace("/search/", "/" + path + "/search/")

            def get_name(ps):
                return str(ps.xpath('a/@title').extract()[0])

            names = map(get_name, subregions)
            pol_links = map(make_link, subregions)
            postings = map(self._grab_posts, pol_links)

            posts = map(structure, zip(names, postings))
        else:
            posts = self._grab_posts(pol)

        return structure((region_name, posts))

    @staticmethod
    def _grab_posts(link):
        """
        Grab all the posts on a given page. Paginate if necessary.
        Returns a list of posts as time/title dictionaries.
        """
        print "link: '%s'" % link
        content = RegionSpider._get_content(link)
        post_times = str(Selector(text=content).xpath(
            '//p/time/@datetime')[0].extract())
        post_titles = str(Selector(text=content).xpath(
            '//p/a/text()')[0].extract())

        posts = map(lambda (tm, tt): {"time": tm, "title": tt},
                    zip(post_times, post_titles))

        next_page = Selector(text=content).xpath(
            '//*[@id="searchform"]/div[3]/div[3]/span[2]/a[3]/@href').extract()
        if next_page:
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

        x = 1 + 2 * random.random()
        time.sleep(x)

        return content

    @staticmethod
    def _parse_continent(site_page_response):
        """
        Parse a chunk of territories (i.e., parse a continent) on
        http://www.craigslist.org/about/sites, returning dict
        containing name/region-list pairs.

        For now, parses only USA.
        """
        continent = site_page_response.xpath(
            '/html/body/article/section//*[@class="colmask"][1]')
        terr_names = map(str, continent.xpath('div/h4/text()').extract())
        territories = continent.xpath('div/ul')

        def grab_regions(territory):
            """
            Return a dictionary consisting of name/link pairs from chunks of
            regions corresponding to a territory (state, washington DC, other
            US territory).
            """
            regions_selector = territory.xpath('child::*/a')
            region_links = map(lambda link: "http:" + str(link),
                               regions_selector.xpath('@href').extract())
            region_names = map(str, regions_selector.xpath('text()').extract())

            return zip(region_names, region_links)

        return dict(zip(terr_names, map(grab_regions, territories)))
