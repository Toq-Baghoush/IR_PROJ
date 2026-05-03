# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import logging


class TvshowCrawlerPipeline:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def process_item(self, item, spider=None):
        try:
            adapter = ItemAdapter(item)
            
            # Log incoming item
            self.logger.info(f"Processing item: {adapter.get('link', 'NO LINK')}")

            if adapter.get('showname'):
                adapter['showname'] = " ".join(adapter['showname'].split())
                
            if adapter.get('link') and not adapter['link'].startswith('http') and spider is not None:
                base = getattr(spider, "start_urls", [""])[0] or ""
                adapter['link'] = base.rstrip("/") + "/" + adapter['link'].lstrip("/")
            
            if adapter.get('plot'):
                adapter['plot'] = " ".join(adapter['plot'].split())
                
            if adapter.get('rating') is not None:
                # rating is a float, convert to string if needed
                if isinstance(adapter['rating'], str):
                    adapter['rating'] = " ".join(adapter['rating'].split())
            
            self.logger.info(f"Item processed successfully")
            return item
        except Exception as e:
            self.logger.error(f"Error processing item: {e}", exc_info=True)
            raise
