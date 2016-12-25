from scrapy import Spider
from scrapy.selector import Selector
import scrapy
from bs4 import BeautifulSoup
import requests
from urlparse import urlparse, urljoin

# Spider used to build database structure
# Finds all regions and regions for a continent, so that the
# Core spider can crawl those regions/subregions and get relevant data


class RegionSpider(Spider):
    name = "region_spider"
    allowed_urls = ["http://craigslist.org"]
    start_url = ["http://www.craigslist.org/about/sites"]

    def parse(self, response):
        # check in shell that this change works
        usa_territories = self._parse_territory_block(response.xpath(
            '/html/body/article/section//*[@class="colmask"][1]'))

        for name, regions in usa_territories.iteritems():
            for name, link in regions.iteritems():
                yield self._get_posts(name, link)

    def _get_posts(self, link):
        """
        Return the list of posts for the politics section for region at link.
        If region has sublinks, return a list of results for those instead.
        Because of the particulars of the layout of the (sub)region pages, this
        function should only ever be recursively called for regions, and never
        for subregions (subregions for a subregion are the other subregions of
        the parent region, so infinite recursion).
        """
        pol = link + "/search/pol"
        # bit at the top of the page that says the name of the region,
        # and contains links to subregions if they exists.
        region_banner = Selector(text=self._get_content(link).xpath(
            '// *[@id="topban"] / div[1]/'))
        subregions = region_banner.xpath('h2/text()')
        region_name = region_banner.xpath('ul')

        if subregions:
            def make_link(ps):
                # does path have trailing /?
                path = str(ps.xpath('li/a/@href').extract())
                return pol.replace("/search/", "/" + path + "/search/")
            links = map(make_link, subregions)
            posts = map(self._grab_posts, links)
        else:
            # there is a urljoin way to do this nicely, probably
            posts = self._grab_posts(link + "")

        return {'name': region_name, 'posts': posts}

    def _grab_posts(self, link):
        """
        Grab all the posts on a given page. Paginate if necessary.
        Returns a dict {region_name : list_of_posts}
        """
        # /html/head/title
        # i.e., new york politics
        # i.e., new york
        # needs to be tested in shell
        content = self._get_content(link)
        post_times = Selector(text=content).xpath(
            '//p/time/@datetime').extract()[0]
        post_titles = Selector(text=content).xpath(
            '//p/a/text()').extract()[0]

        posts = map(lambda (time, title): {"time": time, "title": title},
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
        Politely request the content at link
        """
        return requests.get(link)

    def _parse_territory_block(self, territory_block):
        """
        Parse a chunk of territories (i.e., parse a continent) on
        http://www.craigslist.org/about/sites, returning dict
        containing name/region-list pairs.

        For now, parses only USA
        """
        terr_names = territory_block.xpath('/div/h4')
        territories = territory_block.xpath('/div/ul')

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
