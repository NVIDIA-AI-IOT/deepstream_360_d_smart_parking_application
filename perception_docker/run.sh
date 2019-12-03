#! /bin/bash
DOCKERURL=nvcr.io/nvidia/deepstream_360d:4.0.1-19.11
xhost +
docker pull $DOCKERURL 
docker run --gpus all -it --rm -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=$DISPLAY -w /root nvcr.io/nvidia/deepstream_360d:4.0.1-19.11
