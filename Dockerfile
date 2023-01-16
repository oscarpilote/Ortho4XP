FROM python:3.9-alpine3.17 AS compile-image

WORKDIR /

# INSTALL BUILD DEPENDENCIES
RUN apk add make automake gcc g++ subversion python3-dev git proj proj-util proj-dev geos-dev tk

# INSTALL/BUILD PYTHON PACKAGES/WHEELS
# WORKAROUND: numpy==1.23.5  --> CODE REQUIREMENT
# WORKAROUND: shapely==1.8.5 --> CODE REQUIREMENT
RUN python -m venv /opt/venv                                  && \
    source /opt/venv/bin/activate                             && \
    pip install --upgrade pip                                 && \
    pip install requests numpy Pillow pyproj shapely rtree tk && \
    pip install --force-reinstall -v "numpy==1.23.5"          && \
    pip install --force-reinstall -v "shapely==1.8.5"

FROM python:3.9-alpine3.17 AS target-image
# COPY PYTHON PACKAGES
COPY --from=compile-image /opt/venv /opt/venv

# COPY ORTHO4XP INTO THE IMAGE
COPY ./ /app/

# INSTALL ORTHO4XP REQUIRED DEPENDENCIES
# libc6-compat: https://stackoverflow.com/a/66974607
RUN apk add proj geos tk fontconfig ttf-dejavu libc6-compat

# FINALIZE
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
ENTRYPOINT ["/app/Ortho4XP_v130.py"]
