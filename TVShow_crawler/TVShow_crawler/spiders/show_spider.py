import re
import scrapy
from TVShow_crawler.items import TvshowCrawlerItem


class ShowSpider(scrapy.Spider):
    name = "shows"
    allowed_domains = ["seriesgraph.com"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._seen_show_links = set()

    async def start(self):
        for request in self.start_requests():
            yield request

    def start_requests(self):
        for page_num in range(1, 44):
            list_url = f"https://seriesgraph.com/all-shows/{page_num}"
            yield scrapy.Request(list_url, callback=self.parse_show_list)

    def parse_show_list(self, response):
        show_links = response.css('a[href*="/show/"]::attr(href)').getall()
        for href in show_links:
            if not href:
                continue
            url = response.urljoin(href)
            if url in self._seen_show_links:
                continue
            self._seen_show_links.add(url)
            yield scrapy.Request(url, callback=self.parse_show)

    def parse_show(self, response):
        item = TvshowCrawlerItem()
        item["link"] = response.url

        # --- Show name ---
        showname = response.css("h3::text").get()
        if showname:
            item["showname"] = showname.strip()

        # --- Rating ---
        # Adjust selector to match the actual rating element on the page
        rating_text = (
            response.css(".rating::text").get()
            or response.css('[class*="rating"]::text').get()
            or response.css('[class*="score"]::text').get()
        )
        if rating_text:
            match = re.search(r"[\d.]+", rating_text.strip())
            if match:
                item["rating"] = float(match.group())

        # --- Poster ---
        # Tries <img> inside a poster/cover wrapper, falls back to og:image meta tag
        poster_url = (
            response.css('[class*="poster"] img::attr(src)').get()
            or response.css('[class*="cover"] img::attr(src)').get()
            or response.css('meta[property="og:image"]::attr(content)').get()
        )
        if poster_url:
            item["poster"] = response.urljoin(poster_url)

        # --- Seasons & Episodes ---
        # Each season block is expected to have a heading and a list of episode rows
        seasons_data = []
        season_blocks = response.css('[class*="season"]')

        for season in season_blocks:
            # Collect episode names within this season block
            episode_names = [
                ep.strip()
                for ep in season.css(
                    '[class*="episode"] [class*="title"]::text, '
                    '[class*="episode"] [class*="name"]::text, '
                    'li [class*="name"]::text, '
                    'li::text'
                ).getall()
                if ep.strip()
            ]
            if episode_names:
                seasons_data.append(episode_names)

        if seasons_data:
            item["seasons"] = len(seasons_data)
            item["episodes"] = [len(eps) for eps in seasons_data]
            item["episode_names"] = seasons_data
        else:
            # Fallback: try to read a plain season count from the page
            season_count_text = (
                response.css('[class*="seasons"] span::text').get()
                or response.css('[class*="season-count"]::text').get()
            )
            if season_count_text:
                match = re.search(r"\d+", season_count_text)
                if match:
                    item["seasons"] = int(match.group())

        yield item
