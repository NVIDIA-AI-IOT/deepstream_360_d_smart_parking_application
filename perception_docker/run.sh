#! /bin/bash
DOCKERURL=nvcr.io/nvidia/deepstream_360d:3.0-18.11
xhost +
nvidia-docker pull $DOCKERURL 
nvidia-docker run --rm -it -v /tmp/.X11-unix:/tmp/.X11-unix -v $(pwd)/videos/:/root/DeepStream360d_Release/samples/streams/360d_streams -e DISPLAY=$DISPLAY -w /root $DOCKERURL 
