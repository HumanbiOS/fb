FROM docker.io/alpine:3.11

RUN apk add --no-cache \
      py3-aiohttp \
      py3-magic \
      py3-sqlalchemy \
      py3-psycopg2 \
      py3-beautifulsoup4 \
      #hbmqtt
          py3-yaml \
      py3-idna \
      py3-cffi \
      su-exec

COPY . app/
WORKDIR /app

RUN apk add --virtual .build-deps python3-dev libffi-dev build-base \
 && pip3 install --upgrade pip \
 && pip3 install -r requirements.txt \
 && apk del .build-deps

CMD python3 ./app.py
