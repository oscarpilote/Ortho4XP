FROM ubuntu:18.10

RUN apt-get update -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3 python3-pip python3-requests python3-numpy python3-pyproj python3-gdal \
        python3-shapely python3-rtree python3-pil python3-pil.imagetk p7zip-full libnvtt-bin \
    && mkdir -p /Ortho4XP

COPY . /Ortho4XP/

WORKDIR /Ortho4XP

ENV PYTHONIOENCODING=UTF-8

ENTRYPOINT ["./Ortho4XP_v130.py"]
