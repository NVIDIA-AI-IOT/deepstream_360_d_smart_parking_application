package com.nvidia.ds.util

import org.apache.kafka.clients.producer.KafkaProducer
import com.google.gson.GsonBuilder
import java.util.Properties
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.clients.admin.AdminClient
import org.apache.kafka.clients.admin.ListTopicsOptions

/**
 * wrapper around kafka producer with default properties
 */
class KProducer(val brokers: String) extends Serializable {

  /**
   * init the kafka producer properties
   */
  val props = new Properties();
  props.put("bootstrap.servers", brokers);
  props.put("retries", "0");
  props.put("linger.ms", "1");
  props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
  props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");

  /**
   * validate connection
   */
  try {
    // ...
    val adminClient = AdminClient.create(props)
    adminClient.listTopics(new ListTopicsOptions().timeoutMs(500).listInternal(true)).names().get

  } catch {
    case e: Exception => {
      println(f"Invalid connection URL $brokers \n")
      
      e.printStackTrace()
      
      System.exit(-1)
    }
  }

  /**
   * create kafka producer
   */
  val p = new KafkaProducer[String, String](props)

  /**
   * used for testing
   */
  private[util] def send(e: Message) = {

    val topic = "metromind-start"

    val gson = new GsonBuilder()
      .setDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
      .create()

    val json = gson.toJson(e).replace("timestamp", "@timestamp")

    val key = if (e.event.`type` == "reset") "reset" else e.sensor.id
    //should be based on number of DS box
    val partition = key.hashCode() % 8

    p.send(new ProducerRecord[String, String](topic, partition, key, json))

  }

  /**
   * send message to a specified topic
   */
  def send(topic: String, partition: Int, key: String, value: String) {
    p.send(new ProducerRecord[String, String](topic, partition, key, value))
  }

  /**
   * close the producer
   */
  def close = p.close()

}