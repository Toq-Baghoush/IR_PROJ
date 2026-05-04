BOT_NAME = "TVShow_crawler"
SPIDER_MODULES = ["TVShow_crawler.spiders"]
NEWSPIDER_MODULE = "TVShow_crawler.spiders"

ROBOTSTXT_OBEY = True

DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = 0.5

# FIXED: Removed the markdown hyperlink syntax here
USER_AGENT = "shows_scraper (+http://www.yourdomain.com)" 

ITEM_PIPELINES = {
    "TVShow_crawler.pipelines.TvshowCrawlerPipeline": 300,
}

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

LOG_LEVEL = "INFO"

# Selenium configuration
SELENIUM_DRIVER_NAME = "chrome"
SELENIUM_DRIVER_EXECUTABLE_PATH = "chromedriver"
SELENIUM_DRIVER_ARGUMENTS = ["--headless=new", "--disable-gpu", "--no-sandbox"]

FEED_EXPORT_ENCODING = "utf-8"