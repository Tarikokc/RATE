#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

const char* ssid     = "iPhone de Tarik";
const char* password = "TarikArt942003.#";

// IP de ton PC et route Flask
const char* serverUrl = "http://172.20.10.8:5000/measure";

#define BME_SDA D2
#define BME_SCL D1
const int PIR_PIN = D5;   // SIG du PIR sur D5

Adafruit_BME280 bme;      // I2C

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(PIR_PIN, INPUT);

  Serial.println();
  Serial.println("Connexion au WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connecte au WiFi, IP: ");
  Serial.println(WiFi.localIP());

  // I2C sur D1/D2
  Wire.begin(BME_SDA, BME_SCL);

  Serial.println("Initialisation BME280...");
  bool status = bme.begin(0x76);   // essaie 0x77 si erreur
  if (!status) {
    Serial.println("Erreur: BME280 introuvable !");
  } else {
    Serial.println("BME280 OK");
  }
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    // Lecture capteurs
    float temp = bme.readTemperature();        // °C
    float hum  = bme.readHumidity();           // %
    float pres = bme.readPressure() / 100.0;   // hPa
    int motion = digitalRead(PIR_PIN);         // 0 = pas de mouvement, 1 = mouvement

    Serial.print("T="); Serial.print(temp);
    Serial.print(" H="); Serial.print(hum);
    Serial.print(" P="); Serial.print(pres);
    Serial.print(" M="); Serial.println(motion);

    // Construction du JSON
    String payload = "{";
    payload += "\"sensor\":\"esp8266-1\",";
    payload += "\"temp\":"   + String(temp, 2) + ",";
    payload += "\"hum\":"    + String(hum, 2)  + ",";
    payload += "\"pres\":"   + String(pres, 2) + ",";
    payload += "\"motion\":" + String(motion);
    payload += "}";

    // Envoi HTTP vers Flask
    WiFiClient client;
    HTTPClient http;

    Serial.println("Tentative HTTP vers le serveur...");
    if (http.begin(client, serverUrl)) {
      http.addHeader("Content-Type", "application/json");
      int httpCode = http.POST(payload);

      Serial.print("HTTP POST code: ");
      Serial.println(httpCode);

      if (httpCode > 0) {
        String response = http.getString();
        Serial.print("Reponse serveur: ");
        Serial.println(response);
      }
      http.end();
    } else {
      Serial.println("Erreur http.begin");
    }
  } else {
    Serial.println("WiFi deconnecte, reconnexion...");
    WiFi.reconnect();
  }

  delay(5000);  // toutes les 5 s
}
