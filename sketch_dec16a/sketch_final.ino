#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <Wire.h>
#include <SensirionI2cScd4x.h>

const char* ssid         = "iPhone de Tarik";
const char* password     = "TarikArt942003";
const char* serverUrl    = "http://172.20.10.7:5000/api/measures";
const char* heatingUrl   = "http://172.20.10.7:5000/api/heating/sensor-state";

#define BME_SDA D6
#define BME_SCL D5
const int PIR_PIN = D2;

SensirionI2cScd4x scd4x;
String sensorId;
bool sensorOk = false;
float fakeTemp = 16.0;  

bool connectWifi() {
  WiFi.persistent(false);
  WiFi.disconnect(true);
  delay(200);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("WiFi connexion");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500); Serial.print("."); attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nConnecté : " + WiFi.localIP().toString());
    return true;
  }
  Serial.println("\nEchec WiFi");
  return false;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  pinMode(PIR_PIN, INPUT);

  sensorId = "esp8266-" + String(ESP.getChipId(), HEX);
  Serial.println("Sensor ID : " + sensorId);

  connectWifi();

  Wire.begin(BME_SDA, BME_SCL);
  scd4x.begin(Wire, 0x62);
  scd4x.stopPeriodicMeasurement();
  delay(500);
  uint16_t err = scd4x.startPeriodicMeasurement();
  if (err) {
    Serial.println("SCD40 non détecté → mode données fictives");
    sensorOk = false;
  } else {
    Serial.println("SCD40 démarré");
    sensorOk = true;
  }
  delay(5000);
}

void loop() {
  uint16_t co2 = 0;
  float temp = 0, hum = 0;

  if (sensorOk) {
    uint16_t err = scd4x.readMeasurement(co2, temp, hum);
    if (err) {
      Serial.println("Erreur lecture SCD40 → données fictives");
      sensorOk = false;
    }
  }

  if (!sensorOk) {
    co2  = 400 + random(-20, 20);
    temp = fakeTemp;                        
    hum  = 50.0 + random(-50, 50) / 10.0;
  }

  int motion = digitalRead(PIR_PIN);
  Serial.printf("[%s] CO2=%d T=%.2f H=%.2f M=%d%s\n",
    sensorId.c_str(), co2, temp, hum, motion,
    sensorOk ? "" : " [FAKE]");

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi perdu, reconnexion...");
    connectWifi();
  }

  if (WiFi.status() == WL_CONNECTED) {
    // ── POST mesure ──────────────────────────────────────
    String payload = "{";
    payload += "\"sensor_id\":\"" + sensorId + "\",";
    payload += "\"co2\":"    + String(co2)     + ",";
    payload += "\"temp\":"   + String(temp, 2) + ",";
    payload += "\"hum\":"    + String(hum, 2)  + ",";
    payload += "\"motion\":" + String(motion);
    payload += "}";

    WiFiClient client;
    HTTPClient http;
    if (http.begin(client, serverUrl)) {
      http.addHeader("Content-Type", "application/json");
      int code = http.POST(payload);
      Serial.println("POST -> " + String(code));
      http.end();
    }

    // ── GET état relais (uniquement en mode fake) ─────────
    if (!sensorOk) {
      String url = String(heatingUrl) + "?sensor_id=" + sensorId;
      if (http.begin(client, url)) {
        int code = http.GET();
        if (code == 200) {
          String body = http.getString();
          if (body.indexOf("true") != -1) {
            fakeTemp += 0.12;  // 🔥 chauffage ON → monte ~+1.4°C/min
            Serial.println("Relais ON  → fakeTemp=" + String(fakeTemp, 1) + "°C");
          } else {
            fakeTemp -= 0.04;  // ❄️ chauffage OFF → descend ~-0.5°C/min
            Serial.println("Relais OFF → fakeTemp=" + String(fakeTemp, 1) + "°C");
          }
          fakeTemp = constrain(fakeTemp, 13.0, 35.0);
        }
        http.end();
      }
    }
  }

  delay(5000);
}