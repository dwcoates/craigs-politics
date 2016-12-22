from scrapy import Spider
from scrapy.selector import Selector
import scrapy
from bs4 import BeautifulSoup
import urlparse


class RegionSpider(Spider):
    name = "region_spider"
    allowed_urls = ["http://craigslist.org"]
    start_url = ["http://www.craigslist.org/about/sites"]

    def start_requests(self):
        parse_urls = RegionSpider.cities()

        for url in parse_urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        usa_regions = self._parse_territory_block(response)
        for region in usa_regions:
            post_time = Selector(text=region).xpath(
                '//p/time/@datetime').extract()[0]
            post_title = Selector(text=region).xpath(
                '//p/a/text()').extract()[0]

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
        Parse a chunk of territories (i.e., a continent) on
        http://www.craigslist.org/about/sites

        For now, parses only USA
        """
        names = territory_block.xpath(
            '/html/body/article/section//*[@class="colmask"][1]/div/h4')
        region_blocks = territory_block.xpath(
            '/html/body/article/section//*[@class="colmask"][1]/div/ul')

        def grab_regions(region_block):
            """
            Return a dictionary consisting of name/link pairs from a chunk of
            regions corresponding to a territory (state, washington DC, other
            US territory).
            """
            links_selector = region_block.xpath('child::*/a')
            links = map(lambda link: "http:" + str(link),
                        (links_selector.xpath('@href').extract()))
            names = map(str, links_selector.xpath('text()'))

            return dict(zip(names, links))

        return dict(zip(names, map(grab_regions, region_blocks)))
