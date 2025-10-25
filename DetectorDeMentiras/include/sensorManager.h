/*
  SensorManager.h
  ----------------
  Esta clase se encarga de gestionar las lecturas analógicas del potenciómetro.
  - Toma lecturas continuas del pin configurado.
  - Agrupa un número definido de muestras (lote).
  - Prepara los datos en formato JSON para ser enviados al broker MQTT.

  En este proyecto, el potenciómetro se usa como una fuente de señal analógica
  para simular lecturas de un sensor (por ejemplo, pulso o respuesta galvánica),
  lo que permitirá más adelante enviar señales reales para el detector de mentiras.
*/

#ifndef SENSOR_MANAGER_H
#define SENSOR_MANAGER_H

#include <Arduino.h>

class SensorManager {
private:
    int _pin;
    int _batchSize;
    int _delayMs;
    int _index;
    float* _samples;

public:
    SensorManager(int pin, int batchSize, int delayMs);
    ~SensorManager();

    bool available();               // Indica si un lote de datos está listo
    String getDataBatchJSON();      // Devuelve el lote en formato JSON
};

#endif
