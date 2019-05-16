import json
import multiprocessing
import sys
import time
from urllib.parse import urljoin

import aiohttp
import asyncio
import os
import re

from pathlib import Path

import requests

ROOT_URL = 'https://www.instagram.com/'
PROXY = 'http://127.0.0.1:8001'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
    'Cookie': 'csrftoken=2JzdvnHL9iMuxbV7KiJcASk8RlKuYWAQ'
}
USERNAME = 'ponysmakeup'
PATH = Path(f'./instagram/{USERNAME}')
PATH.mkdir(parents=True, exist_ok=True)


class Instagram:

    def __init__(self, username, maxtasks=200):
        self.username = username
        self.maxtasks = maxtasks  # 最大任务数
        self.queue = asyncio.Queue(maxsize=maxtasks * 2)
        os.environ['http_proxy'] = PROXY
        os.environ['https_proxy'] = PROXY
        self.session = aiohttp.ClientSession(trust_env=True, headers=HEADERS)
        self.num = []

    async def produce_download_urls(self, max=50):
        """
        获取每一页的所有照片链接
        :param max: 一次要获取照片数量
        :return:
        """
        end_cursor = ''
        while True:
            pic_params = {
                'query_hash':
                    'f2405b236d85e8296cf30347c9f08c2a',
                'variables':
                    '{{"id":"{0}","first":{1},"after":"{2}"}}'.format(
                        self.user_id, max, end_cursor),
            }
            pic_url = ROOT_URL + 'graphql/query/'
            async with self.session.get(pic_url, params=pic_params) as resp:
                json = await resp.json()
                edge_media = json['data']['user'][
                    'edge_owner_to_timeline_media']
                edges = edge_media['edges']
                if edges:
                    for edge in edges:
                        await self.queue.put(edge['node']['display_url'])  # queue通信
                    has_next_page = edge_media['page_info']['has_next_page']
                    if has_next_page:
                        end_cursor = edge_media['page_info']['end_cursor']
                    else:
                        break

    async def download(self):
        """
        下载照片
        :return:
        """
        while not (self.producer.done() and self.queue.empty()):
            url = await self.queue.get()  # 获取
            self.num.append(self.queue.qsize())
            filename = PATH / url.split('?')[0].split('/')[-1]
            async with self.session.get(url) as resp:
                with filename.open('wb') as f:
                    async for chunk in resp.content.iter_any():
                        f.write(chunk)
            self.queue.task_done()
            print('.', end='', flush=True)
            print('耗时:', time.time() - self.start)
            # if len(self.num) == self.count:
            #     print('\nProduce done, Total %r photos, plz wait save done :)' % self.count)
            #     print(self.queue.qsize())

    def deep_get(self, dict, path):
        """
        从dict中获取path中的项
        :param dict:
        :param path:
        :return:
        """

        def _split_indexes(key):
            split_array_index = re.compile(r'[.\[\]]+')  # ['foo', '0']
            return filter(None, split_array_index.split(key))

        ends_with_index = re.compile(r'\[(.*?)\]$')  # foo[0]

        keylist = path.split('.')

        val = dict

        for key in keylist:
            try:
                if ends_with_index.search(key):
                    for prop in _split_indexes(key):
                        if prop.isdigit():
                            val = val[int(prop)]
                        else:
                            val = val[prop]
                else:
                    val = val[key]
            except (KeyError, IndexError, TypeError):
                return None

        return val

    async def get_shared_data(self):
        """
        获取 shared data
        :return:
        """
        try:
            async with self.session.get(ROOT_URL + self.username) as resp:
                html = await resp.text()
                if html is not None and '_sharedData' in html:
                    shared_data = html.split("window._sharedData = ")[1].split(
                        ";</script>")[0]
                    if not shared_data:
                        print('!!!!!!!')
                        exit(1)
                    return json.loads(shared_data)
        except Exception:
            pass

    async def init(self):
        """
        初始化必要参数
        :return:
        """
        user = (await self.get_shared_data())['entry_data']['ProfilePage'][0]['graphql']['user']
        if not user:
            print('user is none.')
            exit(1)
        self.user_id = user['id']  # user id
        self.count = user['edge_owner_to_timeline_media']['count']  # 照片数量

    async def close(self):
        await self.session.close()

    async def run(self):
        """
        :return:
        """
        self.start = time.time()
        print('Preparing...')
        print('Initializing...')
        await self.init()
        print('User id: %r.' % self.user_id)
        print('Total %r photos.' % self.count)
        self.producer = asyncio.create_task(self.produce_download_urls())
        print('Downloading...', end='', flush=True)
        await asyncio.gather(*(self.download() for _ in range(self.maxtasks)))



async def main():
    ins = Instagram(USERNAME)
    try:
        await ins.run()
    finally:
        await ins.close()


def check(_):
    print('Start check...')
    with requests.get(urljoin(ROOT_URL, USERNAME), headers=HEADERS,
                 proxies={'http': 'http://localhost:80001', 'https': 'https://localhost:8001'}) as resp:
        pattern = '"edge_owner_to_timeline_media":.?{"count":(.*?),"page_info"'
        count = int(re.findall(pattern, resp.text)[0])
        while True:
            files = len(os.listdir(PATH))
            print('Check files:%r' % files)
            if files == count:
                # print('Total %r photos download done.' % count)
                print('\nProduce done, Total %r photos, plz wait save done :)' % count)
                sys.exit(0)


if __name__ == '__main__':
    try:
        p = multiprocessing.Process(target=check, args=(0,))
        p.start()
        future = asyncio.ensure_future(main())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
        loop.close()
    except KeyboardInterrupt:
        pass
