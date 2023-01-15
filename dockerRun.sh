#!/usr/bin/bash

# CREATE THE REQUIRED LOCAL DIRS IF NOT THERE TO HAVE ACCESS TO THE GENERATED CONTENT FROM THE OUTSIDE
mkdir -p Masks
mkdir -p Orthophotos
mkdir -p OSM_data
mkdir -p Elevation_data
mkdir -p Geotiffs
mkdir -p Tiles
mkdir -p tmp

# RUN THE CONTAINER WITH(OUT) UI (THE WAYLAND WAY!)
# shellcheck disable=SC2068
podman run --interactive --tty --rm \
   \
   --cpus 4 \
   \
   --volume XAUTHORITY:"$XAUTHORITY":ro \
   --volume /tmp/.X11-unix:/tmp/.X11-unix:ro \
   --userns keep-id   \
   --env    "DISPLAY" \
   --security-opt label=type:container_runtime_t \
   \
   --volume "$(pwd)/Ortho4XP.cfg:/app/Ortho4XP.cfg:rw" \
   --volume "$(pwd)/.last_gui_params.txt:/app/.last_gui_params.txt:rw" \
   \
   --volume "$(pwd)/OSM_data:/app/OSM_data" \
   --volume "$(pwd)/Masks:/app/Masks" \
   --volume "$(pwd)/Orthophotos:/app/Orthophotos" \
   --volume "$(pwd)/Elevation_data:/app/Elevation_data" \
   --volume "$(pwd)/Geotiffs:/app/Geotiffs" \
   --volume "$(pwd)/Tiles:/app/Tiles" \
   --volume "$(pwd)/tmp:/app/tmp" \
   o4xp \
   $@
