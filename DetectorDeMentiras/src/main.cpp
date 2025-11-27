/*
 main.cpp
 --------
 Archivo principal del proyecto "Detector de Mentiras" basado en ESP32.

 Este programa integra:
 - SensorManager: Para leer el ECG a alta frecuencia (333 Hz).
 - DallasTemperature: Para leer 2 sensores de temperatura DS18B20 a baja frecuencia.
 - CommunicationManager: Para manejar la conexión WiFi y MQTT.

 Flujo general:
 1. Se inicializa y conecta a WiFi/MQTT.
 2. Inicia el bus 1-Wire y busca los 2 sensores de temperatura.
 3. En el loop:
    a. Bucle de alta velocidad (333 Hz): Muestrea el ECG usando sensor.available().
    b. Bucle de baja velocidad (cada 2 seg): Pide y lee las temperaturas de forma no bloqueante.
 4. Cuando un lote de ECG está listo, se empaqueta con la ÚLTIMA lectura
    de temperatura conocida y se envía por MQTT.
*/

#include <Arduino.h>
#include "SensorManager.h"
#include "CommunicationManager.h"
#include "clavesConfig.h"

// --- LIBRERÍAS DE TEMPERATURA ---
#include <OneWire.h>
#include <DallasTemperature.h>

// --- CONFIGURACIÓN DE PINES ---
#define ONE_WIRE_BUS 33 // Pin D33 para los sensores DS18B20

// --- OBJETOS GLOBALES ---
// Sensor ECG (pin 36=VP, 2=D2, 4=D4, lote 150, delay 3ms=333Hz)
SensorManager sensor(36, 2, 4, 150, 3); 
CommunicationManager comm(MQTT_SERVER, MQTT_PORT, MQTT_USER, MQTT_PASS, "ESP32_ECG_TEMP");

// Objetos para la temperatura
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensors(&oneWire);

// Variables para guardar las direcciones de los 2 sensores
DeviceAddress tempAddr1, tempAddr2;

// Variables globales para guardar la última temperatura leída
// Las inicializamos con un valor inválido por si la lectura falla
float lastTemp1 = -127.0; 
float lastTemp2 = -127.0;

// Temporizador no bloqueante para la temperatura
unsigned long previousMillisTemp = 0;
const long intervalTemp = 2000; // Pedir temperatura cada 2 segundos

// --- FUNCIÓN AUXILIAR PARA IMPRIMIR DIRECCIONES (DEBUG) ---
void printAddress(DeviceAddress deviceAddress) {
  for (uint8_t i = 0; i < 8; i++) {
    if (deviceAddress[i] < 16) Serial.print("0");
    Serial.print(deviceAddress[i], HEX);
  }
}

void setup() {
    Serial.begin(115200);
    Serial.println("Iniciando Detector de Mentiras - Modo ECG + Temperatura");

    // Iniciar sensores de temperatura
    tempSensors.begin();
    Serial.println("Buscando sensores DS18B20...");
    int sensorCount = tempSensors.getDeviceCount();
    Serial.print(sensorCount); Serial.println(" sensores encontrados.");

    if (sensorCount >= 2) {
        // Obtenemos y guardamos las direcciones de los primeros dos sensores
        if (tempSensors.getAddress(tempAddr1, 0) && tempSensors.getAddress(tempAddr2, 1)) {
            Serial.print("Sensor 1 (Temp1) Dirección: "); printAddress(tempAddr1); Serial.println();
            Serial.print("Sensor 2 (Temp2) Dirección: "); printAddress(tempAddr2); Serial.println();
            // Fijamos la resolución (12-bit es más preciso pero más lento, ~750ms)
            tempSensors.setResolution(tempAddr1, 12);
            tempSensors.setResolution(tempAddr2, 12);
        } else {
            Serial.println("Error al obtener direcciones de sensores.");
        }
    } else {
        Serial.println("¡ERROR! Se esperaban 2 sensores de temperatura, revise conexiones.");
    }

    // Conexión WiFi y MQTT
    comm.connectWiFi(WIFI_SSID, WIFI_PASS);
    comm.connectMQTT();

    // Pedimos la primera lectura de temperatura (de forma asíncrona)
    tempSensors.requestTemperatures(); 
    // Damos tiempo al temporizador para que no se active inmediatamente
    previousMillisTemp = millis(); 

    Serial.println("Sistema listo.");
}

void loop() {
    comm.loop(); // Manejar MQTT

    // --- Lógica de Temperatura (Baja Frecuencia, No Bloqueante) ---
    unsigned long currentMillis = millis();
    if (currentMillis - previousMillisTemp >= intervalTemp) {
        previousMillisTemp = currentMillis; // Reinicia el temporizador

        // Leemos las temperaturas usando las direcciones guardadas
        // getTempC() lee el resultado de la petición anterior
        lastTemp1 = tempSensors.getTempC(tempAddr1);
        lastTemp2 = tempSensors.getTempC(tempAddr2);

        // Verificamos si la lectura fue válida (DS18B20 devuelve -127 si falla)
        if(lastTemp1 == -127.0) {
            Serial.println("Error al leer Temp 1");
        }
        if(lastTemp2 == -127.0) {
            Serial.println("Error al leer Temp 2");
        }

        Serial.print("Temp 1: "); Serial.print(lastTemp1);
        Serial.print(" C | Temp 2: "); Serial.print(lastTemp2); Serial.println(" C");

        // Pedimos la *siguiente* lectura (tardará ~750ms en estar lista)
        tempSensors.requestTemperatures(); 
    }

    // --- Lógica de ECG (Alta Frecuencia) ---
    if (sensor.available()) {
        // El lote de ECG está listo
        // Usamos las *últimas* temperaturas guardadas para construir el JSON
        String lote = sensor.getDataBatchJSON(lastTemp1, lastTemp2); 
        
        comm.publish("senores/poligrafo", lote.c_str());
        Serial.println("Lote de ECG+Temp enviado al MQTT.");
    }
}