from scrapy import Spider
from scrapy.selector import Selector

import requests
import time
import random
from urlparse import urlparse, urljoin


class RegionSpider(Spider):
    name = "region_spider"
    allowed_urls = ["http://craigslist.org"]
    start_url = ["http://www.craigslist.org/about/sites"]

    def parse(self, response):
        # check in shell that this change works
        usa_territories = self._parse_continent(response)

        for terr_name, terr_regions in usa_territories.iteritems():
            for link in terr_regions.iteritems():
                yield {"state": terr_name,
                       "region": self._get_posts(link)}

    def _get_posts(self, link):
        """
        Return the list of posts for the politics section for region at link.
        If region has sublinks, return a list of results for those instead.
        """
        link = urljoin(link, "/search/pol")
        # bit at the top of the page that says the name of the region,
        # and contains links to subregions if they exists.
        region_banner = Selector(text=self._get_content(link).xpath(
            '// *[@id="topban"] / div[1]/'))
        region_name = region_banner.xpath('ul')

        def structure(n, p):
            return {'name': n, 'posts': p}

        subregions = region_banner.xpath('h2/text()')
        if subregions:
            def make_link(ps):
                # does path have trailing /?
                path = str(ps.xpath('li/a/@href').extract())
                return link.replace("/search/", "/" + path + "/search/")

            def get_name(ps):
                return str(ps.xpath('ls/a/@title'))

            names = map(get_name, subregions)
            links = map(make_link, subregions)
            postings = map(self._grab_posts, links)

            posts = map(structure, zip(names, postings))
        else:
            posts = self._grab_posts(link)

        return structure(region_name, posts)

    def _grab_posts(self, link):
        """
        Grab all the posts on a given page. Paginate if necessary.
        Returns a dict {region_name : list_of_posts}
        """
        # needs to be tested in shell
        content = self._get_content(link)
        post_times = Selector(text=content).xpath(
            '//p/time/@datetime').extract()[0]
        post_titles = Selector(text=content).xpath(
            '//p/a/text()').extract()[0]

        posts = map(lambda (tm, tt): {"time": tm, "title": tt},
                    zip(post_times, post_titles))

        next_page = Selector(text=content).xpath(
            '//*[@id="searchform"]/div[3]/div[3]/span[2]/a[3]/@href')
        if next_page:
            query = urlparse(str(next_page))[4]
            next_page_link = urljoin(link, "?" + query)
            posts += self._grab_posts(next_page_link)

        return posts

    @staticmethod
    def _get_content(link):
        """
        Politely request the page content at link
        """
        r = requests.get(link)

        x = 1 + 2 * random.random()
        time.sleep(x)

        return r

    def _parse_continent(self, site_page_response):
        """
        Parse a chunk of territories (i.e., parse a continent) on
        http://www.craigslist.org/about/sites, returning dict
        containing name/region-list pairs.

        For now, parses only USA
        """
        continent = site_page_response.xpath(
            '/html/body/article/section//*[@class="colmask"][1]')
        terr_names = continent.xpath('/div/h4')
        territories = continent.xpath('/div/ul')

        def grab_regions(territory):
            """
            Return a dictionary consisting of name/link pairs from chunks of
            regions corresponding to a territory (state, washington DC, other
            US territory).
            """
            regions_selector = territory.xpath('child::*/a')
            region_links = map(lambda link: "http:" + str(link),
                               regions_selector.xpath('@href').extract())
            region_names = map(str, regions_selector.xpath('text()'))

            return zip(region_names, region_links)

        return dict(zip(terr_names, map(grab_regions, territories)))
