import asyncio
import tqdm
from httpcommon import HttpCommon, USER_AGENTS
import re
from urllib import parse
import json


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
        if self.debug:
            print('start parse content from {}'.format(self._get_endpoint_real_url(endpoint)))
        return parser(str(content), **extract)

    async def get(self, endpoint, params=None):
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
            content = await self.http_get(url=self._get_endpoint_real_url(endpoint), params=params,
                                          cookies=self.cookies)
            if self.debug:
                print('finish craw {} with params {}'.format(self._get_endpoint_real_url(endpoint), params))

        return self.parse(endpoint, content)

    def set_debug(self, debug=False):
        self.debug = debug


class CPParser:
    CP_REGS = {
        'view_id': re.compile('viewkey=(.*?)&'),
        'list_video_info': re.compile(
            'class="listchannel"([\w\W]*?)viewkey=([\w\W]*?)&([\w\W]*?)<img src="([\w\W]*?)"([\w\W]*?)title="([\w\W]*?)"([\w\W]*?)时长:</span>([\w\W]*?)\\n([\w\W]*?)作者([\w\W]*?)UID=([\d]*?)"([\w\W]*?)>([\w\W]*?)<'),
        'user_video_info': re.compile(
            'class="myvideo([\w\W]*?)viewkey=([\w\W]*?)"><img height=90 src="([\w\W]*?)"([\w\W]*?)viewkey=([\w\W]*?)">([\w\W]*?)</a>'),
        'following_video_info': re.compile(
            'class="myvideo([\w\W]*?)viewkey=([\w\W]*?)">([\w\W]*?)src="([\w\W]*?)"([\w\W]*?)viewkey=([\w\W]*?)">([\w\W]*?)</a>'),
        'vid': re.compile('\?VID=(.*?)"'),
        'title': re.compile('<title>([\w\W]*?)-'),
        'user': re.compile('<span class="info">作者([\w\W]*?)UID=([\d]*?)"([\w\W]*?)>([\w\W]*?)<'),
        'username': re.compile('receiver=([\w\W]*?)"'),
        'time': re.compile('时长:</span>([\w\W]*?)\\n'),
        'url': re.compile('<source src="([\w\W]*?)"'),
        'vno': re.compile('_([\w\W]*?)\.'),
    }

    def parse_lists(self, content, videos_info={}):
        raw_video_infos = self.CP_REGS['list_video_info'].findall(content)

        for raw_video_info in raw_video_infos:
            view_id = raw_video_info[1]
            img_url = raw_video_info[3]
            title = raw_video_info[5]
            vtime = raw_video_info[7]
            user_no = raw_video_info[10]
            user_name = raw_video_info[12]
            vno = re.compile('_([\w\W]*?)\.').findall(str(img_url))[0]

            videos_info[view_id] = {
                'view_id': view_id,
                'title': title,
                'vtime': vtime,
                'vno': vno,
                'user_name': user_name,
                'user_no': user_no,
                'img_url': img_url
            }
        return videos_info

    def parse_user(self, content, videos_info={}):
        raw_user_video_infos = self.CP_REGS['user_video_info'].findall(content),
        for raw_video_info in raw_user_video_infos:
            view_id = raw_video_info[1]
            img_url = raw_video_info[2]
            title = raw_video_info[5]
            vno = self.CP_REGS['vno'].findall(str(img_url))[0]
            videos_info[view_id] = {
                'view_id': view_id,
                'title': title,
                'vno': vno,
                'img_url': img_url
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

        content = str(content)

        video_info = {
            'vid': self.CP_REGS['vid'].findall(content)[0],
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

    def get_detail(self, view_ids):
        desc = '详情'
        data = self.set_todo(
            [self.api.get('detail', params={'viewkey': view_id}) for view_id in view_ids]).run(desc)
        return data

    def trans_lists_to_dict(self, l):
        data = {}
        for dic in l:
            data.update(dic)

        return data
