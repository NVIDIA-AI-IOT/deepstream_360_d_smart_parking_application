package com.nvidia.ds.stream

import math._
import com.nvidia.ds.util.Coordinate
import java.sql.Timestamp
import com.nvidia.ds.util.Message


 
 
/**
 * trajectory class, based on local coordinates, Euclidean space
 */

case class Trajectory(
  id:String,  
  start:   Timestamp,
  end:     Timestamp,
  records: List[Message]) {

  /**
   * trajectory based on local coordinates, Euclidean space
   */
  val trajectory = records.map(x => x.`object`.coordinate)
  def trajectoryLen = trajectory.length

  val head = trajectory.head
  val last = trajectory.last

  /**
   * smoothen trajectory based on local coordinates, Euclidean space
   */
  def smoothTrajectory = {

    if (trajectoryLen < 100) {

      trajectory
    } else {

      val t = trajectory.sliding(5).map { l =>

        Coordinate(
          l.map(c => c.x).sum / l.length,
          l.map(c => c.y).sum / l.length,
          l.map(c => c.z).sum / l.length)

      }

      trajectory.head +: t.toList :+ trajectory.last

    }

  }

  def smoothTrajectoryLen = smoothTrajectory.length

  /**
   * approximate distance computed based on movement of object for each point in the trajectory
   */
  def distance = {

    val p1 = trajectory.head
    val p2 = trajectory.last

    if (smoothTrajectory.length < 2) {
      0
    } else smoothTrajectory.sliding(2).map(x => euclideanDistance(x(0), x(1))).sum

  }

  /**
   * kms / hour
   */
  def speed = {

    val t = (end.getTime - start.getTime) / 1000 //seconds

    if (t == 0) {
      t
    } else
      distance * 3.6 / t
  }

  /**
   * straight line distance between to start and end of trajectory
   */
  def linearDistance = {

    val p1 = smoothTrajectory.head
    val p2 = smoothTrajectory.last

    sqrt(pow(p1.x - p2.x, 2) + pow(p1.y - p2.y, 2))

  }
  
  /**
   * length of the trajectory in seconds
   */
  def timeInterval = {
    (end.getTime - start.getTime)/1000.0
  }

  /**
   * function to compute euclidean distance between two points
   */
  private def euclideanDistance(p1: Coordinate, p2: Coordinate) = {

    sqrt(pow(p1.x - p2.x, 2) + pow(p1.y - p2.y, 2))

  }
  
  
  override def toString() = {
     f" moving at $speed%4.2f km/hr, covered $distance%4.2f meters in $timeInterval%4.2f seconds,  id = $id"
  }

}
