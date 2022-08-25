#!/bin/sh
set -ex

build() {
    src="$1"
    dst="$2"
    dist="$3"
    platform="$4"
    security="$5"

    docker pull "$src"
    docker build --platform "$platform" --build-arg IMAGE="$src" --build-arg DISTRIBUTION="$dist" --build-arg SECURITY="$security" -t "$dst" .
}

for d in sid; do
    build "i386/debian:$d" "brianmay/debian-i386:$d" "$d" "linux/i386" "none"
    build "debian:$d" "brianmay/debian-amd64:$d" "$d" "linux/amd64" "none"
    build "debian:$d" "brianmay/debian-source:$d" "$d" "linux/amd64" "none"
done

for d in buster; do
    build "i386/debian:$d" "brianmay/debian-i386:$d" "$d" "linux/i386" "pre-bullseye"
    build "i386/debian:$d" "brianmay/debian-i386:$d-security" "$d" "linux/i386" "pre-bullseye"

    build "debian:$d" "brianmay/debian-amd64:$d" "$d" "linux/amd64" "pre-bullseye"
    build "debian:$d" "brianmay/debian-amd64:$d-security" "$d" "linux/amd64" "pre-bullseye"

    build "debian:$d" "brianmay/debian-source:$d" "$d" "linux/amd64" "pre-bullseye"
    build "debian:$d" "brianmay/debian-source:$d-security" "$d" "linux/amd64" "pre-bullseye"
done

for d in bullseye; do
    build "i386/debian:$d" "brianmay/debian-i386:$d" "$d" "linux/i386" "bullseye"
    build "i386/debian:$d" "brianmay/debian-i386:$d-security" "$d" "linux/i386" "bullseye"

    build "debian:$d" "brianmay/debian-amd64:$d" "$d" "linux/amd64" "bullseye"
    build "debian:$d" "brianmay/debian-amd64:$d-security" "$d" "linux/amd64" "bullseye"

    build "debian:$d" "brianmay/debian-source:$d" "$d" "linux/amd64" "bullseye"
    build "debian:$d" "brianmay/debian-source:$d-security" "$d" "linux/amd64" "bullseye"
done
