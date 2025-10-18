from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
import statistics
import threading 
import time      # Para simular datos

# Importamos las claves desde el archivo de configuración
from config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, MQTT_USER, MQTT_PASS

# Configuración de Flask
app = Flask(__name__)
socketio = SocketIO(app)

# Variables para la Lógica del Detector
estado_prueba = "inactivo"
CALIBRATION_SAMPLES = 10
lecturas_calibracion_hr = []
lecturas_calibracion_temp = []
baseline_hr = 0
baseline_temp = 0

# Lógica del Cliente MQTT
# Esta función ahora será llamada cuando el cliente MQTT se conecte
def on_mqtt_connect(client, userdata, flags, rc):
    global estado_prueba
    if rc == 0:
        print("MQTT: Conectado al broker.")
        client.subscribe(MQTT_TOPIC)
        print(f"MQTT: Suscrito a {MQTT_TOPIC}")
        estado_prueba = "calibrando"
        socketio.emit('update_status', {'data': 'Conectado. Iniciando calibración...'})
    else:
        print(f"MQTT: Error de conexión, código: {rc}")

# Esta función se ejecuta con cada mensaje MQTT
def on_mqtt_message(client, userdata, msg):
    global estado_prueba, baseline_hr, baseline_temp, lecturas_calibracion_hr, lecturas_calibracion_temp
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        handle_sensor_data(data)
    except Exception as e:
        print(f"Error procesando mensaje: {e}")

# SEPARAMOS LA LÓGICA PARA PODER REUTILIZARLA CON DATOS SIMULADOS
def handle_sensor_data(data):
    global estado_prueba, baseline_hr, baseline_temp, lecturas_calibracion_hr, lecturas_calibracion_temp
    
    current_hr = data['heartRate']
    current_temp = data['temperature']  
    
    if estado_prueba == "calibrando":
        lecturas_calibracion_hr.append(current_hr)
        lecturas_calibracion_temp.append(current_temp)
        status_msg = f"Calibrando... Muestra {len(lecturas_calibracion_hr)}/{CALIBRATION_SAMPLES}"
        print(status_msg)
        socketio.emit('update_status', {'data': status_msg})

        if len(lecturas_calibracion_hr) >= CALIBRATION_SAMPLES:
            baseline_hr = statistics.mean(lecturas_calibracion_hr)
            baseline_temp = statistics.mean(lecturas_calibracion_temp)
            estado_prueba = "analizando"
            
            status_msg = f"Calibración completa. Línea base: {baseline_hr:.1f}bpm, {baseline_temp:.1f}°C. Analizando..."
            print(status_msg)
            socketio.emit('update_status', {'data': status_msg})
            lecturas_calibracion_hr.clear()
            lecturas_calibracion_temp.clear()

    elif estado_prueba == "analizando":
        hr_threshold = baseline_hr * 1.20
        temp_threshold = baseline_temp - 0.5
        
        indicadores = []
        if current_hr > hr_threshold:
            indicadores.append(f"Ritmo cardíaco elevado ({current_hr}bpm)")
        if current_temp < temp_threshold:
            indicadores.append(f"Temperatura baja ({current_temp}°C)")

        decision = "DICIENDO LA VERDAD"
        if indicadores:
            decision = "MINTIENDO"
        
        print(f"Análisis: {decision}, Razones: {', '.join(indicadores) or 'N/A'}")
        # Enviamos la decisión a la interfaz web
        socketio.emit('new_decision', {
            'decision': decision,
            'reasons': indicadores,
            'hr': current_hr,
            'temp': current_temp
        })

# Función para correr el cliente MQTT en un hilo separado
def mqtt_thread():
    client = mqtt.Client()
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# SIMULADOR DE DATOS (para probar sin el ESP32)
def data_simulator_thread():
    print("Iniciando simulacion de datos")
    global estado_prueba
    estado_prueba = "calibrando"
    socketio.emit('update_status', {'data': 'MODO SIMULADOR. Iniciando calibración...'})
    
    time.sleep(2)
    
    # Simula 10 lecturas de calibración
    for i in range(CALIBRATION_SAMPLES):
        fake_data = {'heartRate': 75 + i, 'temperature': 32.5 - i*0.1}
        handle_sensor_data(fake_data)
        time.sleep(2)
    
    # Simula lecturas de análisis, una de ellas de "mentira"
    while True:
        # Lectura normal
        handle_sensor_data({'heartRate': 80, 'temperature': 32.0})
        time.sleep(4)
        # Lectura de "mentira"
        handle_sensor_data({'heartRate': 110, 'temperature': 31.2})
        time.sleep(4)

# Rutas de Flask
@app.route('/')
def index():
    # Servimos el archivo HTML
    return render_template('index.html')

# Programa Principal
if __name__ == '__main__':
    # Elige si correr el simulador o el cliente MQTT real
    USE_SIMULATOR = True # Cambia a False cuando el ESP32 capture los datos reales

    if USE_SIMULATOR:
        # Inicia el hilo del simulador
        simulator = threading.Thread(target=data_simulator_thread)
        simulator.daemon = True
        simulator.start()
    else:
        # Inicia el cliente MQTT en segundo plano
        mqtt_client_thread = threading.Thread(target=mqtt_thread)
        mqtt_client_thread.daemon = True
        mqtt_client_thread.start()
    
    # Inicia el servidor web Flask
    print("Servidor web iniciado en http://127.0.0.1:5000")
    socketio.run(app, host='127.0.0.1', port=5000)
