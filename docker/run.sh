#!/bin/bash

# Allow connections to X server
xhost +local:docker

docker run --rm -it \
	-e DISPLAY=$DISPLAY \
	-v /tmp/.X11-unix:/tmp/.X11-unix:rw \
	-v ./scenery:/app/scenery \
	ortho4xp

# Close connection to X server
xhost -local:docker
