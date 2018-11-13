package com.nvidia.ds.util

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.types.StructType
import org.apache.spark.sql.types.DoubleType
import org.apache.spark.sql.types.ArrayType

object UtilSpark {
  
  
  def uuid = java.util.UUID.randomUUID.toString
  
  
/**
 * schema to convert JSON into Message object
 */
  def mesageSchema(spark: SparkSession) = {

    import spark.implicits._

    val location = new StructType()
      .add($"lat".double)
      .add($"lon".double)
      .add($"alt".double)

    val coordinate = new StructType()
      .add($"x".double)
      .add($"y".double)
      .add($"z".double)

    val vehicleSchema = new StructType()
      .add($"type".string)
      .add($"license".string)
      .add($"licenseState".string)
      .add($"color".string)
      .add($"confidence".float)
      .add($"model".string)
      .add($"make".string)

    val event = new StructType()
      .add($"id".string)
      .add($"type".string)

      .add($"source".string)
      .add($"email".string)

    val bbox = new StructType()
      .add($"topleftx".double)
      .add($"toplefty".double)
      .add($"bottomrightx".double)
      .add($"bottomrighty".double)

    val analyticsModule = new StructType()
      .add($"id".string)
      .add($"description".string)
      //.add($"confidence".double)
      .add($"source".string)
      .add($"version".string)

    val sensor = new StructType()
      .add($"id".string)
      .add($"type".string)
      .add("location", location)
      .add($"description".string)
      .add("coordinate", coordinate)

    val entrance = new StructType()
      .add($"name".string)
      .add($"lane".string)
      .add($"level".string)
      .add("coordinate", coordinate)

    val parkingSpot = new StructType()
      .add($"id".string)
      .add($"type".string)
      .add($"level".string)
      .add("coordinate", coordinate)

    val aisle = new StructType()
      .add($"id".string)
      .add($"name".string)
      .add($"level".string)
      .add("coordinate", coordinate)

    val place = new StructType()
      .add($"id".string)
      .add($"name".string)
      .add($"type".string)
      .add("location", location)
      .add("entrance", entrance)
      .add("parkingSpot", parkingSpot)
      .add("aisle", aisle)

    val obj = new StructType()
      .add($"id".string)
      .add("vehicle", vehicleSchema)
      .add("bbox", bbox)
      .add("signature", ArrayType(DoubleType, false))
      .add($"speed".double)
      .add($"direction".double)
      .add($"orientation".double)
      .add("location", location)
      .add("coordinate", coordinate)

    val message = new StructType()
      .add($"messageid".string)
      .add($"mdsversion".string)
      .add($"@timestamp".timestamp)
      .add($"used".int)
      .add("place", place)
      .add("sensor", sensor)
      .add("analyticsModule", analyticsModule)
      .add("object", obj)
      .add("event", event)
      .add($"videoPath".string)

    message

  }

}