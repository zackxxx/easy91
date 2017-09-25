import aiohttp_jinja2
from aiohttp import web
import jinja2
import urllib

from crawler import init_crawler

crawler = init_crawler()


async def list(request):
    request.url_raw.query


@aiohttp_jinja2.template('play.html')
async def play(request):
    url = ''
    play_url = ''
    title = ''
    result = None
    try:
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
                url = 'http://91.91p11.space/view_video.php?viewkey=' + view_id
            result = await crawler.api.get('detail', params={'viewkey': view_id})
            print('get view {} res {}'.format(view_id, result))
            play_url = result['download_url']
            title = result['title']
    except Exception as e:
        print(e)
    finally:
        return {'url': url, 'play_url': play_url, 'title': title, 'result': result}


app = web.Application()
aiohttp_jinja2.setup(app,
                     loader=jinja2.FileSystemLoader('./view'))
app.router.add_post('/', play)
app.router.add_get('/', play)

web.run_app(app, port=8080)
