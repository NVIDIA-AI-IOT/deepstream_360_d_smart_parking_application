package com.nvidia.ds.stream

import com.datastax.spark.connector.cql.CassandraConnector
import org.apache.spark.sql.Row
import com.nvidia.ds.util.Util
import com.google.gson.GsonBuilder
import com.datastax.driver.core.SimpleStatement
import com.datastax.driver.core.ConsistencyLevel
import java.text.SimpleDateFormat
import java.sql.Timestamp
import com.nvidia.ds.util.Message
import com.nvidia.ds.util.ParkingSpotDelta
import com.nvidia.ds.util.KProducer
import com.nvidia.ds.util.VehicleState
import com.nvidia.ds.util.FlowRate

/**
 * @author Sujit Biswas
 */

/**
 * Cassandra sink, this also updates the counter in kafka topic,
 * this is temporary hack, till we have the Kafka Connect In place
 */
object CassandraSink {

  def apply(connector: CassandraConnector, config: Map[String, String]) = new CassandraSink(connector, config)
}

class CassandraSink(connector: CassandraConnector, config: Map[String, String]) extends Serializable {

  @transient lazy val log = org.apache.log4j.LogManager.getLogger(getClass.getCanonicalName)

  val brokers = config("kafka-brokers")
  val cassandraNamespace = config("cassandra-namespace")

  

  
 
  private def processParkingSpotAndAisle(value: Message) = {

    
    val encrpytedObject = Util.encryptLicense(value.`object`) 
    
    val t = value.copy(`object` = encrpytedObject)
    
    //TODO encrypt license if present

    //println(t.event.`type` + " " + t.place.aisle)

    if ((t.event.`type` == "parked") || (t.event.`type` == "empty")) {

      val stmt = s"INSERT INTO ${cassandraNamespace}.parkingSpot JSON ? ;"

      val stmt_delta = s"INSERT INTO ${cassandraNamespace}.ParkingSpotDelta JSON ? ;"
      
      val stmt_playback = s"INSERT INTO ${cassandraNamespace}.ParkingSpotPlayback JSON ? ;"

      val stmt_state = s"UPDATE ${cassandraNamespace}.ParkingSpotState SET messageid=?, mdsversion=?,timestamp=?,place=fromJSON(?)," +
        s"sensor=fromJSON(?),analyticsModule=fromJSON(?),object=fromJSON(?)," +
        s"event=fromJSON(?),videoPath=? where garageid=? AND level=? AND spotid=?"

      val utc = Util.to_utc(t.timestamp)

      if (t.place.parkingSpot == null) {
        log.warn("Invalid message / place " + t.place)
      } else {

        //old parkingSpot state
        val m = Message(t.place.parkingSpot.id, t.mdsversion, utc, place = t.place, sensor = t.sensor, `object` = t.`object`, event = t.event, videoPath = t.videoPath)
        val parkingSpotJson = Util.jsonString(m).replace("@timestamp", "timestamp")

        //parking Spot Delta PRIMARY KEY ((garageid, level,sensorType), timestamp, spotid)
        val parkingSpotDelta = ParkingSpotDelta(
          t.place.name, t.place.parkingSpot.level,t.sensor.`type`, t.place.parkingSpot.id,
          t.messageid, t.mdsversion, utc, place = t.place, sensor = t.sensor,
          `object` = t.`object`, event = t.event, videoPath = t.videoPath)

        val parkingSpotDeltaJson = Util.jsonString(parkingSpotDelta).replace("@timestamp", "timestamp")

        connector.withSessionDo { session =>
          //session.execute(stmt, parkingSpotJson)
          session.execute(stmt_delta, parkingSpotDeltaJson)
          session.execute(stmt_playback, parkingSpotDeltaJson)
          session.execute(stmt_state, t.messageid,
            t.mdsversion,
            utc,
            Util.jsonString(t.place),
            Util.jsonString(t.sensor),
            Util.jsonString(t.analyticsModule),
            Util.jsonString(t.`object`),
            Util.jsonString(t.event),
            t.videoPath,
            t.place.name,
            t.place.parkingSpot.level,
            t.place.parkingSpot.id)

        }
      }

    } else {

      // all moving is with respect to a location
      //moving, stopped, entry, exit

      //log.info(t.timestamp +" "+ t.`object`.vehicle.license)
      val stmt = s"INSERT INTO ${cassandraNamespace}.Aisle JSON ? ;"

      val utc = Util.to_utc(t.timestamp)
      
      val level = if(t.place.entrance != null) t.place.entrance.level else t.place.aisle.level

      val m = Message(t.place.name+"-"+level, t.mdsversion, utc, place = t.place, sensor = t.sensor, `object` = t.`object`, event = t.event, videoPath = t.videoPath)

      val j = Util.jsonString(m).replace("@timestamp", "timestamp")

      connector.withSessionDo { session =>
        session.execute(stmt, j)
      }

    }

  }

 
 

 

  import org.apache.spark.sql.ForeachWriter
 

  val parkedMovingWriter = new ForeachWriter[Message] {

    override def open(partitionId: Long, version: Long) = {
      true
    }
    override def process(value: Message) = {
      processParkingSpotAndAisle(value)
    }

    override def close(errorOrNull: Throwable) = {

      //println(errorOrNull)

    }

  }

  val flowRateWriter = new ForeachWriter[FlowRate] {

    override def open(partitionId: Long, version: Long) = {
      true
    }
    override def process(value: FlowRate) = {

      //UPDATE flowrate  SET exit = 5  WHERE id = 'test' and timestamp = '2018-02-27 21:33:17.098Z' ;

      val timestamp = Util.to_utc(value.timestamp)

      val formattedDate = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").format(timestamp);

      val sql = s"UPDATE ${cassandraNamespace}.flowrate  SET ${value.`type`} = ${value.count}  WHERE id = '${value.id}' and timestamp = '$formattedDate' ; "

      //println(sql)

      connector.withSessionDo { session =>
        session.execute(sql)

      }

    }

    override def close(errorOrNull: Throwable) = {

      //println(errorOrNull)

    }

  }
  
  
  val trajectoryFilterWriter = new ForeachWriter[List[Message]] {

    override def open(partitionId: Long, version: Long) = {
      true
    }
    override def process(value: List[Message]) = {

      value.foreach{ x =>
        //println(x)
        
        /**
         * enable this when consuming from a reid-module
         */
        //processParkingSpotAndAisle(x)
      }

    }
    override def close(errorOrNull: Throwable) = {
      
    }
  }
  
  

}

