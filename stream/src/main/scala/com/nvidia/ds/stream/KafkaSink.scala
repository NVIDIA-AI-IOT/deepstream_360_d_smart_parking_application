package com.nvidia.ds.stream

import scala.math.BigDecimal

import org.apache.spark.sql.ForeachWriter

import com.nvidia.ds.util.AnalyticsModule
import com.nvidia.ds.util.Anomaly
import com.nvidia.ds.util.AnomalyEventType
import com.nvidia.ds.util.Event
import com.nvidia.ds.util.KProducer
import com.nvidia.ds.util.Message
import com.nvidia.ds.util.Util
import com.nvidia.ds.util.VehicleState



/**
 * Kafka sink
 */
object KafkaSink {

  def apply(config: Map[String, String]) = new KafkaSink(config)
}

class KafkaSink(config: Map[String, String]) extends Serializable {

  @transient lazy val log = org.apache.log4j.LogManager.getLogger(getClass.getCanonicalName)

  val brokers = config("kafka-brokers")
  val anomalyTopic = config("anomalyTopic")
  val eventsTopic = config("eventsTopic")
  val topic = config("topic")

  val whitelist = Util.readSet(config("whitelist"))
  val blacklist = Util.readSet(config("blacklist"))

  log.info("kafka brokers: " + brokers)

  private def processBlackAndWhiteListAnomaly(value: Message, producer: KProducer) = {

    val event = value.event.`type`

    if (event == "entry" || event == "exit") { //check anomaly, whitelist or backlist, should refactor into a different stream

      val x = if (whitelist.contains(value.`object`.vehicle.license)) {

        Some(createWhiteBlackListAnomaly(value, AnomalyEventType.Whitelist.toString()))
      } else if (blacklist.contains(value.`object`.vehicle.license)) {
        Some(createWhiteBlackListAnomaly(value, AnomalyEventType.Blacklist.toString()))
      } else {
        None
      }

      if (!x.isEmpty) {
        val a = x.get
        println(a)
        val json = Util.jsonString(a)

        val partition = math.abs(a.event.`type`.hashCode() % 8)
        producer.send(anomalyTopic, partition, "", json)
      }

    }

  }

  private def createWhiteBlackListAnomaly(message: Message, typeOfAnomaly: String) = {

    val entryVideo = if (message.event.`type` == "entry") message.videoPath else ""
    val exitVideo = if (message.event.`type` == "exit") message.videoPath else ""
    val spotVideo = ""

    val e = Event(Util.uuid, typeOfAnomaly)

    val a = AnalyticsModule("1", "this car is " + typeOfAnomaly + "ed", "MetromindAM-" + typeOfAnomaly)

    val utc = Util.to_utc(message.timestamp)

    Anomaly(Util.uuid, "1.0", utc, utc, utc, message.place, a, Util.encryptLicense(message.`object`), e, entryVideo, exitVideo, spotVideo)

  }

  private def createUnderStayAnomaly(value: VehicleState, typeOfAnomaly: String) = {

    val message = value.previous.get
    val entryVideo = if (message.event.`type` == "entry") message.videoPath else ""
    val exitVideo = value.exitVideoPath
    val spotVideo = ""

    val utc = Util.to_utc(message.timestamp)
    val endTime = Util.to_utc(value.end)
    val startTime = Util.to_utc(value.start)

    val diff = (endTime.getTime - utc.getTime).toDouble / 60000

  
  
    val (e, a) =  {

      val d = BigDecimal(diff).setScale(2, BigDecimal.RoundingMode.HALF_UP).toDouble

      Event(Util.uuid, typeOfAnomaly) -> AnalyticsModule("1", s"Short Stay $d minutes", "MetromindAM-" + typeOfAnomaly)

    }

    Anomaly(Util.uuid, "1.0", startTime, startTime, endTime, message.place, a, Util.encryptLicense(message.`object`), e, entryVideo, exitVideo, spotVideo)

  }
  
  
  /**
   * car stalled anomaly
   */
  
   def createStalledCarAnomaly(value: VehicleState, typeOfAnomaly: String) = {

    val message = value.previous.get
    
    val isEntry = (value.exitVideoPath == "")
    val entryVideo = ""//if(isEntry ) message.videoPath else ""
    val exitVideo =  ""//value.exitVideoPath
    val spotVideo = value.exitVideoPath //should use the value.exitVideoPath

    val utc = Util.to_utc(message.timestamp)
    val endTime = Util.to_utc(value.end)
    val startTime = Util.to_utc(value.start)

    val diff = (endTime.getTime - utc.getTime).toDouble / 1000

    val d = BigDecimal(diff).setScale(2, BigDecimal.RoundingMode.HALF_UP).toDouble

    val e = Event(Util.uuid, typeOfAnomaly)

    val a = AnalyticsModule("1", s"Unexpected Stopping $d seconds", "MetromindAM-" + typeOfAnomaly)

    //println(utc +" " + endTime +" "+a)
    //println(utc)

    Anomaly(Util.uuid, "1.0", startTime, startTime,endTime, message.place, a, Util.encryptLicense(message.`object`), e, entryVideo, exitVideo, spotVideo)

  }

  /**
   * to be used if any of the fields contains PII 
   */
  val passThroughEventsWriter = new ForeachWriter[Message] {

    var producer: KProducer = _
    override def open(partitionId: Long, version: Long) = {
      producer = new KProducer(brokers)
      true
    }
    override def process(value: Message) = {

      val t = if (value.event.`type` == "reset") {
        value
      } else {

        val eo = Util.encryptLicense(value.`object`)

        value.copy(`object` = eo)

      }

      val j = Util.jsonString(t)

      /**
       * can randomly distribute / partition for now
       */
      val partition = math.abs(t.hashCode() % 8)
      producer.send(eventsTopic, partition, "", j)

    }
    override def close(errorOrNull: Throwable) = {
      producer.close
    }
  }

  val blackAndWhiteListAnomalyWriter = new ForeachWriter[Message] {

    var producer: KProducer = _
    override def open(partitionId: Long, version: Long) = {
      producer = new KProducer(brokers)
      true
    }
    override def process(value: Message) = {
      processBlackAndWhiteListAnomaly(value, producer)
    }
    override def close(errorOrNull: Throwable) = {
      producer.close
    }
  }

  val understayWriter = new ForeachWriter[VehicleState] {

    var producer: KProducer = _
    override def open(partitionId: Long, version: Long) = {
      producer = new KProducer(brokers)
      true
    }
    override def process(value: VehicleState) = {
      val a = createUnderStayAnomaly(value, AnomalyEventType.Understay.toString())
      val json = Util.jsonString(a)

      val partition = math.abs(a.event.`type`.hashCode() % 8)
      log.info(json)
      producer.send(anomalyTopic, partition, "", json)
    }
    override def close(errorOrNull: Throwable) = {
      producer.close
    }
  }
  
  
   val stalledCarWriter = new ForeachWriter[VehicleState] {

    var producer: KProducer = _
    override def open(partitionId: Long, version: Long) = {
      producer = new KProducer(brokers)
      true
    }
    override def process(value: VehicleState) = {
      val a = createStalledCarAnomaly(value, AnomalyEventType.UnexpectedStopping.toString())
      val json = Util.jsonString(a)

      //println(a.`object`.vehicle.license + " " + a.exitVideo)

      val partition = math.abs(a.event.`type`.hashCode() % 8)
      producer.send(anomalyTopic, partition, "", json)
    }
    override def close(errorOrNull: Throwable) = {
      producer.close
    }
  }
  
  

}

