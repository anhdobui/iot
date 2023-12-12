#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = "do";
const char* password = "12341234";

#define MQTT_SERVER "broker.mqttdashboard.com"
#define MQTT_PORT 1883
#define MQTT_USER "anhdobui2002@gmail.com"
#define MQTT_PASSWORD "Nhom12toth02"
#define MQTT_LED_TOPIC "ESP32/Led"

#define LEDPINRed 25
#define LEDPINGreen 26
#define LEDPINYl 27


unsigned long previousMillis = 0; 
const long interval = 5000;
int current_ledState = LOW;
int last_ledState = LOW;

WiFiClient wifiClient;
PubSubClient client(wifiClient);


void setup_wifi() {
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  randomSeed(micros());
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void connect_to_broker() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32";
    clientId += String(random(0xffff), HEX);
    if (client.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD)) {
      Serial.println("connected");
      client.subscribe(MQTT_LED_TOPIC);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 2 seconds");
      delay(2000);
    }
  }
}

void callback(char* topic, byte *payload, unsigned int length) {
  Serial.println("-------new message from broker-----");
  Serial.print("topic: ");
  Serial.println(topic);
  Serial.print("message: ");
  Serial.write(payload, length);
  Serial.println();
  if (*payload == '1') current_ledState = HIGH;
  if (*payload == '0') current_ledState = LOW;
}

void changeLed(int current_ledState_Red){
  digitalWrite(LEDPINRed, LOW);
  digitalWrite(LEDPINGreen, LOW);
  for(int i=0; i<5; i++){
    digitalWrite(LEDPINYl, HIGH);
    delay(500);
    digitalWrite(LEDPINYl, LOW);
    delay(500);
  }
  digitalWrite(LEDPINGreen, !current_ledState_Red);
  digitalWrite(LEDPINRed, current_ledState_Red);
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(500);
  
  setup_wifi();
  client.setServer(MQTT_SERVER, MQTT_PORT );
  client.setCallback(callback);
  connect_to_broker();
  pinMode(LEDPINRed, OUTPUT);
  pinMode(LEDPINGreen, OUTPUT);
  pinMode(LEDPINYl, OUTPUT);
  digitalWrite(LEDPINRed, current_ledState);
  digitalWrite(LEDPINGreen, !current_ledState);
  digitalWrite(LEDPINYl, LOW);
}
void loop() {
  client.loop();
  if (!client.connected()) {
    connect_to_broker();
  }
  if (last_ledState != current_ledState) {
    last_ledState = current_ledState;
    changeLed(current_ledState);
  }
  
}

