package com.nvidia.ds.stream

import org.apache.spark.unsafe.types.CalendarInterval

import com.nvidia.ds.util.VehicleState
import com.nvidia.ds.util.Message
import com.nvidia.ds.util.Util
import java.sql.Timestamp
import magellan.PolyLine
import magellan.Point

/**
 * manages state of vehicles, for multiple use cases
 */

class StateMgmt(config: Map[String, String]) extends Serializable {

  @transient lazy val log = org.apache.log4j.LogManager.getLogger(getClass.getCanonicalName)

  val cal = CalendarInterval.fromString("interval " + config("understay"))

  val interval = cal.milliseconds()

  log.info("understay interval set to " + interval)

  import org.apache.spark.sql.streaming.{ GroupStateTimeout, OutputMode, GroupState }

  
  /**
   * maintain state of car entry/exit, if the car stays for a short period of time,
   *  it generates anomaly event
   */
  def understayAnomaly(
    vehicleId: String,
    inputs:    Iterator[Message],
    oldState:  GroupState[VehicleState]): VehicleState = {

    if (oldState.hasTimedOut) {

      //log.info("state time out : " + oldState.get.activity)

      val s = oldState.get
      s.activity = "timeout"
      s.anomaly = false
      oldState.remove

      s

    } else {

      var state: VehicleState = if (oldState.exists) oldState.get else VehicleState(
        vehicleId,
        "none",
        null,
        null)
      // we simply specify an old date that we can compare against and
      // immediately update based on the values in our data

      for (input <- inputs) {
        if (input.event.`type` == "entry") {
          state.activity = input.event.`type`
          state.start = input.timestamp
          state.end = input.timestamp
          state.anomaly = false
          state.previous = Some(input)
          oldState.update(state)
          oldState.setTimeoutDuration(interval)
        } else if (input.event.`type` == "exit" && state.activity == "entry") {

          //log.info("time diff : " + (input.timestamp.getTime - state.start.getTime))
          if (input.timestamp.after(state.start) && (input.timestamp.getTime - state.start.getTime < interval)) {
            state.end = input.timestamp
            state.anomaly = true
            state.exitVideoPath = input.videoPath

            state.activity = "exit"
          }
          oldState.update(state)
          oldState.setTimeoutDuration(5000)
        }
        //exit only nothing to do
      }
      state

    }
  }

  
  /**
   * car stopped anomaly
   */
  
