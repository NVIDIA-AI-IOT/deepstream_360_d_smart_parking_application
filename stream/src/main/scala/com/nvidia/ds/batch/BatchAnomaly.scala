package com.nvidia.ds.batch

import org.apache.spark.sql.SparkSession
import com.nvidia.ds.util._
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import java.time.ZoneOffset
import java.sql.Timestamp
import java.time.LocalDateTime
import scala.reflect.api.materializeTypeTag

/**
 * example batch anomaly, note this takes the date from Kafka and does the batch processing,
 *  in practice this not recommended, data should be read from HDFS or S3
 */

object BatchAnomaly {

  def main(args: Array[String]) {

    @transient val sys = System.getProperty("os.name")

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
    val anomalyKafkaTopic = config("anomalyTopic")

    val spark = if (sys.startsWith("Mac")) {
      SparkSession
        .builder
        .appName("Metromind-BatchAnomaly")
        .master("local[8]")
        .getOrCreate()
    } else {
      SparkSession
        .builder
        .appName("Metromind-BatchAnomaly")
        .getOrCreate()
    }

    /**
     * spark.sqlContext
     */
    val sqlContext = spark.sqlContext
    import sqlContext.implicits._

    /**
     * user define function to convert local time to UTC
     */
    def localToGMT() = {
      val utc = LocalDateTime.now(ZoneOffset.UTC)
      Timestamp.valueOf(utc)
    }

    /**
     * user define function to diff in hours for two timestamp
     */
    val timeDiffInHours = udf {

      (t1: Timestamp, t2: Timestamp) =>
        {

          val next = if (t2 == null) {
            localToGMT()
          } else t2

          //println("t1 = "+ t1 +" , next = " + next)
          -(t1.getTime - next.getTime) * 1.0 / (1000 * 60 * 60)

        }

    }

    /**
     * udf to generate overstay anomaly event
     */
    val typeOfAnomaly = AnomalyEventType.Overstay.toString()
    val eventUdf = udf {
      () =>
        {
          Event(Util.uuid, typeOfAnomaly)
        }
    }

    /**
     * udf for analytics module
     */
    val analyticModuleUdf = udf {

      (diff: Double) =>
        {

          val d = BigDecimal(diff).setScale(2, BigDecimal.RoundingMode.HALF_UP).toDouble

          val a = AnalyticsModule("1", typeOfAnomaly + ", " + d + " hrs", "MetromindAM-" + typeOfAnomaly)

          a
        }

    }

    /**
     * udf to replace the videoPath
     */
    val replace = udf((videoPath: String) => if (videoPath == null) "" else videoPath.replace("http://metrovideodev", "https://smartgarage.metromind.net/smartvideo"))

    /**
     * read event stream from Kafka, this is for demo purpose only, in production read from HDFS or S3
     */
    val events = spark.read
      .format("kafka")
      .option("kafka.bootstrap.servers", kafkaBrokers)
      .option("subscribe", kafkaTopic)
      .option("startingOffsets", "earliest")
      .option("failOnDataLoss", false)
      .load()
      .selectExpr( /**"timestamp",**/ "CAST(key AS STRING)", "CAST(value AS STRING)")

    /**
     * check for last 24 hours data
     */
    val xHoursAgo = Util.timeXhoursAgo(24)

    /**
     *  schema, used to map JSON to Message object
     */
    val schema = UtilSpark.mesageSchema(spark)

    /**
     * events data related to parked and empty
     */
    val traffic = events.select(from_json($"value", schema)
      .alias("json"))
      .select("json.*").
      select("messageid", "mdsversion", "place", "object", "@timestamp", "event", "videoPath")
      //.filter($"@timestamp" > xHoursAgo)
      .filter($"event.type" === "parked" || $"event.type" === "empty")

    traffic.show(false)
    println("\n total count " + traffic.count())

    /**
     * WindowSpec with the partitioning
     */
    val wSpec1 = Window.partitionBy("place.parkingspot.id", "place.parkingspot.level").orderBy("@timestamp")

    
    /**
     * computes how long is car is parked in a parking spot, and raise an anomaly
     */
    val anomaly = traffic
      .withColumn("nextEvent", lead(traffic("event"), 1).over(wSpec1))
      .withColumn("endTimestamp", lead(traffic("@timestamp"), 1).over(wSpec1))
      .withColumn("exitVideo", lead(traffic("videoPath"), 1).over(wSpec1))
      .filter($"event.type" === "parked" && ($"nextEvent.type" === "empty" || $"endTimestamp" === null))
      .withColumn("timeDiff", timeDiffInHours($"@timestamp", $"endTimestamp"))

      /**
       * for demo purpose only, if a car has stayed more than 5 minutes, raise an overstay anomaly
       * normally this anomaly should be raised if the car has stayed more than 24 hours
       */
      .filter($"timeDiff" > 5.0 / 60)
      .withColumn("analyticsModule", analyticModuleUdf($"timeDiff"))
      .withColumn("event", eventUdf())
      .withColumn("aisleVideo", lit(""))
      .withColumn("startTimestamp", $"@timestamp")
      .withColumn("videoPath", replace($"videoPath"))
      .withColumnRenamed("videoPath", "entryVideo")
      .withColumn("timestamp", $"endTimestamp")
      .drop($"timeDiff")
      .drop($"nextEvent")
      .drop($"@timestamp")

    println(anomaly.count)
    anomaly.show(false)

 
    /**
     * convert to Anomaly dataset
     */
    val aDs = anomaly.as[Anomaly]

    /**
     * persist the message to kafka
     */
    aDs
      .map { a =>
        //encrypt before you sent
        val o = Util.encryptLicense(a.`object`)
        a.copy(`object` = o)
      }
      .map(a => (a.event.`type`, Util.jsonString(a))).toDF("key", "value")
      .write
      .format("kafka")
      .option("kafka.bootstrap.servers", kafkaBrokers)
      .option("topic", anomalyKafkaTopic)
      .save()

    aDs.printSchema

    if (sys.startsWith("Mac")) spark.stop()

  }

}