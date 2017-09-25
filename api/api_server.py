from aiohttp import web
import urllib
import sys
import os

# Add the directory containing your module to the Python path (wants absolute paths)

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))

from crawler import init_crawler, get_config

crawler = init_crawler(debug=True)


async def lists(request):
    meta = {
        'cat': {
            'rf': '最近加精',
            'top': '本月最热',
            'hot': '当前最热',
            'md': '本月讨论',
            'rp': '最近得分',
            'tf': '本月收藏',
            'mf': ' 收藏最多',
            'long': '10分钟以上 ',
        }
    }

    cat = request.rel_url.query.get('cat', None)
    page = request.rel_url.query.get('page', 0)
    extra = {}

    if cat == 'top':
        extra['m'] = request.rel_url.query.get('m', 0)

    data, meta['pagination'] = await crawler.api.get_lists(cat, page, with_meta=True, extra=extra)
    return web.json_response({'data': data, 'meta': meta})


async def user(request):
    meta = {}
    data = {}
    user_no = request.match_info.get('user_no', None)
    if user is not None:
        page = request.rel_url.query.get('page', 1)
        data, meta['pagination'] = await crawler.api.get_user_lists(user_no, page, with_meta=True)

    return web.json_response({'data': data, 'meta': meta})


async def detail(request):
    try:
        data = {}
        if request.method == 'POST':
            data = await request.post()
            url = data.get('url')
            if 'http' in url:
                print('view url {}'.format(url))
                params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                view_ids = params.get('viewkey')
                view_id = view_ids[0]
            else:
                view_id = url
        else:
            view_id = request.match_info.get('view_id', None)
        if view_id:
            data = await crawler.api.get_detail(view_id)
    except Exception as e:
        print(e)
    finally:
        return web.json_response({'data': data})


app = web.Application()

app.router.add_get('/', lists)
app.router.add_get('/user/{user_no}', user)
app.router.add_get('/detail/{view_id}', detail)

web.run_app(app, port=8081)
