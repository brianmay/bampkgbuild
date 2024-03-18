#!/bin/sh
set -ex

build() {
    src="$1"
    dst="$2"
    dist="$3"
    platform="$4"
    security="$5"
    experimental="$6"

    docker pull --platform "$platform" "$src"
    docker build --force-rm --platform "$platform" --build-arg IMAGE="$src" --build-arg DISTRIBUTION="$dist" --build-arg SECURITY="$security" --build-arg EXPERIMENTAL="$experimental" -t "$dst" .
}

for d in experimental; do
    build "docker.io/i386/debian:sid" "brianmay/debian-i386:$d" "sid" "linux/i386" "none" "libc6"
    build "docker.io/debian:sid" "brianmay/debian-amd64:$d" "sid" "linux/amd64" "none" "libc6"
    build "docker.io/debian:sid" "brianmay/debian-source:$d" "sid" "linux/amd64" "none" "libc6"
done

for d in sid; do
    build "docker.io/i386/debian:$d" "brianmay/debian-i386:$d" "$d" "linux/i386" "none"
    build "docker.io/debian:$d" "brianmay/debian-amd64:$d" "$d" "linux/amd64" "none"
    build "docker.io/debian:$d" "brianmay/debian-source:$d" "$d" "linux/amd64" "none"
done

for d in bullseye; do
    build "i386/debian:$d" "brianmay/debian-i386:$d" "$d" "linux/i386" "bullseye"
    build "i386/debian:$d" "brianmay/debian-i386:$d-security" "$d" "linux/i386" "bullseye"

    build "debian:$d" "brianmay/debian-amd64:$d" "$d" "linux/amd64" "bullseye"
    build "debian:$d" "brianmay/debian-amd64:$d-security" "$d" "linux/amd64" "bullseye"

    build "debian:$d" "brianmay/debian-source:$d" "$d" "linux/amd64" "bullseye"
    build "debian:$d" "brianmay/debian-source:$d-security" "$d" "linux/amd64" "bullseye"
done

for d in bookworm; do
    build "i386/debian:$d" "brianmay/debian-i386:$d" "$d" "linux/i386" "bullseye"
    build "i386/debian:$d" "brianmay/debian-i386:$d-security" "$d" "linux/i386" "bullseye"

    build "debian:$d" "brianmay/debian-amd64:$d" "$d" "linux/amd64" "bullseye"
    build "debian:$d" "brianmay/debian-amd64:$d-security" "$d" "linux/amd64" "bullseye"

    build "debian:$d" "brianmay/debian-source:$d" "$d" "linux/amd64" "bullseye"
    build "debian:$d" "brianmay/debian-source:$d-security" "$d" "linux/amd64" "bullseye"
done

