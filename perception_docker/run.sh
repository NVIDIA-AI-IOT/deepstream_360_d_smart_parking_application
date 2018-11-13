#! /bin/bash
xhost +
nvidia-docker pull nvcr.io/nvidia/deepstream_360d:3.0-18.11
nvidia-docker run --rm -it -v /tmp/.X11-unix:/tmp/.X11-unix -v $(pwd)/videos/:/root/DeepStream360d_Release/samples/streams/360d_streams -e DISPLAY=$DISPLAY -w /root nvcr.io/nvidia/deepstream_360d:3.0-18.11 
