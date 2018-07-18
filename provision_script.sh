#!/usr/bin/env bash

apt-get -y update

# This is just to make sure you have the latest Ubuntu Xenial
apt-get -y upgrade

apt-get install -y python3 \
    python3-pip \
    python3-requests \
    python3-numpy \
    python3-pyproj \
    python3-gdal \
    python3-shapely \
    python3-rtree \
    python3-pil \
    python3-pil.imagetk \
    p7zip-full

apt-get -y update
