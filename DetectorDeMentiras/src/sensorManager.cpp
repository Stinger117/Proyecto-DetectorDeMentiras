/*
  sensorManager.cpp
  -----------------
  Esta clase se encarga de la lectura del potenciómetro conectado al ESP32,
  simulando una señal fisiológica (por ejemplo, para un detector de mentiras).

  Funciones principales:
  - Lee datos analógicos del pin definido (en este caso, GPIO 34).
  - Almacena un conjunto de muestras (lote) de tamaño definido.
  - Espera un pequeño retraso entre lecturas (por ejemplo, 5 ms) para mantener una frecuencia estable (~200 Hz).
  - Cuando el lote está completo, lo convierte en una cadena JSON lista para enviarse por MQTT.

  En el futuro, esta clase podría ampliarse para incluir otros sensores (temperatura, pulso, GSR, etc.),
  o aplicar filtros y normalización a las señales antes del envío.
*/

#include "SensorManager.h"

SensorManager::SensorManager(int pin, int batchSize, int delayMs)
  : _pin(pin), _batchSize(batchSize), _delayMs(delayMs), _index(0) {
    _samples = new float[_batchSize];
    pinMode(_pin, INPUT);
}

SensorManager::~SensorManager() {
    delete[] _samples;
}

bool SensorManager::available() {
    _samples[_index] = analogRead(_pin);
    _index++;

    delay(_delayMs);

    if (_index >= _batchSize) {
        _index = 0;
        return true; // lote listo
    }

    return false;
}

String SensorManager::getDataBatchJSON() {
    String json = "{\"DatosPotenciometro\":[";  
    for (int i = 0; i < _batchSize; i++) {
        json += String(_samples[i], 0); 
        if (i < _batchSize - 1) json += ",";
    }
    json += "],\"TimestampMilisegundos\":" + String(millis()) + "}"; 
    return json;
}