   def stalledCarAnomaly(
    vehicleId: String,
    inputs:    Iterator[Message],
    oldState:  GroupState[VehicleState]): VehicleState = {

    val THRESHOLD = 4 // in meters
    val INTERVAL = 20 // in seconds

    val sortedInput = inputs.toList.sortBy(x => x.timestamp.getTime)

    def bbox(m: List[Message]) = {
      val i = m.toList.sortBy(x => x.timestamp.getTime)
      val points = i.map(x => x.`object`.coordinate).map(p => Point(p.x, p.y))
      val pointsWithIndex = points.zipWithIndex.map(x => x._2 -> x._1)
      val polyLine = PolyLine(pointsWithIndex.map(x => x._1).toArray, pointsWithIndex.map(x => x._2).toArray)
      val bb = polyLine.boundingBox
      bb
    }
    def hasMoved(m: List[Message]) = {
      val bb = bbox(m)
      //log.info(bb)
      (bb.xmax - bb.xmin > THRESHOLD || bb.ymax - bb.ymin > THRESHOLD)
    }

    if (oldState.hasTimedOut) {

      //log.info("should not come here")
      //log.info("state time out : " + oldState.get.vehicleId + " "+ oldState.get.activity)
      oldState.get.activity = "timeout"
      oldState.get.anomaly = false
      val x = oldState.get
      oldState.remove()
      x

    } else if (!oldState.exists) {

      /**
       * if the vehicle is not moving, create a new state and update
       */

      if (hasMoved(sortedInput)) {
        //do nothing

        val state: VehicleState = VehicleState(
          vehicleId,
          "none",
          null,
          null) //dummy state

        state

      } else {

        //vehicle not moving

        val i = sortedInput

        val interval = if (i.length <= 1) 0.0 else (i.last.timestamp.getTime - i.head.timestamp.getTime).toDouble / 1000

        //check anomaly or not
        val anomaly = if (interval >= INTERVAL) true else false
        
        
        //this decides which video path to keep
        //println("new state " + sortedInput.map(x => x.event.`type`).toSet)
        val isEntry = sortedInput.exists(x => x.event.`type` == "entry")
        val exitVideoPath = if(isEntry) "" else i.last.videoPath
        

        val state = VehicleState(
          vehicleId,
          "car parked in aisle",
          i.head.timestamp,
          i.last.timestamp,
          Some(i.head),
          Some(i.last),
          anomaly,
          exitVideoPath)

          
        oldState.update(state)
        //no activity for 5 minutes
        oldState.setTimeoutDuration(300000)
        
        //if(anomaly) log.info("not moving " + vehicleId + " interval " + interval)

        state
      }

    } else {

      /**
       * state exist, check the vehicle has moved since the last state
       */

      
      
      var state: VehicleState = VehicleState(
        vehicleId,
        "none",
        null,
        null) //dummy state
      // we simply specify an old date that we can compare against and
      // immediately update based on the values in our data

      //last time same event was reported should be less than 5 minutes
      val timeDiff = (sortedInput.head.timestamp.getTime - oldState.get.previousL.get.timestamp.getTime).toDouble / 1000

      
      //more than 5 minutes  of no activity
      if (timeDiff > 300) {
        //remove the stale state
        log.info("stale state " + oldState.get)
        oldState.remove()

      } else {

        //draw a polyline, and see if the vehicle has moved in the last 1 minutes
        val m = oldState.get.previous.get +: sortedInput

        val i = m //.toList.sortBy(x => x.timestamp.getTime)
        val points = i.map(x => x.`object`.coordinate).map(p => Point(p.x, p.y))
        val pointsWithIndex = points.zipWithIndex.map(x => x._2 -> x._1)
        val polyLine = PolyLine(pointsWithIndex.map(x => x._1).toArray, pointsWithIndex.map(x => x._2).toArray)
        val bb = polyLine.boundingBox

        //neither moved in x or y in the time interval

        //println(i.mkString("--"))
        val interval = if (i.length <= 1) 0.0 else (i.last.timestamp.getTime - i.head.timestamp.getTime).toDouble / 1000

        //log.info("state exists " +vehicleId +" "+ interval)
        
        if (interval >= INTERVAL && bb.xmax - bb.xmin < THRESHOLD && bb.ymax - bb.ymin < THRESHOLD) {

          //log.info("car parked in aisle " + interval +" seconds")

          //log.info(s"car  $vehicleId travelled ${bb.xmax - bb.xmin} ${bb.ymax - bb.ymin} in " + interval +" seconds")

          
          //this decides which video path to keep
        //println("old state " + sortedInput.map(x => x.event.`type`).toSet)
        
        val isEntry = sortedInput.exists(x => x.event.`type` == "entry")
        //check the exit videopath set earlier
        val previousExitVideoPath=oldState.get.exitVideoPath
        
        //if previous sequence has a entry or current sequence has a entry
        val exitVideoPath = if(previousExitVideoPath =="" || isEntry) "" else i.last.videoPath
          
          state = VehicleState(
            vehicleId,
            "car parked in aisle",
            i.head.timestamp,
            i.last.timestamp,
            Some(i.head),
            Some(i.last),
            true,
            exitVideoPath)

          oldState.update(state)

          //no activity for 5 minutes
          oldState.setTimeoutDuration(300000)
          
          //log.info("anomaly state " + oldState.get)

        }

      }

      state

    }

  }
  
  
 
/**
 * filter shorter trajectory
 */
  def filterTrajectory(
    vehicleId: String,
    inputs:    Iterator[Message],
    oldState:  GroupState[Trajectory]): List[Message] = {

    val THRESHOLD = 3 //seconds

    if (oldState.hasTimedOut) {

      
      val x = oldState.get
      log.info(s"9 state time out :  ${x}")

      

      oldState.remove()

      List[Message]()

    } else if (!oldState.exists) {

      
       
      val messages = inputs.toList.sortBy(x => x.timestamp.getTime)

      val newT = Trajectory(
        vehicleId,
        messages.head.timestamp,
        messages.last.timestamp,
        messages)

      oldState.update(newT)
      oldState.setTimeoutDuration("5 seconds")

      if (validTrajectory(newT)) {
        log.info("1 new state with valid trajectory  : " + newT)
        newT.records
      } else {
        log.info("2 new state with invalid trajectory  : " + newT)
        List[Message]()
      }

    } else { // old state exist

      val messages = inputs.toList.sortBy(x => x.timestamp.getTime)

      val newT = Trajectory(
        vehicleId,
        messages.head.timestamp,
        messages.last.timestamp,
        messages)

      lazy val validstate = validState(oldState.get.end, newT.start)

      if (!validstate) { // old state not valid
        
        log.info("3 stale state   : " + vehicleId)

        oldState.remove()
        oldState.update(newT)
        oldState.setTimeoutDuration("5 seconds")

        if (validTrajectory(newT)) {
          log.info("4 stale state with valid trajectory  : " + newT)
          newT.records
        } else {
          log.info("5 stale state with invalid trajectory  : " + newT)
          //do not send the new Message till it crosses the threshold
          List[Message]()
        }

      } else { // old state is valid

        val oldT = oldState.get

        val updatedT = Trajectory(
          vehicleId,
          oldState.get.start,
          newT.end,
          oldT.records ++ newT.records)

        val messsages = if (validTrajectory(oldT)) {
          //send only delta as the previous trajectory data was already sent
          log.info("6 valid old state with new trajectory  : " + updatedT)
          newT.records
        } else {
          if (validTrajectory(updatedT)) {
            //if the updated trajectory is valid
            log.info("7 valid updated trajectory  : " + updatedT)
            updatedT.records
          } else {
            //do not send the new Message till it crosses the threshold
            log.info("8 invalid updated trajectory  : " + updatedT)
            List[Message]()
          }
        }

        oldState.update(updatedT)
        oldState.setTimeoutDuration("5 seconds")

        messsages
      }

    }
  }

  /**
   * if the end of trajectory t1 is way ahead of start of trajectory t2 start, the state is stale or invalid
   */
  def validState(t1_end: Timestamp, t2_start: Timestamp, interval: Long = 6000) = {

    val valid = t2_start.getTime - t1_end.getTime < interval

    if (!valid) println(s"invalid $t1_end  $t2_start")

    valid
  }

  def validTrajectory(t: Trajectory) = {
    val THRESHOLD = 3 //seconds
    t.timeInterval > THRESHOLD

  }

}