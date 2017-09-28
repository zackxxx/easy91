import asyncio
import tqdm
from httpcommon import HttpCommon
import re
from urllib import parse
import json
from bs4 import BeautifulSoup


def dd(content):
    print(type(content))
    print(content)
    exit(1)


class CPError(Exception):
    def __init__(self, msg, error_code=None):
        self.error_code = error_code
        super(CPError, self).__init__(msg)

    @property
    def msg(self):
        return self.args[0]


class CPApi(HttpCommon):
    END_POINT = {
        'lists': {'uri': 'v.php', 'auth': False, 'parser': 'parse_lists'},
        'following': {'uri': 'my_subs.php', 'auth': False, 'parser': 'parse_following'},
        'user': {'uri': 'uvideos.php', 'auth': False, 'parser': 'parse_user'},
        'detail': {'uri': 'view_video.php', 'auth': False, 'parser': 'parse_detail'},
        'hd_detail': {'uri': 'view_video.php', 'auth': False, 'parser': 'parse_hd_detail'},
        'info': {'uri': 'getfile_jw.php', 'auth': False, 'parser': 'parse_info'},
        'hd_detail': {'uri': 'view_video_hd.php', 'auth': False, 'parser': 'parse_hd_detail'},
    }

    def __init__(self, base_url, get_real_base_url, semaphore, debug=False):
        self.debug = debug
        self.semaphore = semaphore
        self.cp_parser = CPParser()
        self.get_real_base_url = get_real_base_url
        self.base_url = base_url
        self.init_cookies()

    def set_cookie(self, filename):
        with open(filename, 'r') as f:
            self.cookies = json.loads(f.read())

    def init_cookies(self):
        self.cookies = {'language': 'cn_CN'}

    def _endpoint_setting(self, endpoint, key=None):
        setting = self.END_POINT.get(endpoint, None)
        if setting is None:
            raise CPError('endpoint not exist')
        if key is not None:
            return setting[key]
        return setting

    def _get_endpoint_real_url(self, endpoint):
        if endpoint == 'info':
            self.get_real_base_url + self._endpoint_setting(endpoint, 'uri')
        return self.base_url + self._endpoint_setting(endpoint, 'uri')

    def _endpoint_need_auth(self, endpoint):
        return self._endpoint_setting(endpoint, 'auth')

    def parse(self, endpoint, content, **extract):
        parser = getattr(self.cp_parser, self._endpoint_setting(endpoint, 'parser'))
        print(parser)
        if self.debug:
            print('start parse content from {}'.format(self._get_endpoint_real_url(endpoint)))
        return parser(str(content), **extract)

    async def get(self, endpoint, params=None, raw=False, pagination=False):
        '''
        :param endpoint: lists, following, user, detail, hd_detail, info
        :param params:
            category
            viewkey
            UID
            page
            type=public
            VID
        :return:
        '''

        with (await self.semaphore):
            if self._endpoint_need_auth(endpoint):
                self.cookies = self.get_auth_cookie()
            if self.debug:
                print('start craw {} with params {}'.format(self._get_endpoint_real_url(endpoint), params))
            try:
                content = await self.http_get(url=self._get_endpoint_real_url(endpoint), params=params,
                                              cookies=self.cookies)
            except Exception as error:
                print('fail craw {} with params {}, error: {}'.format(self._get_endpoint_real_url(endpoint), params,
                                                                      error))
                with open('fail_page', 'a') as f:
                    f.write(json.dumps(params) + '\n')
                return {}
            else:
                if self.debug:
                    print('finish craw {} with params {}'.format(self._get_endpoint_real_url(endpoint), params))
                if raw:
                    return content

                data = self.parse(endpoint, content)

                if self.debug:
                    print('get {} with item count {}'.format(endpoint, len(data)))

                if self.debug:
                    file_name = endpoint
                    for k, v in params.items():
                        file_name += str(k) + '-' + str(v)
                    with open('../example/' + file_name, 'w', encoding='utf-8') as f:
                        f.write(content)

                if pagination:
                    import urllib
                    last_page, current_page = self.cp_parser.get_pagination(content)
                    pagination = {
                        'last_page': last_page,
                        'current_page': current_page,
                        'per_page': len(data),
                        'source_url': self._get_endpoint_real_url(endpoint) + '?' + urllib.parse.urlencode(params)
                    }
                    return data, pagination

                return data

    def set_debug(self, debug=False):
        self.debug = debug

    # 对外接口
    async def get_lists(self, category=None, page=1, with_meta=False, extra={}):
        if category is None:
            return await self.get('lists', params={'next': 'watch', 'page': page}, pagination=with_meta)
        else:
            params = {'category': category, 'page': page}
            params.update(extra)
            return await self.get('lists', params=params, pagination=with_meta)

    async def get_detail(self, view_id):
        return await self.get('detail', params={'viewkey': view_id})

    async def get_user_lists(self, user_no, page, with_meta=False):
        return await self.get('user', params={'UID': user_no, 'page': page}, pagination=with_meta)


