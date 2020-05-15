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
Fill .env (Note: If using docker, ensure that server names and ports reflect the docker container name and port. Example: SERVER_ADDRESS=http://humanbios-server:8282  
```
$ docker build -t humanbios-fb . 
$ docker-compose up -d
```

