package com.nvidia.ds.util

object Playback extends App {

  val appName = getClass.getCanonicalName
  @transient val sys = System.getProperty("os.name")



  val usage = """
    Usage: mvn exec:java -Dexec.mainClass=com.nvidia.ds.util.Playback -Dexec.args = KAFKA_BROKER_IP_ADDRESS:PORT  [--input-file inputFile]  [--topic-name topic]
  """

  if (args.length == 0) println(usage)
  val arglist = args.toList
  type OptionMap = Map[String, Any]

  def nextOption(map: OptionMap, list: List[String]): OptionMap = {
    def isSwitch(s: String) = (s(0) == '-')
    list match {
      case Nil => map
      case "--input-file" :: value :: tail =>
        nextOption(map ++ Map("input-file" -> value.trim()), tail)
      case "--topic-name" :: value :: tail =>
        nextOption(map ++ Map("topic-name" -> value.trim()), tail)
      case string :: opt2 :: tail if isSwitch(opt2) =>
        nextOption(map ++ Map("broker-url" -> string), list.tail)
      case string :: Nil => nextOption(map ++ Map("broker-url" -> string), list.tail)
      case option :: tail =>
        println("Unknown option " + option)
        System.exit(1); Map()
    }
  }
  val options = nextOption(Map(), arglist)
  println(usage)
  println(options)

  val inputFile = if (options.isDefinedAt("input-file")) options("input-file").toString() else "data/demo-1.json"
  val topicName = if (options.isDefinedAt("topic-name")) options("topic-name").toString() else "metromind-start"

  val data = Util.readData(inputFile).toList.sortBy(x => x.timestamp.getTime)

  val config = Util.readConfig("/local-config.txt")

  val brokers = options("broker-url").toString()

  val producer = new KProducer(brokers)

  val (newlat, newlon) = (37.371160038718216, -123.9717545322192)
  val (oldlat, oldlon) = (37.3498233, -121.9675349)

  val (latOffset, lonOffet) = (newlat - oldlat, newlon - oldlon)

  var tt = data(0).timestamp.getTime
  data.foreach { x =>

    val m = if (x.event.`type` == "parked" || x.event.`type` == "empty") {
      val p = x.place.parkingSpot
      val id = if (p.id contains "PS") p.id else p.level + "-PS-" + p.id
      val p_ = p.copy(id = id)

      val place = x.place.copy(parkingSpot = p_)

      x.copy(place = place)

    } else x

    println(x.timestamp + " " + m.event.`type` + " " + m.`object`.vehicle.license + " " + m.place.parkingSpot + " " + m.sensor)

    val json = Util.jsonString(m)
    val partition = math.abs(m.event.`type`.hashCode() % 8)

    val d = m.timestamp.getTime - tt
    Thread.sleep(d)
    tt = m.timestamp.getTime
    producer.send(topicName, partition, m.sensor.id, json)

  }

  producer.close

}