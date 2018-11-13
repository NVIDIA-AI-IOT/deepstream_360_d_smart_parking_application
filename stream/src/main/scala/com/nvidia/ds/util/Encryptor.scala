package com.nvidia.ds.util

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.util.Base64
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

/**
 * 
 *
 * Encryption / Decryption utility
 */
object Encryptor {

  //do not use this keys for production
  val key = "1234567890abcdef1234567890abcdef"; // 256 bit key
  val initVector = "1234567890abcdef"; // 16 bytes IV

  val iv = new IvParameterSpec(initVector.getBytes("UTF-8"));

  val skeySpec = new SecretKeySpec(key.getBytes("UTF-8"), "AES");
  
  //val skeySpec1 = generateKey(key)
  //val skeySpec2 = generateKey(key)

  //AES/CBC/PKCS5Padding or AES/CBC/PKCS5PADDING
  val eCipher = Cipher.getInstance("AES/CBC/PKCS5PADDING");
  eCipher.init(Cipher.ENCRYPT_MODE, skeySpec, iv);

  val dCipher = Cipher.getInstance("AES/CBC/PKCS5PADDING");
  dCipher.init(Cipher.DECRYPT_MODE, skeySpec, iv);

  /**
   * returns base 64 encoded string after encryption
   */
  def encrypt(plainText: String) = this.synchronized{
    Base64.getEncoder.encodeToString(eCipher.doFinal(plainText.getBytes("UTF-8")))
  
  }

  /**
   * '
   * returns the de-crypted text
   */
  def decrypt(encryptedText: String) = this.synchronized{
    val decoded = Base64.getDecoder.decode(encryptedText.getBytes("UTF-8"))

    new String(dCipher.doFinal(decoded))

  }

  def generateKey(passphrase: String) = {
    val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA1");
    val spec = new PBEKeySpec(passphrase.toCharArray(), Integer.toHexString(100).getBytes, 1000, 256);
    val key = new SecretKeySpec(factory.generateSecret(spec).getEncoded(), "AES");
    key;

  }

  def main(args: Array[String]) {

    for (i <- 1 to 1000000) {
      val e = Encryptor.encrypt("MTH7ARA")
      println("encrypted : " + e)

      val d = Encryptor.decrypt(e)
      println("decrypted : " + d + " " + d.length())
    }

  }

}