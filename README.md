# DeepStream 3.0 - 360 Degree Smart Parking Application
 
![Architecture](readme-images/architecture.png?raw=true "Architecture")

This document describes the full end to end smart parking application that is available with DeepStream 3.0. The above architecture provides a reference to build distributed and scalable DeepStream applications.

**Note**: The perception server only supports DeepStream 3.0.

## Introduction

The perception capabilities of a DeepStream application can now seamlessly be augmented with data analytics capabilities to build complete solutions, offering rich data dashboards for actionable insights. This bridging of DeepStream’s perception capabilities with data analytics frameworks is particularly useful for applications requiring long term trend analytics, global situational awareness, and forensic analysis. This also allows leveraging major Internet of Things (IOT) services as the infrastructure backbone.

The data analytics backbone is connected to DeepStream applications through a distributed messaging fabric. DeepStream 3.0 offers two new plugins, gstnvmsgconv and gstnvmsgbroker, to transform and connect to various messaging protocols. The protocol supported in this release is Kafka.
 


To build an end to end implementation of the Analytics layer, DeepStream 3.0 uses open source tools and frameworks that can easily be reproduced for deployment on an on-premise server or in the Cloud.
The framework comprises stream and batch processing capabilities. Every component of the Analytics layer, Message Broker, Streaming, NoSQL, and Search Indexer can be horizontally scaled. The streaming analytics pipeline can be used for processes like anomaly detection, alerting, and computation of statistics like traffic flow rate. Batch processing can be used to extract patterns in the data, look for anomalies over a period of time, and build machine learning models. The data is kept in a NoSQL database for state management, e.g. the occupancy of a building, activity in a store, or people movement in a train station. This also provides the capability for forensic analytics, if needed. The data can be indexed for search and time series analytics. Information generated by streaming and batch processing is exposed through a standard API for visualization. The API can be accessed through REST, WebSocket, or messaging, based on the use case. The user interface allows the user to consume all the relevant information.
Deployment is based on an open source technology stack. The modules and technology stack are shown with respect to the Streaming Data pipeline.

## Getting Started

To get started, clone this repository by either clicking the download button on top right corner, or using the command
   
    git clone https://github.com/NVIDIA-AI-IOT/deepstream_360_d_smart_parking_application.git

To run this application, the user needs to start the following docker containers:

1. **[Analytics Server](https://github.com/NVIDIA-AI-IOT/deepstream_360_d_smart_parking_application/tree/master/analytics_server_docker)**: Check the README inside `analytics_server_docker` directory and follow the steps to start the docker containers.
2. **[Perception Server](https://github.com/NVIDIA-AI-IOT/deepstream_360_d_smart_parking_application/tree/master/perception_docker)**: Check the README inside `perception_docker` directory and follow the steps to start the docker container.

Other modules included in this application are as follows:
1. [Apis](https://github.com/NVIDIA-AI-IOT/deepstream_360_d_smart_parking_application/tree/master/apis)
2. [Stream](https://github.com/NVIDIA-AI-IOT/deepstream_360_d_smart_parking_application/tree/master/stream)
3. [Tracker](https://github.com/NVIDIA-AI-IOT/deepstream_360_d_smart_parking_application/tree/master/tracker)
4. [Ui](https://github.com/NVIDIA-AI-IOT/deepstream_360_d_smart_parking_application/tree/master/ui)
