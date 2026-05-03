import re
from urllib.parse import parse_qs, unquote, urlparse

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
            # Use Selenium to render the show detail page
            yield scrapy.Request(url, callback=self.parse_show, meta={"selenium": True})

    def parse_show(self, response):
        item = TvshowCrawlerItem()
        item["link"] = response.url

        # --- Show name ---
        showname = response.css("h3::text").get()
        if showname:
            item["showname"] = showname.strip()

        # --- Rating ---
        # Adjust selector to match the actual rating element on the page
        rating_text = response.css("strong::text").get()
        if rating_text:
            match = re.search(r"([\d.]+)", rating_text.strip())
            if match:
                item["rating"] = float(match.group(1))

        # --- Poster ---
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

        # --- Seasons & Episodes (via Selenium) ---
        # Try to extract from rendered chart using browser automation
        try:
            driver = response.meta.get("driver")
            if driver:
                # Wait for chart to load
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.by import By

                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_all_elements_located((By.XPATH, "//text()[contains(., 'S')]")))

                # Extract season numbers from chart (S1, S2, S3, ...)
                season_labels = driver.execute_script(
                    """
                    let seasonText = document.body.innerText;
                    let matches = seasonText.match(/S\\d+/g);
                    return matches ? [...new Set(matches)] : [];
                    """
                )
                if season_labels:
                    season_nums = [int(s[1:]) for s in season_labels]
                    item["seasons"] = max(season_nums) if season_nums else None

                # Try to extract episode data from the chart
                episode_data = driver.execute_script(
                    """
                    let episodes = [];
                    let rect = document.querySelector('[class*="recharts"]');
                    if (rect) {
                        let points = rect.querySelectorAll('circle');
                        points.forEach(p => {
                            let title = p.getAttribute('title') || p.getAttribute('data-title') || '';
                            if (title) episodes.push(title);
                        });
                    }
                    return episodes.length > 0 ? episodes : null;
                    """
                )
                if episode_data:
                    item["episode_names"] = [episode_data]
                    item["episodes"] = [len(episode_data)]
        except Exception as e:
            self.logger.warning(f"Error extracting episode data via Selenium: {e}")

        yield item
