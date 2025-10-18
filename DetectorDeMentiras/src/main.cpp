#include <Arduino.h>

#include "sensorManager.h"

#include "communicationManager.h"



SensorManager sensorManager;

CommunicationManager commsManager;





const long interval = 2000;  

unsigned long previousMillis = 0;  



void setup() {

    Serial.begin(115200);

    sensorManager.setup();

    commsManager.setup();

}



void loop() {

 

    commsManager.loop();



    unsigned long currentMillis = millis();

    if (currentMillis - previousMillis >= interval) {

       

        previousMillis = currentMillis;



       

        float temp = sensorManager.getTemperature();

        int hr = sensorManager.getHeartRate();



        char jsonData[100];

        snprintf(jsonData, sizeof(jsonData), "{\"temperature\":%.2f,\"heartRate\":%d}", temp, hr);

       

        commsManager.publishData(jsonData);

        Serial.println("Datos enviados.");

    }



}