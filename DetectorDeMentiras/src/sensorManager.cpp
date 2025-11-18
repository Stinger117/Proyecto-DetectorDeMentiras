/*
 sensorManager.cpp
 -----------------
 Implementación para el sensor ECG AD8232.

 Funciones principales:
 - Lee datos analógicos del pin OUTPUT del AD8232.
 - Comprueba los pines LO+ y LO- (Leads Off). Si alguno está en ALTO, 
   significa que un electrodo está desconectado.
 - Almacena un conjunto de muestras (lote).
 - Espera un retraso (ej. 3ms) para la frecuencia de muestreo deseada (333 Hz).
 - Cuando el lote está completo, lo convierte en una cadena JSON.
*/

#include "SensorManager.h"

// Constructor actualizado
SensorManager::SensorManager(int analogPin, int loPlusPin, int loMinusPin, int batchSize, int delayMs)
  : _analogPin(analogPin), _loPlusPin(loPlusPin), _loMinusPin(loMinusPin),
    _batchSize(batchSize), _delayMs(delayMs), _index(0) {
      
    _samples = new float[_batchSize];
    
    // Configurar los modos de los pines
    pinMode(_analogPin, INPUT);
    pinMode(_loPlusPin, INPUT);
    pinMode(_loMinusPin, INPUT);
}

SensorManager::~SensorManager() {
    delete[] _samples;
}

bool SensorManager::available() {
    // Comprobar si los electrodos están desconectados
    // Los pines LO+ y LO- van a HIGH si un electrodo se desconecta.
    if (digitalRead(_loPlusPin) == HIGH || digitalRead(_loMinusPin) == HIGH) {
        // Si están desconectados, guardamos 0
        _samples[_index] = 0.0; 
    } else {
        // Si están conectados, leemos la señal de ECG
        _samples[_index] = analogRead(_analogPin);
    }
    
    _index++;

    delay(_delayMs); // Esperamos el delay configurado (ej. 3ms)

    if (_index >= _batchSize) {
        _index = 0;
        return true; // lote listo
    }

    return false;
}

// DEVUELVE EL LOTE EN FORMATO JSON CON TEMPERATURAS
String SensorManager::getDataBatchJSON(float temp1, float temp2) {
    // Inicia el JSON y el array de ECG
    String json = "{\"DatosECG\":[";  
    
    for (int i = 0; i < _batchSize; i++) {
        json += String(_samples[i], 0); 
        if (i < _batchSize - 1) json += ",";
    }
    json += "]\n"; // Cierra el array de ECG
    
    // Añade las claves de temperatura
    json += ",\"DatosTemp1\":\n";
    json += String(temp1, 2); // Añade temp1 con 2 decimales
    
    json += ",\"DatosTemp2\":\n";
    json += String(temp2, 2); // Añade temp2 con 2 decimales

    // Añade el timestamp y cierra el objeto JSON
    json += ",\"TimestampMilisegundos\":" + String(millis()) + "}"; 
    return json;
}