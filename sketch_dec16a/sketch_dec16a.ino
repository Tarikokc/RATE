#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <Wire.h>
#include <SensirionI2cScd4x.h>

const char* ssid      = "iPhone de Tarik";
const char* password  = "TarikArt942003";
const char* serverUrl = "http://172.20.10.3:5000/measure";

#define BME_SDA D6
#define BME_SCL D5
const int PIR_PIN = D2;

SensirionI2cScd4x scd4x;

void setup() {
  Serial.begin(115200);
  delay(1000);
  pinMode(PIR_PIN, INPUT);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nConnecté WiFi : " + WiFi.localIP().toString());

  Wire.begin(BME_SDA, BME_SCL);
  scd4x.begin(Wire, 0x62);
  scd4x.startPeriodicMeasurement();
  Serial.println("SCD40 démarré");
  delay(5000); // 1ère mesure prend 5s
}

void loop() {
  uint16_t co2;
  float temp, hum;
  scd4x.readMeasurement(co2, temp, hum);
  int motion = digitalRead(PIR_PIN);

  Serial.printf("CO2=%d T=%.2f H=%.2f M=%d\n", co2, temp, hum, motion);

  if (WiFi.status() == WL_CONNECTED) {
    String payload = "{";
    payload += "\"sensor\":\"esp8266-1\",";
    payload += "\"co2\":"    + String(co2)        + ",";
    payload += "\"temp\":"   + String(temp, 2)    + ",";
    payload += "\"hum\":"    + String(hum, 2)     + ",";
    payload += "\"motion\":" + String(motion);
    payload += "}";

    WiFiClient client;
    HTTPClient http;
    if (http.begin(client, serverUrl)) {
      http.addHeader("Content-Type", "application/json");
      int code = http.POST(payload);
      Serial.println("HTTP POST: " + String(code));
      http.end();
    }
  }
  delay(5000);
}