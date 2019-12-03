## Setup Instructions

This document describes the steps involved to run the 360d app using the docker image.


1. Assuming that the application has been cloned from this repository

       $ git clone https://github.com/NVIDIA-AI-IOT/deepstream_360_d_smart_parking_application.git
   use the following command to change the current directory.

       $ cd ./deepstream_360_d_smart_parking_application/perception_docker 

   Create a directory named 'videos' and change the current directory by executing the command 
   
       $ mkdir videos && cd videos
       
   Download videos from https://nvidia.app.box.com/s/ezzw0js1ti555vbn3swsggvepcsh3x7e and place it in the 'videos' directory.

2. Login to Nvidia container registry (nvcr.io)

       $ docker login nvcr.io

     Enter the username as `$oauthtoken` and copy your NGC APIKey as the password.
     Note that the login is sticky and does not have to be repeated every time.
     Refer to https://docs.nvidia.com/ngc/ngc-getting-started-guide/index.html for more information. 

3. Execute the `run.sh` command (sudo maybe required depending on how docker is configured on your system) by going to perception_docker
   directory

4. When the container starts up, edit config file to set broker url (if required). To do so first install an editor (eg: nano)

       $ apt-get update
    
       $ apt-get install nano

5. Enable logging (optional)

       $ DeepStream360d_Release/sources/tools/nvds_logger/setup_nvds_logger.sh 

    **Note:** the log severity level can be edited in the setup script if desired
    -- set to 7 if logging of entire messages is required

6. Run the 360d app<br/>
Eg:

       $ deepstream-360d-app -c DeepStream360d_Release/samples/configs/deepstream-360d-app/source10_gpu0.txt 


   **Note:** if there is an error that looks like below, then the broker address is not valid.

       ERROR from nvmsgbroker: Could not configure supporting library.
       Debug info: gstnvmsgbroker.c(325): gst_nvmsgbroker_start (): /GstPipeline:pipeline/GstNvMsgBroker:nvmsgbroker:
       unable to connect to broker library
