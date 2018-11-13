

package com.nvidia.ds.util

import java.time.ZoneOffset
import java.sql.Timestamp
import java.time.LocalDateTime
import scala.util.Random
import com.google.gson.GsonBuilder
import java.text.SimpleDateFormat
import scala.concurrent.Future
import scala.concurrent.ExecutionContext.Implicits.global
import scala.concurrent.Await
import scala.concurrent.duration.Duration

import scala.collection.mutable.Map

/**
 * 
 * 
 * Defines all the case classes related to the JSON schema
 */

object TestMessage {

  
 
  private[this] val r = new Random(26L)

  def rDouble = BigDecimal(100 * r.nextDouble()).setScale(2, BigDecimal.RoundingMode.FLOOR).toDouble

 
  def localToGMT() = {

    val utc = LocalDateTime.now(ZoneOffset.UTC)
    Timestamp.valueOf(utc)

  }
  def uuid = java.util.UUID.randomUUID.toString

 

 

 


}


case class Message(
  messageid:       String             = TestMessage.uuid,
  mdsversion:      String             = "1.0",
  timestamp:       java.sql.Timestamp = TestMessage.localToGMT(),
  used:            Integer            = null,
  place:           Place              = new Place,
  sensor:          Sensor             = new Sensor,
  analyticsModule: AnalyticsModule    = new AnalyticsModule,
  `object`:        Object             = new Object,
  event:           Event              = new Event,
  videoPath:       String             = "")

case class ParkingSpotDelta(
  garageid:        String,
  level:           String,
  sensorType:      String,
  spotid:          String,
  messageid:       String             = TestMessage.uuid,
  mdsversion:      String             = "1.0",
  timestamp:       java.sql.Timestamp = TestMessage.localToGMT(),
  used:            Integer            = null,
  place:           Place              = new Place,
  sensor:          Sensor             = new Sensor,
  analyticsModule: AnalyticsModule    = new AnalyticsModule,
  `object`:        Object             = new Object,
  event:           Event              = new Event,
  videoPath:       String             = "")

case class Event(
  id:     String = "event-id",
  `type`: String = null,

  source: String = null,
  email:  String = null)

case class Vehicle(
  `type`:       String = "sedan",
  make:         String = "Bugatti",
  model:        String = "M",
  color:        String = "blue",
  confidence:   Double = TestMessage.rDouble,
  license:      String = null, //TestMessage.license,
  licenseState: String = "CA")

case class Bbox(
  topleftx:     Double = 0.0,
  toplefty:     Double = 0.0,
  bottomrightx: Double = 1000.0,
  bottomrighty: Double = 1000.0)

case class Object(
  id:          String        = "object-id",
  vehicle:     Vehicle       = new Vehicle,
  bbox:        Bbox          = new Bbox,
  signature:   Array[Double] = Array(0.2, 0.3, 0.4),
  speed:       Double        = 0.0,
  direction:   Double        = 0.0,
  orientation: Double        = 0.0,
  location:    Location      = new Location,
  coordinate:  Coordinate    = new Coordinate)

case class AnalyticsModule(
  id:          String = "AM-id",
  description: String = "Vehicle Detection and License Plate Recognition",
  //confidence:  Double = TestMessage.rDouble,
  source:  String = "",
  version: String = "1.0")

case class Location(
  lat: Double = TestMessage.rDouble,
  lon: Double = TestMessage.rDouble,
  alt: Double = TestMessage.rDouble)

case class Coordinate(
  x: Double = 1,
  y: Double = 2,
  z: Double = 3)

case class Sensor(
  id:          String     = "",
  `type`:      String     = "Camera",
  location:    Location   = new Location,
  description: String     = "",
  coordinate:  Coordinate = new Coordinate)

case class Entrance(
  name:       String     = "",
  lane:       String     = "lane1",
  level:      String     = "P1",
  coordinate: Coordinate = new Coordinate)

case class ParkingSpot(
  id:         String     = "spot-id",
  `type`:     String     = "LV",
  level:      String     = "P1",
  coordinate: Coordinate = new Coordinate)

case class Aisle(
  id:         String     = "grid-id",
  name:       String     = "Left Lane",
  level:      String     = "P1",
  coordinate: Coordinate = new Coordinate)

case class Place(
  id:          String      = "place-id",
  name:        String      = "",
  `type`:      String      = "building/garage",
  location:    Location    = new Location,
  entrance:    Entrance    = null,
  parkingSpot: ParkingSpot = null,
  aisle:       Aisle       = null)




object AnomalyEventType extends Enumeration {
  val Overstay, Understay, Blacklist, Whitelist, UnexpectedStopping = Value
}

case class Anomaly(
  messageid:       String          = TestMessage.uuid,
  mdsversion:      String          = "1.0",
  timestamp:       Timestamp,
  startTimestamp:    Timestamp       = null,
  endTimestamp:    Timestamp       = null,
  place:           Place,
  analyticsModule: AnalyticsModule,
  `object`:        Object,
  event:           Event,
  entryVideo:      String,
  exitVideo:       String,
  aisleVideo:      String)

case class VehicleState(
  vehicleId:         String,
  var activity:      String,
  var start:         java.sql.Timestamp,
  var end:           java.sql.Timestamp,
  var previous:      Option[Message]    = None,
  var previousL:      Option[Message]    = None,
  var anomaly:       Boolean            = false,
  var exitVideoPath: String             = "")

case class FlowRate(
  id:        String,
  timestamp: Timestamp,
  `type`:    String,
  count:     BigInt)

