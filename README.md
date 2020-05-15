# Setup

### Caddy webserver
```
$ docker network create caddynet 
$ docker pull caddy
$ cd docker/caddy
$ vim Caddyfile
```
Change `Caddyfile` to fit your domain
```
$ docker-compose up -d
```
### Run front end
```
$ cd ../..
$ cp .env.sample .env
$ vim .env
```
Fill .env
```
$ docker build -t humanbios-fb . 
$ docker-compose up -d
```

