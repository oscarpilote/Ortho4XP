FROM python:3.7-slim

ENV DEBIAN_FRONTEND="noninteractive"
ENV LANG="en_US.UTF-8"
ENV LC_ALL="C.UTF-8"
ENV LANGUAGE="en_US.UTF-8"

RUN apt-get -q update \
 && apt-get install --no-install-recommends -yq \
        build-essential \
        libz-dev \
        libjpeg62-turbo-dev \
        unzip \
 && apt-get autoremove -yq \
 && apt-get autoclean \
 && rm -rf /tmp/* \
           /var/lib/apt/lists/*

RUN mkdir /tmp/wheels \
 && pip3 wheel Pillow-SIMD \
      -w /tmp/wheels

COPY Utils/Triangle4XP.c /tmp/triangle/
RUN gcc -O2 -pipe -msse3 \
      -o /tmp/triangle/Triangle4XP \
      /tmp/triangle/Triangle4XP.c \
      -lm \
 && strip /tmp/triangle/Triangle4XP

ADD http://dev.x-plane.com/download/tools/xptools_lin_15-3.zip /tmp/
RUN unzip /tmp/xptools_lin_15-3.zip tools/DSFTool -d /tmp/xptools

FROM python:3.7-slim

ENV DEBIAN_FRONTEND="noninteractive"
ENV LANG="en_US.UTF-8"
ENV LC_ALL="C.UTF-8"
ENV LANGUAGE="en_US.UTF-8"

RUN apt-get -q update \
 && apt-get install --no-install-recommends -yq \
      gdal-bin \
      libspatialindex5 \
      libjpeg62-turbo \
      zlib1g \
      p7zip-full \
      libnvtt-bin \
      wget \
      python3-pyproj \
      python3-numpy \
      python3-shapely \
      python3-rtree \
      python3-requests \
      python3-gdal \
      libtk8.6 \
      python3-pil \
      python3-pil.imagetk \
 && apt-get autoremove -yq \
 && apt-get autoclean \
 && rm -rf /tmp/* \
           /var/lib/apt/lists/*

RUN mkdir /tmp/wheels
COPY --from=0 /tmp/wheels/* /tmp/wheels
RUN pip3 install /tmp/wheels/*  \
 && rm -r /tmp/wheels

COPY docker/build_ortho.sh /ortho
RUN chmod +x /ortho

COPY Extents/         /ortho4xp/Extents/
COPY Filters          /ortho4xp/Filters/
COPY Licence/         /ortho4xp/Licence/
COPY Providers/       /ortho4xp/Providers/
COPY src/             /ortho4xp/src/
COPY Utils/Earth/     /ortho4xp/Utils/Earth/
COPY Utils/*.gif  \
     Utils/water* Utils/*.png \
     /ortho4xp/Utils/

COPY Ortho4XP.cfg-sample /ortho4xp/Ortho4XP.cfg
COPY Ortho4XP_v130.py README.md /ortho4xp/

COPY --from=0   \
     /tmp/triangle/Triangle4XP  \
     /tmp/xptools/tools/DSFTool \
     /ortho4xp/Utils/


RUN mkdir /build

VOLUME /scenery
VOLUME /build
VOLUME /overlay

ENV PYTHONPATH=/usr/lib/python3/dist-packages:/ortho4xp/src

ENV MAX_CONVERT_SLOTS="4" \
    HIGHRES_AIRPORTS=ICAO

WORKDIR /ortho4xp
ENTRYPOINT [ "/ortho" ]
