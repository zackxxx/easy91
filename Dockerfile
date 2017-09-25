FROM frolvlad/alpine-python3

RUN apk add --update --no-cache py-lxml

COPY ./requirements.txt ./

RUN pip install -i https://mirrors.aliyun.com/pypi/simple --no-cache-dir -r requirements.txt

WORKDIR /usr/src/app/easy91/

COPY . .

CMD python3 /usr/src/app/easy91/api/api_server.py $PORT
