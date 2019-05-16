import logging
import scrapy
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exceptions import DropItem

LOGGER = logging.getLogger(__name__)


class InsImagesPipeline(ImagesPipeline):

    def get_media_requests(self, item, info):
        image_url = item['image_url']
        yield scrapy.Request(image_url, meta={'proxy': 'http://127.0.0.1:8001'})

    def item_completed(self, results, item, info):
        image_paths = [x['path'] for ok, x in results if ok]
        if not image_paths:
            raise DropItem("Item contains no images")
        print('-----[DOWLOADING]开始下载:', item['image_url'])
        return item
