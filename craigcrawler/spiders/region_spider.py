from scrapy import Spider
from scrapy.selector import Selector
import scrapy
from bs4 import BeautifulSoup
import requests
import urlparse

# Spider used to build database structure
# Finds all regions and regions for a continent, so that the
# Core spider can crawl those regions/subregions and get relevant data


class RegionSpider(Spider):
    name = "region_spider"
    allowed_urls = ["http://craigslist.org"]
    start_url = ["http://www.craigslist.org/about/sites"]

    def start_requests(self):
        parse_urls = RegionSpider.cities()

        for url in parse_urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        # check in shell that this change works
        usa_territories = self._parse_territory_block(response.xpath(
            '/html/body/article/section//*[@class="colmask"][1]'))

        for name, regions in usa_territories.iteritems():
            for name, link in regions.iteritems():
                yield self._get_posts(name, link, is_region=True)

    def _get_posts(self, link, is_region=False):
        """
        Return the list of posts for the politics section for region at link.
        If region has sublinks, return a list of results for those instead.
        Because of the particulars of the layout of the (sub)region pages, this
        function should only ever be recursively called for regions, and never
        for subregions (subregions for a subregion are the other subregions of
        the parent region, so infinite recursion).
        """
        def linkify(ps):
            """
            Get the absolute link for a subregion reference on the page
            """
            return link + "/search/" + str(ps.xpath('li/a/@href').extract() + "/pol")

        # bit at the top of the page that says the name of the region,
        # and contains links to subregions if they exists.
        region_banner = Selector(text=requests.get(link).xpath(
            '// *[@id="topban"] / div[1]/'))
        subregions = region_banner.xpath('h2/text()')
        name = region_banner.xpath('ul')

        if subregions and is_region:
            links = map(linkify, subregions)
            return map(self._grab_posts, links)
        else:
            # there is a urljoin way to do this nicely, probably
            posts = self._grab_posts(link + "")

        return {name: posts}

    def _grab_posts(self, link):
        """
        Grab all the posts on a given page. Paginate if necessary.
        Returns a dict {region_name : list_of_posts}
        """
        pass

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
