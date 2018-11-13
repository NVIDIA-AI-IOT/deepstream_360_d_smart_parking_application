package com.nvidia.ds.stream

import com.nvidia.ds.util._
import java.net.InetAddress
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.streaming.Trigger
import org.apache.spark.sql.types.StructType
import org.apache.spark.sql.types.IntegerType
import org.apache.spark.sql.types.ArrayType
import org.apache.spark.sql.types.DoubleType
import org.apache.spark.sql.functions._
import java.text.SimpleDateFormat
import scala.collection.mutable.Queue




/**
 * post perception Event Stream processor,
 * the deepstream perception layer generated the events like entry, exit, moving, parked, empty
 * with respect to Vehicle, the events generated are processed in real time
 * 
 * USED for load test only
 */
object StreamProcessorLoadTest {

  /**
   * operation system information
   */
  @transient val sys = System.getProperty("os.name")

  /**
   * env & prefix information is used for checkpoint directory path
   */
  val env = "docker/"
  val prefix = if (sys.startsWith("Mac")) "" else "/tmp/data/"

  /**
   * checkpoint locations
   */
  val checkpoint_events = if (sys.startsWith("Mac")) "checkpoint-events" else s"${prefix}${env}checkpoint/events"

  /**
   * application name
   */
  val appName = getClass.getCanonicalName

  /**
   * logger
   */
  @transient lazy val log = org.apache.log4j.LogManager.getLogger(getClass.getCanonicalName)

  def main(args: Array[String]) {

    /**
     * application configuration
     */
    val config = if (sys.startsWith("Mac"))
      Util.readConfig("/local-config.txt")
    else
      Util.readConfig("/docker-config.txt")

    

    /**
     * init kafka broker and topic
     */

    val kafkaBrokers = config("kafka-brokers")
    val kafkaTopic = config("topic")

    /**
     * init state management module
     */
    val stateMgmt = new StateMgmt(config)

    /**
     * get or create sparkSession
     */
    val spark = if (sys.startsWith("Mac")) {
      SparkSession
        .builder
        .appName(appName)
        .master("local[8]")
        .getOrCreate()
    } else {
      SparkSession
        .builder
        .appName(appName)
        .getOrCreate()
    }

    import spark.implicits._

    /**
     * setup spark configuration
     */
    spark.conf.set("spark.sql.shuffle.partitions", 8)
    spark.conf.set("spark.sql.streaming.metricsEnabled", "true")

   

    /**
     * initialize kafka sink
     */
    val kafkasink = KafkaSink(config)
    log.info("Kafka Sink Intialized")

    /**
     * user defined function to fix invalid JSON
     * change / modify code if needed
     */
    val cleanValue = udf {
      (value: String) =>
        {
          if (value.contains("\"used\" : \"1\",")) {
            log.info("invalid schema")
            value.replace("\"used\" : \"1\",", "")
          } else value
        }

    }

    /**
     * user defined function to change input data
     * change / modify code if needed
     */
    val replace = udf((videoPath: String) =>
      if (videoPath == null) ""
      else videoPath.replace("http://metrovideodev", "https://smartgarage.metromind.net/smartvideo"))

    /**
     * read event stream from Kafka
     */
    val events = spark.readStream
      .format("kafka")
      .option("kafka.bootstrap.servers", kafkaBrokers)
      .option("subscribe", kafkaTopic)
      .option("startingOffsets", "latest")
      .option("failOnDataLoss", false)
      .load()
      .selectExpr( /**"timestamp",**/ "CAST(key AS STRING)", "CAST(value AS STRING)")
      .select($"key", cleanValue($"value").alias("value"))

    /**
     * schema to convert JSON string into a StructType
     */
    val schema = UtilSpark.mesageSchema(spark)

    /**
     * transform event stream from JSON string into a StructType
     */
    val traffic = events.select(from_json($"value", schema).alias("json"))
      .select("json.*")
      .withColumn("timestamp", $"@timestamp")
      .withColumn("videoPath", replace($"videoPath"))

    /**
     * filter entry, exit events
     */
    val entryExit = traffic.filter($"event.type" === "entry" || $"event.type" === "exit")
      .as[Message]

    /**
     * filter all moving events, i.e. parked, moving, entry, exit
     */
    val parkedMoving = traffic.filter($"event.type" =!= "reset")
      .as[Message]

   

   

   

  
     //write encrypted events
    val passThroughEventsQuery = parkedMoving.writeStream
      .outputMode("Update")
      .option("truncate", "false")
      .option("checkpointLocation", checkpoint_events)
      .foreach(kafkasink.passThroughEventsWriter)
      .queryName("encryptedEventsQuery")
    //.start()  

    /**
     * start each of the streaming query
     */
  
   
     passThroughEventsQuery.start() 
  

   

    /**
     * Wait until any of the queries on the associated SQLContext has terminated
     */
    spark.streams.awaitAnyTermination()

    spark.stop()

  }

}

  
  
  
  