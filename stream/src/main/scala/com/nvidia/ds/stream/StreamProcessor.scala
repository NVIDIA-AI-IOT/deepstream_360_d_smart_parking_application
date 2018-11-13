package com.nvidia.ds.stream

import com.nvidia.ds.util._
import java.net.InetAddress
import org.apache.spark.sql.SparkSession
import com.datastax.spark.connector.cql.CassandraConnector
import org.apache.spark.sql.streaming.Trigger
import org.apache.spark.sql.types.StructType
import org.apache.spark.sql.types.IntegerType
import org.apache.spark.sql.types.ArrayType
import org.apache.spark.sql.types.DoubleType
import org.apache.spark.sql.functions._
import java.text.SimpleDateFormat
import scala.collection.mutable.Queue
import org.apache.spark.sql.streaming.GroupStateTimeout

/**
 * post perception Event Stream processor,
 * the deepstream perception layer generated the events like entry, exit, moving, parked, empty
 * with respect to Vehicle, the events generated are processed in real time
 */
object StreamProcessor {

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
  val checkpoint_parked_moving = if (sys.startsWith("Mac")) "checkpoint-parked-moving" else s"${prefix}${env}checkpoint/parked-moving"
  val checkpoint_whitelist_blacklist = if (sys.startsWith("Mac")) "checkpoint-whitelist-blacklist" else s"${prefix}${env}checkpoint/whilelist-blacklist"
  val checkpoint_understay = if (sys.startsWith("Mac")) "checkpoint-understay" else s"${prefix}${env}checkpoint/understay"
  val checkpoint_stalled = if (sys.startsWith("Mac")) "checkpoint-stalled" else s"${prefix}${env}checkpoint/stalled"
  val checkpoint_flowrate = if (sys.startsWith("Mac")) "checkpoint-flowrate" else s"${prefix}${env}checkpoint/flowrate"
  val checkpoint_trajectory = if (sys.startsWith("Mac")) "checkpoint-trajectory" else s"${prefix}${env}checkpoint/trajectory"

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
     * init cassandra hosts
     */
    val cassandraHosts = config("cassandra-hosts")
      .split(",")
      .map(x => if (x == "localhost") InetAddress.getLoopbackAddress else InetAddress.getByName(x))
      .toSet

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
     * initialize casssandra sink
     */
    val connector = CassandraConnector.apply(cassandraHosts)
    val sink = CassandraSink(connector, config)
    log.info("Cassandra-Kafka Sink Intialized")

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

    /**
     *  write parking and aisle updates to cassandra
     */
    val parkedMovingQuery = parkedMoving.writeStream
      .outputMode("Update")
      .option("truncate", "false")
      .option("checkpointLocation", checkpoint_parked_moving)
      .foreach(sink.parkedMovingWriter)
      .queryName("parkedMovingQuery")

    /**
     * whitelist and blacklist anomaly
     */
    val whitelistBlacklsitAnommalyQuery = entryExit.writeStream
      .outputMode("Update")
      .option("truncate", "false")
      .option("checkpointLocation", checkpoint_whitelist_blacklist)
      .foreach(kafkasink.blackAndWhiteListAnomalyWriter)
      .queryName("whitelistBlacklsitAnommalyQuery")

    /**
     * detect car understay, if a car enter and exit the garage within a short time
     */
    val understayAnomalyQuery = entryExit.filter(x => x.event.`type` != "reset")
      .filter { x =>
        val l = x.`object`.vehicle.license.trim().toUpperCase()
        !(l == "UNKNOWN" || l == "" || l == "DGDGCOM")
      }
      .groupByKey(x => x.`object`.vehicle.license.trim().toUpperCase())
      .mapGroupsWithState(GroupStateTimeout.ProcessingTimeTimeout())(stateMgmt.understayAnomaly)
      .filter(x => x.anomaly)
      .writeStream
      .trigger(Trigger.ProcessingTime("60 seconds"))
      .option("checkpointLocation", checkpoint_understay)
      .foreach(kafkasink.understayWriter)
      .outputMode("update")
      .queryName("understayAnomalyQuery")

    /**
     * computes traffic flow rate per hour
     */
    val trafficFlowRate = entryExit
      .withWatermark("timestamp", "1 seconds").
      groupBy(
        window($"timestamp", "60 seconds", "10 seconds"), $"event.type", $"place.name").count()
      .select($"name".alias("id"), $"window.end".alias("timestamp"), $"type", ($"count" * 60).alias("count")) //extrapolate to per hour
      .as[FlowRate]
      .writeStream
      .outputMode("Append")
      .option("checkpointLocation", checkpoint_flowrate)
      .foreach(sink.flowRateWriter)
      .queryName("trafficFlowRate")

    /**
     * car stopped in aisle anomaly
     */
    val stalledCarAnomalyQuery = parkedMoving
      .filter(x => x.event.`type` != "parked")
      .filter(x => x.event.`type` != "empty")
      .filter(x => x.`object`.vehicle != null && x.`object`.vehicle.license != null)
      .filter { x =>
        val l = x.`object`.vehicle.license.trim().toUpperCase()

        !(l == "UNKNOWN" || l == "" || l == "DGDGCOM")
      }
      .groupByKey(x => x.`object`.vehicle.license.trim().toUpperCase())
      .mapGroupsWithState(GroupStateTimeout.ProcessingTimeTimeout())(stateMgmt.stalledCarAnomaly)
      .filter(x => x.anomaly)
      .writeStream
      .trigger(Trigger.ProcessingTime("30 seconds"))
      .queryName("stalledCarAnomalyQuery")
      .option("checkpointLocation", checkpoint_stalled)

      .foreach(kafkasink.stalledCarWriter)
      .outputMode("update")

    /**
     * filter out spurious trajectories, this may happen due to false detection in cameras
     */
    val trajectoryFilterQuery = parkedMoving

      .withWatermark("timestamp", "1 seconds")
      .groupByKey(x => x.sensor.id + " #-# " + x.`object`.id)
      .mapGroupsWithState(GroupStateTimeout.ProcessingTimeTimeout())(stateMgmt.filterTrajectory)
      .filter(x => !x.isEmpty)
      .writeStream
      .outputMode("Update")
      .option("truncate", "false")
      .trigger(Trigger.ProcessingTime("3 seconds"))
      .option("checkpointLocation", checkpoint_trajectory)
      .foreach(sink.trajectoryFilterWriter)
      .queryName("trajectoryFilterQuery")
    //.start()

    /**
     * start each of the streaming query
     */
    parkedMovingQuery.start()
    understayAnomalyQuery.start()
    trafficFlowRate.start()
    stalledCarAnomalyQuery.start()

    //trajectoryQuery.start()

    /**
     * optional enable if needed
     */
    //whitelistBlacklsitAnommalyQuery.start()

    /**
     * Wait until any of the queries on the associated SQLContext has terminated
     */
    spark.streams.awaitAnyTermination()

    spark.stop()

  }

}

  
  
  
  