class CPParser:
    CP_REGS = {
        'view_id': re.compile('viewkey=(.*?)&'),
        'pages': re.compile('page=([\w\W]*?)\"'),
        'current_page': re.compile('<span class="pagingnav">([\w\W]*?)</span>'),
        'list_video_info': re.compile(
            'class="listchannel"([\w\W]*?)viewkey=([\w\W]*?)&([\w\W]*?)<img src="([\w\W]*?)"([\w\W]*?)title="([\w\W]*?)"([\w\W]*?)时长:</span>([\w\W]*?)\\n([\w\W]*?)作者([\w\W]*?)UID=([\d]*?)"([\w\W]*?)>([\w\W]*?)<'),
        'user_video_info': re.compile(
            'class="myvideo([\w\W]*?)viewkey=([\w\W]*?)"><img height=90 src="([\w\W]*?)"([\w\W]*?)viewkey=([\w\W]*?)">([\w\W]*?)</a>'),
        'following_video_info': re.compile(
            'class="myvideo([\w\W]*?)viewkey=([\w\W]*?)">([\w\W]*?)src="([\w\W]*?)"([\w\W]*?)viewkey=([\w\W]*?)">([\w\W]*?)</a>'),
        'vid': re.compile('\?VID=(.*?)"'),
        'content_view_id': re.compile('viewkey=(.*?)[\"|&]'),
        'content_vno': re.compile('/(\d*?)\.mp4'),
        'title': re.compile('<title>([\w\W]*?)-'),
        'user': re.compile('<span class="info">作者([\w\W]*?)UID=([\d]*?)"([\w\W]*?)>([\w\W]*?)<'),
        'username': re.compile('receiver=([\w\W]*?)"'),
        'time': re.compile('时长:</span>([\w\W]*?)\\n'),
        'url': re.compile('<source src="([\w\W]*?)"'),
        'vno': re.compile('_([\w\W]*?)\.'),
    }

    @staticmethod
    def parse_lists(content):
        videos_info = {}

        bs = BeautifulSoup(content, 'lxml')

        bs_videos = bs.find_all('div', attrs={'class': 'listchannel'})

        for bs_video in bs_videos:
            bs_link = bs_video.find_all('a')
            source_link = bs_link[0].get('href')
            view_id = re.compile('viewkey=([0-9a-z]+)').findall(source_link)[0]
            img_url = bs_link[0].find('img').get('src').replace('1_', '').replace('2_', '').replace('3_', '')
            title = bs_link[0].find('img').get('title')
            user_no = re.compile('UID=(\d+)').findall(bs_link[-1].get('href'))[0]
            vtime = re.compile('时长:([\w\W]*?)\n').findall(bs_video.text)[0]
            user_name = bs_link[-1].text
            vno = re.compile('/(\d+)\.').findall(str(img_url))[0]

            videos_info[view_id] = {
                'view_id': view_id,
                'title': title,
                'vtime': vtime,
                'vno': vno,
                'user_name': user_name,
                'user_no': user_no,
                'img_url': img_url,
                'source': source_link
            }
        return videos_info

    @classmethod
    def get_pagination(cls, content):
        pages = cls.CP_REGS['pages'].findall(content)
        pages.append('1')
        current_page = int(cls.CP_REGS['current_page'].findall(content)[0])
        pages = [int(page) for page in pages if page.isnumeric()]
        return max(current_page, max(pages)), current_page

    @classmethod
    def parse_user(cls, content):
        videos_info = {}

        bs = BeautifulSoup(content, 'lxml')
        print(bs)
        for bs_video in bs.find_all('div', attrs={'class': 'myvideo'}):
            detail = bs_video.find('p').text
            created_at = re.compile('添加时间: ([\w\W]*?)\n').findall(detail)[0]
            vtime = re.compile('时长: ([\w\W]*?)\ ').findall(detail)[0]
            bs_video_link = bs_video.find('p').find('a')
            view_id = bs_video_link.get('href').split('=')[-1]
            title = bs_video_link.text
            img_url = bs_video.find('img').get('src')
            vno = cls.CP_REGS['vno'].findall(str(img_url))[0]
            videos_info[view_id] = {
                'view_id': view_id,
                'title': title,
                'vno': vno,
                'img_url': img_url,
                'vtime': vtime,
                'created_at': created_at,
                'detail': detail,
            }

        return videos_info

    def parse_following(self, content, videos_info={}):
        raw_user_video_infos = self.CP_REGS['following_video_info'].findall(content)
        for raw_video_info in raw_user_video_infos:
            view_id = raw_video_info[1]
            img_url = raw_video_info[3]
            title = raw_video_info[6]
            vno = self.CP_REGS['vno'].findall(str(img_url))[0]

            videos_info[view_id] = {
                'view_id': view_id,
                'title': title,
                'vno': vno,
                'img_url': img_url
            }
        return videos_info

    def parse_detail(self, content):
        if '视频不存在' in content:
            print('视频已删除')
            return None

        bs = BeautifulSoup(content, 'lxml')

        bs_detail = bs.find('div', attrs={'id': 'videodetails'})
        # print(bs)
        bs_links = bs_detail.find_all('a')

        video_info = {
            'view_id': self._parse_item_view_id(str(bs)),
            'vno': re.compile('/(\d+)\.mp4').findall(bs.find('source').get('src'))[0],
            'title': bs.find('div', attrs={'id': 'viewvideo-title'}).text,
            'vid': self._parse_item_vid(bs_detail.text),
            'user_no': self._parse_item_user_no(bs_links[0].get('href')),
            'user_name': bs_links[0].text,
            'download_url': bs.find('source').get('src'),
            'vtime': self._parse_item_vtime(bs.text),
            'img_url': bs.find('video').get('poster'),
            'created_at': self._parse_item_created_at(bs_detail.text),
            'detail': bs.find('meta', attrs={'name': 'description'}).get('content'),
            'is_good': '精品电影' in bs_detail.text,
        }

        return video_info

    @staticmethod
    def _parse_item_vid(string):
        return re.compile('VID=([\w\W]*?)\n').findall(string)[0]

    @staticmethod
    def _parse_item_view_id(string):
        return re.compile('viewkey=([0-9a-z]+)').findall(string)[0]

    @staticmethod
    def _parse_item_user_no(string):
        return re.compile('UID=(\d+)').findall(string)[0]

    @staticmethod
    def _parse_item_vtime(string):
        return re.compile('时长: ([\w\W]*?)\s').findall(string)[0]

    @staticmethod
    def _parse_item_created_at(string):
        return re.compile('添加时间: ([\w\W]*?)\s').findall(string)[0]

    def parse_hd_detail(self, content):
        if '视频不存在' in content:
            print('视频已删除')
            return None

        content = str(content)

        video_info = {
            'vid': self.CP_REGS['vid'].findall(content)[0],
            'vno': self.CP_REGS['content_vno'].findall(content)[0],
            'view_id': self.CP_REGS['content_view_id'].findall(content)[0],
            'user_no': int(self.CP_REGS['user'].findall(content)[0][1].strip()),
            'user_name': self.CP_REGS['username'].findall(content)[0].strip(),
            'download_url': self.CP_REGS['url'].findall(content)[0],
            'vtime': self.CP_REGS['time'].findall(content)[0].strip(),
        }

        return video_info

    def parse_info(self, content):
        return parse.parse_qs(str(content))


