class SectionSpider(Spider):
    name = "section_spider"

    def parse(self, response):
        sections = response.xpath('//*[@id="center"]')

        # Test these in shell
        # may be better to use child::*

        community = sections.xpath('//*[@id="ccc"]/div/ul/li/a')
        personals = sections.xpath('//*[@id="ppp0"]/li/a')
        housing = sections.xpath('//*[@id="hhh0"]/li/a')
        for_sale = sections.xpath('//*[@id="sss"]/div/ul/li/a')
        services = sections.xpath('//*[@id="bbb"]/div/ul/li/a')
        jobs = sections.xpath('//*[@id="jjj0/li/a"]')
        gigs = sections.xpath('//*[@id="ggg"]/div/ul/li/a')

        pass

    def _grab_personals(self, selector):
        """
        Handles the advisory pages in personals sections, which ask you if you
        are over 18 or whatever. Sometimes it asks you which subsection you'd
        like; woman seeking woman, man seeking woman, etc.
        """
        pass
