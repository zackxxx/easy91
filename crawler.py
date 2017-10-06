#! /usr/local/bin/python3

from cpcommon import CPCrawler
import asyncio
import sys
import os
from repository import persist_video, persist_video_source, Video
from common import dd, get_config

VERBOSE = False
MAX_CONCUR_REQ = 10


def update(crawler):
    categories = ['rf', 'top', 'hot', 'md', 'rp', 'tf']
    for category in categories:
        videos = crawler.get_lists(category, 1, 6)
        for view_id, video_info in videos.items():
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, persist_video, video_info)


def update_source(crawler, end_page=20, start_page=1):
    try:
        step = 20
        total_pages = end_page - start_page + 1
        current_end_page = start_page + step - 1
        while current_end_page <= end_page:
            videos = crawler.get_all(start_page, end_page=current_end_page)
            print(
                'total page {} current page {} to {} with video count {}'.format(total_pages, start_page,
                                                                                 current_end_page,
                                                                                 len(videos)))
            for view_id, video_info in videos.items():
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, persist_video_source, video_info)

            current_end_page += step
            start_page += step
    except KeyboardInterrupt:
        print('current start page is {}'.format(start_page))

    except Exception:
        return start_page
    else:
        return None


def sync_all(crawler, start_page=1, end_page=20):
    while True:
        start_page = int(start_page)
        end_page = int(end_page)
        print('start offset {}'.format(start_page))
        start_page = update_source(crawler, end_page, start_page)
        print('error offset {}'.format(start_page))
        if start_page is None:
            break


def get_url(crawler, count=200):
    try:
        videos = Video.select().where(Video.downloaded == 0).limit(count)
        if videos.count() > 0:
            view_ids = [video.view_id for video in videos]
            result = crawler.get_detail(view_ids)
    except BaseException:
        result = crawler.get_pending_data()
    finally:
        urls = [detail['download_url'] for detail in result if detail is not None]
        deleted = set(view_ids) - set([detail['view_id'] for detail in result if detail is not None])
        deleted_count = len(deleted)
        if deleted_count > 0:
            deleted_count = Video.update(downloaded=-1).where(Video.view_id << deleted).execute()

        print('craw succeed count {}, deleted count {}'.format(len(set(view_ids)) - deleted_count, deleted_count))

        with open('data/urls.txt', 'w') as f:
            for url in urls:
                f.write(url + "\n")
        return urls


def get_detail(crawler, view_ids):
    try:
        result = crawler.get_detail(view_ids)
    except BaseException:
        result = crawler.get_pending_data()

    for video in result:
        persist_video(video)

    urls = [detail['download_url'] for detail in result if detail is not None]
    with open('data/urls.txt', 'w') as f:
        for url in urls:
            f.write(url + "\n")
    print(urls)
    return urls


def get_user_lists(crawler, user_info):
    for user_no, start_page, end_page in user_info:
        videos = crawler.get_user_lists(user_no, start_page, end_page)
        for view_id, video_info in videos.items():
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, persist_video, video_info)


def get_hd_url(crawler, count=200):
    try:
        videos = Video.select().where(Video.downloaded == 0).limit(count)
        if videos.count() > 0:
            view_ids = [video.view_id for video in videos]
            result = crawler.get_hd_detail(view_ids, raw=True)
            dd(result)
    except BaseException:
        result = crawler.get_pending_data()
    finally:
        urls = [detail['download_url'] for detail in result if detail is not None]
        deleted = set(view_ids) - set([detail['view_id'] for detail in result if detail is not None])
        deleted_count = len(deleted)
        # if deleted_count > 0:
        # deleted_count = Video.update(downloaded=-1).where(Video.view_id << deleted).execute()

        print('craw succeed count {}, deleted count {}'.format(len(set(view_ids)) - deleted_count, deleted_count))

        with open('data/urls.txt', 'w') as f:
            for url in urls:
                f.write(url + "\n")
        return urls


def init_url():
    get_real = get_config('URL', 'real')
    base_url = get_config('URL', 'base')
    return get_real, base_url


def init_crawler(debug=False):
    get_real, base_url = init_url()
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
        exit(0)

    debug = bool(get_config('APP', 'debug'))
    crawler = init_crawler(debug=debug)

    if 'sync' in running:
        sync_all(crawler, *(running[1:3]))

    if len(running) == 0:
        update(crawler)
        get_url(crawler, 20)

    if 'user' in running:
        if len(running) > 1:
            user_info = [tuple(running[1:])]
        else:
            user_info = [
                (6165190, 1, 1),
                (6012931, 1, 4),
                (6302848, 1, 4),
                (6011203, 1, 1),
            ]
        get_user_lists(crawler, user_info)

    if 'update' in running:
        update(crawler)

    if len(running) > 0 and 'v' == running[0]:
        get_detail(crawler, running[1:])

    if 'url' in running:
        if running[-1].isdigit():
            count = int(running[-1])
        else:
            count = 20
        get_url(crawler, count)