class CPCrawler:
    def __init__(self, base_url, get_real_base_url, concur_req, verbose):
        self.verbose = verbose
        self.concur_req = concur_req
        semaphore = asyncio.Semaphore(self.concur_req)
        self.api = CPApi(base_url, get_real_base_url, semaphore)
        self.todo = []
        self.pending_data = []

    def set_debug(self, debug=True):
        self.api.set_debug(debug)

    def run(self, desc=None):
        loop = asyncio.get_event_loop()
        self.flush_pending_data()
        data = loop.run_until_complete(self.crawler_coro(self.get_todo(), self.pending_data, desc))
        return data

    async def crawler_coro(self, todo, data=[], desc=None):
        todo_iter = asyncio.as_completed(todo)
        if not self.verbose:
            todo_iter = tqdm.tqdm(todo_iter, total=len(todo))
        for future in todo_iter:
            res = await future
            data.append(res)

        return data

    def get_todo(self):
        todo = self.todo[:]
        self.flush_todo()
        return todo

    def set_todo(self, todo):
        self.todo = todo
        return self

    def flush_todo(self):
        self.todo = []
        return self

    def get_pending_data(self):
        pending_data = self.pending_data[:]
        self.flush_pending_data()
        return pending_data

    def flush_pending_data(self):
        self.pending_data = []
        return self

    def get_lists(self, category, start_page, end_page):
        desc = '分类 {}, {} 页 到 {} 页'.format(category, start_page, end_page)
        data = self.set_todo([self.api.get('lists', params={'category': category, 'page': page}) for page in
                              range(start_page, end_page + 1)]).run(desc)
        return self.trans_lists_to_dict(data)

    def get_all(self, start_page, end_page):
        desc = '更新源, {} 页 到 {} 页'.format(start_page, end_page)
        data = self.set_todo([self.api.get('lists', params={'next': 'watch', 'page': page}) for page in
                              range(start_page, end_page + 1)]).run(desc)

        print('craw page {} to {}, data count {}'.format(start_page, end_page, len(self.trans_lists_to_dict(data))))
        return self.trans_lists_to_dict(data)

    def get_detail(self, view_ids):
        desc = '详情'
        data = self.set_todo(
            [self.api.get('detail', params={'viewkey': view_id}) for view_id in view_ids]).run(desc)
        return data

    def get_user_lists(self, user_no, start_page, end_page):
        desc = '用户NO {}, {} 页 到 {} 页'.format(user_no, start_page, end_page)
        data = self.set_todo([self.api.get('user', params={'UID': user_no, 'page': page}) for page in
                              range(start_page, end_page + 1)]).run(desc)
        return self.trans_lists_to_dict(data)

    def get_hd_detail(self, view_ids, raw=False):
        desc = '详情'
        data = self.set_todo(
            [self.api.get('hd_detail', params={'viewkey': view_id}, raw=raw) for view_id in view_ids]).run(desc)
        return data

    def trans_lists_to_dict(self, l):
        data = {}
        for dic in l:
            data.update(dic)

        return data
