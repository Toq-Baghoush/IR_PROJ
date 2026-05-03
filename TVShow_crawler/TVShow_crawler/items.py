import scrapy


class TvshowCrawlerItem(scrapy.Item):
    showname = scrapy.Field()
    link = scrapy.Field()
    rating = scrapy.Field()
    poster = scrapy.Field()
    seasons = scrapy.Field()
    episodes = scrapy.Field()
    episode_names = scrapy.Field()

