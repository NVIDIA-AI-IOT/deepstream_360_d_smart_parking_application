#! /bin/bash
xhost +
nvidia-docker pull   gitlab-master.nvidia.com:5005/deepstreamsdk/release_image/deepstream360_release:cl_25208070
nvidia-docker run --rm -it -v /tmp/.X11-unix:/tmp/.X11-unix -v $(pwd)/videos/:/root/DeepStream360d_Release/samples/streams/360d_streams -e DISPLAY=$DISPLAY -w /root  gitlab-master.nvidia.com:5005/deepstreamsdk/release_image/deepstream360_release:cl_25208070 
