from scrapy import Spider
from scrapy.selector import Selector
import scrapy
from bs4 import BeautifulSoup
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
            for name, region_entry in regions.iteritems():
                region_link = region_entry['link']
                regions[name] = self._get_subregions()

            post_link = Selector(text=region).xpath('//p/a/@href').extract()[0]
            if post_link is not None:
                post_link = str(urlparse.urljoin(
                    response.url.replace("/search/pol", ""), post_link))

            yield {
                'post_time': post_time,
                'post_title': post_title,
                'post_link': post_link
            }

    def _get_subregions(self, region_selector):
        """
        Return the a dictionary of name/link pairs for a subregion. If
        Region has no subregions, return link.
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

            return dict(zip(region_names, region_links))

        return dict(zip(terr_names, map(grab_regions, territories)))
