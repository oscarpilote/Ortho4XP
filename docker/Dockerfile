FROM python:3.7-slim
RUN apt update              \
 && apt -y install          \
      build-essential       \
      libz-dev              \
      libjpeg62-turbo-dev

RUN mkdir /tmp/wheels       \
 && pip3 wheel Pillow-SIMD \
      -w /tmp/wheels


FROM python:3.7-slim

RUN apt update              \
 && apt -y install          \
      gdal-bin              \
      libspatialindex5      \
      libjpeg62-turbo       \
      zlib1g                \
      p7zip-full            \
      libnvtt-bin           \
      wget

RUN apt install -y          \
      python3-pyproj        \
      python3-numpy         \
      python3-shapely       \
      python3-rtree         \
      python3-requests      \
      python3-gdal

RUN apt install -y          \
      libtk8.6              \
      python3-pil           \
      python3-pil.imagetk

RUN mkdir /tmp/wheels
COPY --from=0 /tmp/wheels/* /tmp/wheels
RUN pip3 install /tmp/wheels/*  \
 && rm -r /tmp/wheels


COPY files/patches/* /tmp/patches/
RUN patch -d /ortho4xp -p1  </tmp/patches/generate_ovl.patch

COPY files/build_ortho.sh /ortho
RUN chmod +x /ortho

RUN mkdir /build

VOLUME /scenery
VOLUME /build
VOLUME /overlay

ENV PYTHONPATH=/usr/lib/python3/dist-packages:/ortho4xp/src
ENV ENABLE_USGS=""

WORKDIR /ortho4xp
ENTRYPOINT [ "/ortho" ]
