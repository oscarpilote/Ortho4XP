FROM ubuntu:resolute

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y python3 python3-pip python3-requests python3-numpy python3-pyproj python3-gdal python3-shapely python3-rtree python3-pil python3-pil.imagetk p7zip-full libnvtt-bin freeglut3-dev gdal-bin python3-scikit-fmm

ENV DISPLAY=:1
WORKDIR /app
COPY . .

CMD ["python3", "Ortho4XP.py"]
