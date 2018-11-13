package com.nvidia.ds.util

import java.sql.Timestamp
import java.text.SimpleDateFormat
import java.time.LocalDateTime
import java.time.ZoneOffset
import java.util.Calendar
import java.util.TimeZone

import org.json4s.DefaultFormats

import com.google.gson.GsonBuilder


/**
 * util class
 */

object Util extends Serializable {
  
  
  /**
   * default date format
   */
  def defaultFormat =
    new DefaultFormats {
      override def dateFormatter = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    }

  
  /**
   * GsonBuilder
   */
  def gson = new GsonBuilder()
    .setDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    .create()

  /**  
   *   converts an object to Json string
   */
  def jsonString(e: Any) = gson.toJson(e).replace("timestamp", "@timestamp")

 
  /**
   * read configuration
   */
  def readConfig(path: String) = {
    val f = scala.io.Source.fromInputStream(getClass.getResourceAsStream(path))
    val lines = f.getLines().map { x =>
      {
        val reg = x.split("=", 2)

        (reg(0).trim(), reg(1).trim())
      }
    }
    lines.toList.filterNot(p => p._1 == "" || p._2 == "").map(x => x._1 -> x._2).toMap
  }

  /**
   * use to read set, backlist or whitelist license plate
   */
  def readSet(path: String) = {
    val f = scala.io.Source.fromInputStream(getClass.getResourceAsStream(path))
    val lines = f.getLines().map { x =>
      //println(x)
      x.trim

    }
    lines.toList.toSet
  }

  
  /**
   * safe string to int
   */
  def safeStringToInt(str: String): Option[Int] = {
    import scala.util.control.Exception._
    catching(classOf[NumberFormatException]) opt str.toInt
  }



   
  val config = readConfig("/local-config.txt")

  
  /**
   * convert current local time to UTC
   */
  def localToGMT() = {
   val utc = LocalDateTime.now(ZoneOffset.UTC)
   Timestamp.valueOf(utc)
  }

  /**
   * convert input timestamp to UTC
   */
  def to_utc(t: Timestamp) = {
    new Timestamp(t.getTime() - Calendar.getInstance().getTimeZone().getOffset(t.getTime()));
  }

  
  /**
   * compute time X hours ago
   */
  def timeXhoursAgo(hours: Long) = {

    val utc = LocalDateTime.now(ZoneOffset.UTC)

    val xhours = utc.minusHours(hours)

    Timestamp.valueOf(xhours)

  }

  
  /**
   * convert string to UTC time
   */
  def to_utc_from_String(d: String) = {

    val dateFormatter = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")

    dateFormatter.setTimeZone(TimeZone.getTimeZone("UTC"))

    val date = dateFormatter.parse(d)

    val ts = new Timestamp(date.getTime());

    Util.to_utc(ts)

  }

  
  /**
   * read JSON data to list to Message Object
   */
  def readData(path: String = "data/traffic.txt") = {
    val f = scala.io.Source.fromFile(path)

    //test
    import org.json4s._
    import org.json4s.native.JsonMethods._

    implicit val formats = new DefaultFormats {
      override def dateFormatter = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    }

    val records = f.getLines().map { x =>

      val p = parse(x.replace("@timestamp", "timestamp"))

      val e = p.extract[Message]

      e

    }

    records

  }

  val enableEncrption = false
  
  /**
   * encrypt license plate
   */
  def encryptLicense(obj: Object) = {

    if (enableEncrption) {

      val l = obj.vehicle.license

      if (l == null || l.trim() == "") {
        obj
      } else {
        val ll = Encryptor.encrypt(l)
        val v = obj.vehicle.copy(license = ll)
        val o = obj.copy(vehicle = v)

        o

      }
    } else obj

  }

  def uuid = java.util.UUID.randomUUID.toString

 

  
 
}

