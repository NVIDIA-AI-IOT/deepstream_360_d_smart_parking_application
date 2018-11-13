
# Streaming Architecture

![Streaming Architecture](readme-images/pipeline.png?raw=true "Streaming")   

**Kafka** is used as the message broker in the reference implementation. Processing between module are decoupled using Kafka when needed.
 
The stream processing is done using **Apache Spark**. We use a custom python module for “multi-camera-tracking”. The key streaming modules are as below.
    
a) The **multi-camera-tracking** is explained in the track project, primarily it is responsible for deduplicating detection of the same object seen by multiple cameras and tracking the object across cameras.

b) The **preprocessing** module is responsible of validation of every JSON messages that is being send from the perception layer, it maps each JSON message to Strongly typed domain object.

c) The **anomaly detection** module maintain state of each and every vehicle/object. As the trajectory of each vehicle is maintained over time, it is very easy to compute information like speed of vehicle, how long a car has stayed in a particular location, is the car stalled in unexpected location?

d) **Flowrate** module is used to understand the traffic patterns, flow rate, this involves micro-batching of data over sliding window
 
This project implements the last 3 module, multi-camera-tracking is done in python.
    
The data is persisted in Cassandra and ElasticSearch. Cassandra is used to maintain the state of the parking garage at a given point of time. The state of the parking Garage comprises of parking spot occupancy, car movement in the aisle, car entry and exit. The application can show the current state of the garage, it also enables playback of event from a given point of time. All data events, anomalies are indexed in ElasticSearch for search, timeseries analytics and dashboard.
 
![Batch Architecture](readme-images/batch.png?raw=true "Batch")   
The **Batch** processing is done based on the accumulated data over a period of time. The data ideally should be stored on distributed file system like HDFS or S3, for the Reference application in the docker container as we are not using cloud deployment, and the data is read from the kafka topic itself, the entire data for a given topic is read to do batch processing on it. The output of the batch processing is stored in the persistent store and is consumed by the API.

## Anomaly Detection, Stateful stream processing
 
The implementation is based on Apache Spark structured streaming, a fault tolerant streaming engine. As maintaining trajectories required advanced stateful operations, it uses *mapGroupsWithState* operation. The API allow maintaining user-defined per-group state between triggers for a steaming dataframe. The timeout is set to cleanup any state which has not seen any activity for a configurable period of time. Important to note that the reference implementation use processing time and is based on the clock time, hence it could be affected by changes in the system clock, example clock skew.
 
 
Trajectories for each and every vehicle is maintained during the period of time the vehicle is seen in the aisle area. Location of car within aisle or parking spot is determined by ROI (region of interest). The perception layer generates the information with respect to location of car. Maintaining trajectories of vehicle gives us the ability to compute many information like speed, time of stay and whether a vehicle is stalled in particular location. The trajectories are cleaned up if no events are seen with respect to a vehicle for configurable period of time. The trajectories are formed based on “moving” events. If a vehicle gets parked after moving through the aisle, the corresponding trajectory will be cleaned up after configurable period of time.
 
![Anomaly Detection](readme-images/anomaly.png?raw=true "Anomaly")   
 
# Gettting Started

### Compile and Install the project

        mvn clean install -Pjar-with-dependencies

    this will genearte the required jar, note the location of new jars created

        [INFO] --- maven-jar-plugin:2.4:jar (default-jar) @ stream-360 ---
        [INFO] Building jar: /Users/home/git/stream-360/target/stream-360-1.0.jar
        [INFO] 
        [INFO] --- maven-assembly-plugin:2.5.5:single (make-assembly) @ stream-360 ---
        [INFO] Building jar: /Users/home/git/stream-360/target/stream-360-1.0-jar-with-dependencies.jar


### Start Spark Streaming job, 
This job does following
    
    a) manages the state of parking garage  
    b) detects car "understay" anomaly  
    c) detects car "stalled" anomaly    
    d) computes flowrate


    Install Apache Spark, or use a existing cluster, if spark-master is running in docker container  

        docker exec -it spark-master /bin/bash

    the docker container picks up the jar file from spark/data

        ./bin/spark-submit  --class com.nvidia.ds.stream.StreamProcessor --master spark://master:7077 --executor-memory 4G --total-executor-cores 4 /tmp/data/stream-360-1.0-jar-with-dependencies.jar


    
    
### Start Spark batch job, 
This detects "overstay" anomaly

        
        ./bin/spark-submit  --class com.nvidia.ds.batch.BatchAnomaly --master spark://master:7077 --executor-memory 4G --total-executor-cores 4 /tmp/data/stream-360-1.0-jar-with-dependencies.jar