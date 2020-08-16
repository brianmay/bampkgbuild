#!/bin/sh
set -ex
for d in stretch buster bullseye sid; do
    docker build --build-arg IMAGE=i386/debian:$d -t brianmay/debian-i386:$d .
    docker build --build-arg IMAGE=debian:$d -t brianmay/debian-amd64:$d .
    docker build --build-arg IMAGE=debian:$d -t brianmay/debian-source:$d .
done
