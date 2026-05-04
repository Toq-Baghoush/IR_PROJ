import re
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import scrapy
from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from TVShow_crawler.items import TvshowCrawlerItem


class ShowSpider(scrapy.Spider):
    name = "shows"
    allowed_domains = ["seriesgraph.com"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._seen_show_links = set()
        self.driver = None
        self.imdb_episodes_collected = {}
        self.total_pages = 43

    def init_selenium(self):
        if self.driver:
            return

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        driver_path = self.settings.get('SELENIUM_DRIVER_EXECUTABLE_PATH')
        service = None

        if driver_path:
            driver_path = Path(driver_path)
            if not driver_path.is_absolute():
                driver_path = Path(__file__).resolve().parents[2] / driver_path
            driver_path = str(driver_path)
            if Path(driver_path).exists():
                service = Service(driver_path)
            else:
                self.logger.warning(
                    f"Configured ChromeDriver path not found: {driver_path}. Falling back to webdriver-manager."
                )

        if service is None:
            driver_path = ChromeDriverManager().install()
            service = Service(driver_path)

        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(5)

    def make_selenium_response(self, url):
        try:
            self.init_selenium()
            self.driver.get(url)
            time.sleep(2)
            body = self.driver.page_source
            return HtmlResponse(url=url, body=body, encoding='utf-8', request=scrapy.Request(url))
        except Exception as exc:
            self.logger.warning(f"Failed to load page with Selenium: {exc}")
            return None

    def closed(self, reason):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    async def start(self):
        for request in self.start_requests():
            yield request

    def start_requests(self):
        for page_num in range(1, self.total_pages + 1):
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
        rendered_response = self.make_selenium_response(response.url)
        if rendered_response:
            response = rendered_response

        item = TvshowCrawlerItem()
        item["link"] = response.url
        show_id = response.url.split("/show/")[1].split("-")[0]

        showname = response.css("h1::text, h3::text").get()
        if showname:
            item["showname"] = showname.strip()

        rating_text = response.css("strong::text, .ShowRating__value::text, .rating-value::text").get()
        if rating_text:
            match = re.search(r"([\d.]+)", rating_text.strip())
            if match:
                item["rating"] = float(match.group(1))

        poster_url = None
        if showname:
            poster_url = response.xpath('//img[@alt=$name]/@src', name=showname.strip()).get()
        poster_url = poster_url or response.css('meta[property="og:image"]::attr(content)').get()
        if poster_url:
            if "_next/image" in poster_url:
                parsed = urlparse(poster_url)
                query_url = parse_qs(parsed.query).get("url")
                if query_url:
                    poster_url = unquote(query_url[0])
            item["poster"] = response.urljoin(poster_url)

        season_texts = response.css('div.rt-ScrollAreaRoot svg g.tick text::text, div.rt-ScrollAreaRoot svg text::text').re(r'^S(\d+)$')
        episode_texts = response.css('div.rt-ScrollAreaRoot svg g.tick text::text, div.rt-ScrollAreaRoot svg text::text').re(r'^E(\d+)$')

        if season_texts:
            season_numbers = [int(s) for s in season_texts]
            item["seasons"] = max(season_numbers)

        if episode_texts:
            item["episodes"] = len(episode_texts)

        if not item.get("seasons"):
            page_text = ' '.join(response.xpath('//text()[normalize-space()]').getall())
            page_seasons = re.findall(r'S(\d+)E(\d+)', page_text, re.IGNORECASE)
            if page_seasons:
                item["seasons"] = max(int(s) for s, _ in page_seasons)
            if not item.get("episodes"):
                item["episodes"] = len(set(page_seasons))

        episode_names = response.css(
            '[class*="Episode"] [class*="title"]::text, [class*="episode"] [class*="title"]::text, [class*="episode-name"]::text'
        ).getall()
        episode_names = [name.strip() for name in episode_names if name and len(name.strip()) > 1]
        if episode_names:
            item["episode_names"] = episode_names

        imdb_episode_urls = []
        all_hrefs = response.css('a::attr(href)').getall()
        for href in all_hrefs:
            if not href:
                continue
            if 'imdb.com' in href and '/title/' in href:
                imdb_episode_urls.append(response.urljoin(href))
            elif href.startswith('/title/'):
                imdb_episode_urls.append(response.urljoin(href))

        data_hrefs = response.css('[data-href*="imdb"]::attr(data-href)').getall()
        for href in data_hrefs:
            if href and 'imdb.com' in href:
                imdb_episode_urls.append(href)

        onclick_attrs = response.xpath('//@onclick').getall()
        for onclick in onclick_attrs:
            if 'imdb.com' in onclick:
                match = re.search(r'(https?://[^\s\'\"]*imdb[^\s\'\"]*)', onclick)
                if match:
                    url = match.group(1).replace('&quot;', '').replace('&amp;', '&')
                    imdb_episode_urls.append(url)

        imdb_episode_urls = list(dict.fromkeys(response.urljoin(url) for url in imdb_episode_urls))
        imdb_episode_urls = [url for url in imdb_episode_urls if '/title/' in url][:15]

        self.logger.info(
            f"Show: {showname or response.url}, seasons={item.get('seasons')}, episodes={item.get('episodes')}, found {len(imdb_episode_urls)} IMDB links"
        )

        if imdb_episode_urls:
            self.imdb_episodes_collected[show_id] = {
                'item': item,
                'episodes': [],
                'total_urls': len(imdb_episode_urls)
            }
            for idx, imdb_url in enumerate(imdb_episode_urls):
                yield scrapy.Request(
                    url=imdb_url,
                    callback=self.scrape_imdb_episode,
                    meta={
                        'show_id': show_id,
                        'episode_index': idx,
                        'total_episodes': len(imdb_episode_urls)
                    },
                )
        else:
            yield item

    def scrape_imdb_episode(self, response):
        show_id = response.meta['show_id']
        ep_index = response.meta['episode_index']
        total_eps = response.meta['total_episodes']

        if show_id not in self.imdb_episodes_collected:
            return

        episode_data = {
            "imdb_url": response.url,
            "title": None,
            "year": None,
            "episode_rating": None,
            "episode_number": None,
            "season_number": None,
            "description": None,
            "runtime": None,
        }

        title = response.xpath('//h1//span/text()').get()
        if not title:
            title = response.xpath('//h1/text()').get()
        if not title:
            title = response.xpath('//title/text()').get()
        if title:
            episode_data["title"] = title.strip()

        page_text = ' '.join(response.xpath('//text()[normalize-space()]').getall())
        se_match = re.search(r'S(\d+)\s*E(\d+)', page_text, re.IGNORECASE)
        if se_match:
            episode_data["season_number"] = int(se_match.group(1))
            episode_data["episode_number"] = int(se_match.group(2))

        rating_text = response.xpath(
            '//span[@data-testid="rating"]/text() | //span[contains(@class, "AggregateRatingButton__RatingScore")]/text() | //div[contains(@class, "rating")]/span/text()'
        ).get()
        if rating_text:
            rating_match = re.search(r'([\d.]+)', rating_text)
            if rating_match:
                episode_data["episode_rating"] = float(rating_match.group(1))

        plot = response.xpath(
            '//span[@data-testid="plot-xl"]/text() | //div[contains(@data-testid, "plot")]/span/text() | //p[contains(@class, "GenresAndPlot__Text")]/text()'
        ).get()
        if plot:
            episode_data["description"] = plot.strip()

        runtime_text = response.xpath('//li[contains(text(), "min")]/text()').get()
        if runtime_text:
            runtime_match = re.search(r'(\d+)\s*min', runtime_text)
            if runtime_match:
                episode_data["runtime"] = int(runtime_match.group(1))

        year = response.xpath('//a[contains(@href, "/year/")]/text()').get()
        if not year:
            year_match = re.search(r'(20\d{2}|19\d{2})', page_text)
            if year_match:
                year = year_match.group(1)
        if year:
            episode_data["year"] = year.strip()

        self.logger.info(
            f"Scraped IMDB: {episode_data['title']} S{episode_data.get('season_number')}E{episode_data.get('episode_number')}"
        )

        self.imdb_episodes_collected[show_id]['episodes'].append(episode_data)

        if ep_index >= total_eps - 1 or len(self.imdb_episodes_collected[show_id]['episodes']) >= 5:
            item = self.imdb_episodes_collected[show_id]['item']
            item["imdb_episodes"] = self.imdb_episodes_collected[show_id]['episodes']
            item["episode_names"] = [ep["title"] for ep in item["imdb_episodes"] if ep.get("title")]
            yield item
            del self.imdb_episodes_collected[show_id]
