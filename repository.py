from peewee import *
from common import dd, get_config


def init_db():
    driver = get_config('DATABASE', 'driver')
    host = get_config(driver, 'host')
    username = get_config(driver, 'username')
    password = get_config(driver, 'password')
    database = get_config(driver, 'database')
    port = int(get_config(driver, 'port'))

    if driver == 'POSTGRESQL':
        db = PostgresqlDatabase(database, user=username, host=host, password=password)
    elif driver == 'SQLITE':
        from playhouse.sqlite_ext import SqliteExtDatabase
        db = SqliteExtDatabase('data/database.db')
    elif driver == 'MYSQL':
        db = MySQLDatabase(database, user=username, host=host, password=password, port=port)
    else:
        raise NotSupportedError
    return db


db = init_db()


class BaseModel(Model):
    class Meta:
        database = db


class Video(BaseModel):
    id = IntegerField(primary_key=True)
    view_id = CharField(null=True, unique=True)
    title = CharField(null=True, default=0)
    img_url = CharField(null=True)
    download_url = CharField(null=True, default=0)
    vid = CharField(null=True)
    vno = CharField(null=True)
    vtime = CharField(null=True)
    user_name = CharField(null=True)
    user_no = CharField(null=True)
    downloaded = IntegerField(default=0)


class VideoSource(BaseModel):
    id = IntegerField(primary_key=True)
    view_id = CharField(null=True, unique=True)
    title = CharField(null=True, default=0)
    img_url = CharField(null=True)
    download_url = CharField(null=True, default=0)
    vid = CharField(null=True)
    vno = CharField(null=True)
    vtime = CharField(null=True)
    user_name = CharField(null=True)
    user_no = CharField(null=True)
    downloaded = IntegerField(default=0)


Video.create_table(True)
VideoSource.create_table(True)


def persist_video(video_info):
    try:
        if video_info is None:
            return None
        video = Video.get(Video.view_id == video_info['view_id'])
        print('{} exist, skip'.format(video_info['view_id']))
        return video
    except Video.DoesNotExist:
        try:
            video = Video.create(**video_info)
            print('save {}, success'.format(video_info['view_id']))
            return video
        except Exception as e:
            print(e)


def persist_video_source(video_info):
    try:
        if video_info is None:
            return None
        video = VideoSource.get(VideoSource.view_id == video_info['view_id'])
        # print('{} exist, skip'.format(video_info['view_id']))
    except VideoSource.DoesNotExist:
        video = VideoSource.create(**video_info)
        # print('save {}, success'.format(video_info['view_id']))

    return video
