#! /usr/local/bin/python3

from cpcommon import CPCrawler
import asyncio
import collections
import sys
import os
from repository import persist_video, Video

VERBOSE = False
MAX_CONCUR_REQ = 10


def dd(content):
    print(type(content))
    print(content)
    exit(1)


def update(crawler):
    categories = ['rf', 'top', 'hot', 'md', 'rp', 'tf']
    for category in categories:
        videos = crawler.get_lists(category, 1, 6)
        for view_id, video_info in videos.items():
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, persist_video, video_info)


def get_url(crawler, count=200):
    try:
        videos = Video.select().where(Video.downloaded == 0).limit(count)
        if videos.count() > 0:
            result = crawler.get_detail([video.view_id for video in videos])
    except BaseException:
        result = crawler.get_pending_data()
    finally:
        urls = [detail['download_url'] for detail in result if detail is not None]
        with open('data/urls.txt', 'w') as f:
            for url in urls:
                f.write(url + "\n")
        return urls


def init_crawler(debug=False):
    get_real = 'http://91.9p91.com/'
    base_url = 'http://91.91p11.space/'
    crawler = CPCrawler(base_url, get_real, MAX_CONCUR_REQ, debug)
    crawler.set_debug(debug)
    return crawler


def rename(path):
    for filename in os.listdir(path):
        file_info = filename.split('.')
        vno = file_info[0]
        rename_video(vno, filename, path)


def rename_video(vno, origin_file_name, path):
    try:
        video = Video.get(Video.vno == vno)
    except Video.DoesNotExist:
        print('info not found %s', str(vno))
    else:
        file_info = origin_file_name.split('.')
        title = video.title.replace('\n', '').replace('/', '').replace(' ', '')
        if video.user_name is not None:
            user_name = video.user_name.replace('\n', '').replace('/', '').replace(' ', '')
        else:
            user_name = ''
        new_file_name = '{}-{}-{}-{}.{}'.format(title, vno, user_name, video.user_no, file_info[-1])
        os.rename(os.path.join(path, origin_file_name), os.path.join(path, new_file_name))
        video.downloaded = 1
        video.save()
        print('update %s to %s', origin_file_name, new_file_name)


if __name__ == '__main__':

    argv = sys.argv
    running = argv[1:]

    if 'rename' in running:
        path = running[-1]
        rename(path)

    crawler = init_crawler()

    if len(running) == 0:
        update(crawler)
        get_url(crawler, 20)

    if 'update' in running:
        update(crawler)
    if 'url' in running:
        if running[-1].isdigit():
            count = int(running[-1])
        else:
            count = 20
        get_url(crawler, count)
