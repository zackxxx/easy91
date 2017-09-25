FROM frolvlad/alpine-python3

COPY ./requirements.txt ./

RUN pip install -i https://mirrors.aliyun.com/pypi/simple --no-cache-dir -r requirements.txt

WORKDIR /usr/src/app/easy91/

COPY . .

EXPOSE 8081

CMD [ "python3", "/usr/src/app/easy91/api/api_server.py" ]
