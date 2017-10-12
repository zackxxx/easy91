FROM frolvlad/alpine-python3

RUN apk add --update --no-cache py-lxml \
        vim \
        && rm -rf /var/cache/apk/*

COPY ./requirements.txt ./

RUN pip3 install -i https://mirrors.aliyun.com/pypi/simple --no-cache-dir -r requirements.txt

WORKDIR /usr/src/app/
COPY . .
COPY ./config.ini.prod ./config.ini

CMD python3 /usr/src/app/api/api_server.py $PORT
