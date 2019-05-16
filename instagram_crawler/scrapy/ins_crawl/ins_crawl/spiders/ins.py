
# -*- coding: utf-8 -*-
import scrapy
import requests
import json
import logging

from urllib.parse import (urlencode, urljoin)
from ins_crawl.spiders.config import *
from ins_crawl.items import InsCrawlItem

LOGGER = logging.getLogger(__name__)


class InsSpider(scrapy.Spider):
    name = 'ins'
    allowed_domains = ['instagram.com']
    start_urls = ['http://instagram.com/']

    def __init__(self, username='taeri__taeri', *args, **kwargs):
        super(InsSpider, self).__init__(*args, **kwargs)
        self.username = username
        self.shared_data = self.get_shared_data()

    def request(self, end_cursor, callback):
        url = urljoin(self.start_urls[0], 'graphql/query/') + '?'
        params = {
            'query_hash': 'f2405b236d85e8296cf30347c9f08c2a',
            'variables':
                '{{"id":"{0}","first":{1},"after":"{2}"}}'.format(
                    self.user_id, 50, end_cursor),
        }
        url = url + urlencode(params)
        request = scrapy.Request(url=url, callback=callback, meta={'proxy': 'http://127.0.0.1:8001'})
        request.cookies['csrftoken'] = CSRFTOKEN
        request.headers[
            'User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'
        return request

    def start_requests(self):

        if self.shared_data is not None:
            user = self.shared_data['entry_data']['ProfilePage'][0]['graphql']['user']
            self.user_id = user['id']
            self.count = user['edge_owner_to_timeline_media']['count']
            LOGGER.info('\n{}\nUser id:{}\nTotal {} photos.\n{}\n'.format('-' * 20, self.user_id, self.count, '-' * 20))
            for i, url in enumerate(self.start_urls):
                yield self.request("", self.parse_item)
        else:
            LOGGER.error('-----[ERROR] shared_data is None.')

    def parse_item(self, response):
        j = json.loads(response.text)
        edge_media = j['data']['user']['edge_owner_to_timeline_media']
        edges = edge_media['edges']
        if edges:
            for edge in edges:
                item = InsCrawlItem()
                item['image_url'] = edge['node']['display_url']
                item['username'] = self.username
                yield item
            has_next_page = edge_media['page_info']['has_next_page']
            if has_next_page:
                end_cursor = edge_media['page_info']['end_cursor']
                yield self.request(end_cursor, self.parse_item)
            else:
                LOGGER.info('获取照片完毕.')

    def get_shared_data(self):
        """
        获取 shared data
        :return:
        """
        try:
            proxies = {
                'http': 'http://' + PROXY,
                'https': 'https://' + PROXY
            }
            with requests.get(self.start_urls[0] + self.username, proxies=proxies) as resp:
                # with scrapy.Request(self.start_urls[0] + self.username, meta={'proxy':'http://' + PROXY}) as resp:
                html = resp.text
                if html is not None and '_sharedData' in html:
                    shared_data = html.split("window._sharedData = ")[1].split(
                        ";</script>")[0]
                    if not shared_data:
                        print('Not found [share data]')
                        exit(1)
                    return json.loads(shared_data)
        except Exception as exc:
            LOGGER.error('[-----]', repr(exc))
