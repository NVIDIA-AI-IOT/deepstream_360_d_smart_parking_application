package com.nvidia.ds.util

import org.scalatest.Matchers
import org.scalatest.FlatSpec

class KProducerSpec extends FlatSpec with Matchers {

  "KProducer" should "send data" in {

    val config = Util.readConfig("/local-config.txt")

    val brokers = config("kafka-brokers")

    val producer = new KProducer(brokers)

    //sent reset before start
    {
      val p = Place()
      val e = Event("1.0", "reset")

      val resetM = Message(TestMessage.uuid, "1.0", Util.localToGMT(), 0, p, null, null, null, event = e, videoPath = null)

      val json = Util.jsonString(resetM)
      //producer.send("metromind-start", 0, "reset", json)

    }

  }

}