#!/bin/sh

# author: martin@affolter.net

container="frontend"
tag="latest"

docker build -t $container:$tag .
docker run \
  -p 8080:80 \
  $container:$tag