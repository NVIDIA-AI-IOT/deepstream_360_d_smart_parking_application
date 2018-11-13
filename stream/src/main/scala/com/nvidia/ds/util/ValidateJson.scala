package com.nvidia.ds.util

import java.sql.Timestamp

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.udf
import org.apache.spark.sql.streaming.Trigger

import com.github.fge.jackson.JsonLoader
import com.github.fge.jsonschema.main.JsonSchemaFactory

/**
 * validate json messages based on json schema
 */
object ValidateJson {

  @transient val sys = System.getProperty("os.name")

  val appName = getClass.getCanonicalName

  @transient lazy val log = org.apache.log4j.LogManager.getLogger(getClass.getCanonicalName)

  def main(args: Array[String]) {

    val config = if (sys.startsWith("Mac")) Util.readConfig("/local-config.txt") else Util.readConfig("/docker-config.txt")
    val brokers = config("kafka-brokers") //"kafka1.data.nvidiagrid.net:9092" //
    val topic = config("topic")

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

    spark.conf.set("spark.sql.shuffle.partitions", 8)

    import spark.implicits._

    val validateJson = udf {

      (value: String) =>
        {

          import scala.collection.JavaConversions._

          var t = (true, "")

          try {

            val r = ValidateJson.validateJson(value)

            t = (r.isSuccess(), r.iterator().toList.map(x => x.asJson()).mkString("\n"))

          } catch {
            case e: Exception => { t = (false, e.getMessage) }
          }

          t

        }

    }

    /**
     * read event stream
     */
    val events = spark.readStream
      .format("kafka")
      .option("kafka.bootstrap.servers", brokers)
      .option("subscribe", topic)
      .option("startingOffsets", "latest")
      .option("failOnDataLoss", false)
      .load()
      .selectExpr("timestamp", "CAST(key AS STRING)", "CAST(value AS STRING)")
      .select(validateJson($"value").alias("error"), $"value")
      .select($"error.*", $"value")
      .toDF("flag", "message", "value")

    
      /**
       * for now print into console, most appropriate is to put into Elasticsearch to history
       */
      val consoleQuery = events //.select("event","place")//.filter($"event.type" === "moving") //.withColumn("@timestamp", to_utc_timestamp($"timestamp","PST"))

      .filter(!$"flag")
      .writeStream
      .trigger(Trigger.ProcessingTime("60 seconds"))
      .outputMode("Append")
      .format("console")
      .option("truncate", "false")

    consoleQuery.start()

    spark.streams.awaitAnyTermination()

    spark.stop()

  }

  /**
   * json schema factory
   */
  val factory = JsonSchemaFactory.byDefault()
  
  /**
   * json schema-string into json object
   */
  val schemaJ = load("/schema/day2.json")
  
  
  /**
   * json schema object
   */
  val schema = factory.getJsonSchema(schemaJ)

  /**
   * Load one resource from the current package as a {@link JsonNode}
   *
   * @param name name of the resource (<b>MUST</b> start with {@code /}
   * @return a JSON document
   * @throws IOException resource not found
   */

  def load(name: String) = {
    JsonLoader.fromResource(name)
  }

  /**
   * load json string into a json object and validate against the schema
   */
  def validateJson(json: String) = {
    val j = JsonLoader.fromString(json)
    val r = schema.validate(j)
    r
  }

}