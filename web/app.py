from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
import statistics
import threading
import time
import numpy as np
import neurokit2 as nk

# Importamos las claves desde el archivo de configuración
from config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, MQTT_USER, MQTT_PASS

# --- CONFIGURACIÓN ---
SAMPLING_RATE = 333 

historico_bpm = []
historico_temp = []
historico_ecg_raw = [] # Búfer de datos crudos

# Búfer de 6 segundos (~2000 puntos). NeuroKit necesita un búfer grande.
MAX_ECG_POINTS = 2000
MIN_ECG_POINTS_FOR_PROCESSING = 2000 

# Configuración de Flask
app = Flask(__name__)
socketio = SocketIO(app)

# --- LÓGICA DE LÍNEA BASE AUTOMÁTICA ---
baseline_hr = 0
baseline_temp = 0
baseline_set = False # ¿Ya hemos establecido la línea base?
baseline_readings_hr = [] # Almacén temporal para calcular la línea base
baseline_readings_temp = []
NUM_BASELINE_SAMPLES = 10 # Tomar 10 muestras válidas para la línea base

# --- LÓGICA DE PROCESAMIENTO DE SEÑAL ---
def process_ecg_batch(ecg_raw_data, temp1, temp2):
    global historico_ecg_raw, historico_bpm, historico_temp, baseline_set
    
    # 1. ACUMULAR la señal
    historico_ecg_raw.extend(ecg_raw_data)
    if len(historico_ecg_raw) > MAX_ECG_POINTS:
        historico_ecg_raw = historico_ecg_raw[-MAX_ECG_POINTS:]

    current_hr = 0 # BPM por defecto

    # 2. VERIFICAR si tenemos suficientes datos para procesar
    if len(historico_ecg_raw) < MIN_ECG_POINTS_FOR_PROCESSING:
        print(f"Acumulando datos de ECG... {len(historico_ecg_raw)}/{MIN_ECG_POINTS_FOR_PROCESSING} puntos.")
        current_hr = 0 
    else:
        # 3. PROCESAR el historial acumulado
        try:
            ecg_signal = np.array(historico_ecg_raw)
            
            if np.any(ecg_signal > 0): # Comprobar que no sean solo ceros
                # --- MÉTODO CORREGIDO (MÁS LIGERO) ---
                # 1. Limpiar la señal
                ecg_signal_cleaned = nk.ecg_clean(ecg_signal, sampling_rate=SAMPLING_RATE, method="neurokit")
                # 2. Encontrar picos R
                peaks_info = nk.ecg_findpeaks(ecg_signal_cleaned, sampling_rate=SAMPLING_RATE, method="neurokit")
                r_peaks = peaks_info['ECG_R_Peaks']
                
                if len(r_peaks) > 1:
                    # Corrección del error 'desired_units':
                    current_hr = nk.signal_rate(r_peaks, sampling_rate=SAMPLING_RATE).mean()
                else:
                    current_hr = 0 # No hay suficientes picos para calcular
                
                if np.isnan(current_hr):
                    current_hr = 0
            else: 
                print("Electrodos desconectados (datos ECG en 0). No se calcula BPM.")
                current_hr = 0 

        except Exception as e:
            print(f"Error procesando ECG con NeuroKit: {e}")
            current_hr = 0 

    # --- Manejo de temperatura ---
    if temp1 == -127.0 or temp2 == -127.0: 
        current_temp_avg = 0 
        temp1_val = 0
        temp2_val = 0
    else:
        current_temp_avg = (temp1 + temp2) / 2.0
        temp1_val = temp1
        temp2_val = temp2

    print(f"--- Datos Procesados --- HR: {current_hr:.1f} bpm, Temp Avg: {current_temp_avg:.1f} °C (T1:{temp1_val:.1f}, T2:{temp2_val:.1f})")

    if current_hr > 0: 
        historico_bpm.append(current_hr)
        historico_temp.append(current_temp_avg)

    handle_sensor_data({
        'heartRate': current_hr, 
        'temperature_avg': current_temp_avg,
        'temp1': temp1_val,
        'temp2': temp2_val,
        'ecg_raw': ecg_raw_data 
    })

# --- LÓGICA DEL DETECTOR (CON CALIBRACIÓN AUTOMÁTICA) ---
def handle_sensor_data(data):
    global baseline_hr, baseline_temp, baseline_set, baseline_readings_hr, baseline_readings_temp
    
    current_hr = data['heartRate']
    current_temp_avg = data['temperature_avg']
    current_temp1 = data['temp1']
    current_temp2 = data['temp2']
    ecg_raw_batch = data['ecg_raw'] 

    # Si el BPM es inválido (0), solo actualiza la gráfica y espera
    if current_hr <= 0:
        if not baseline_set:
             socketio.emit('update_status', {'data': 'Lectura no válida. Ajuste electrodos o espere...'})
        
        socketio.emit('sensor_data_update', {
            'ecg_data': ecg_raw_batch,
            'temp1': round(current_temp1, 1),
            'temp2': round(current_temp2, 1),
            'bpm': 0
        })
        return

    # --- LÓGICA DE CALIBRACIÓN AUTOMÁTICA ---
    if not baseline_set:
        baseline_readings_hr.append(current_hr)
        baseline_readings_temp.append(current_temp_avg)
        
        status_msg = f"Calculando línea base... {len(baseline_readings_hr)}/{NUM_BASELINE_SAMPLES}"
        print(status_msg)
        socketio.emit('update_status', {'data': status_msg})

        # Emitir datos para que la gráfica se mueva durante la calibración
        socketio.emit('sensor_data_update', {
            'ecg_data': ecg_raw_batch,
            'temp1': round(current_temp1, 1),
            'temp2': round(current_temp2, 1),
            'bpm': round(current_hr, 1)
        })

        if len(baseline_readings_hr) >= NUM_BASELINE_SAMPLES:
            baseline_hr = statistics.mean(baseline_readings_hr)
            baseline_temp = statistics.mean(baseline_readings_temp)
            baseline_set = True
            
            status_msg = f"Línea base ESTABLECIDA: {baseline_hr:.1f}bpm, {baseline_temp:.1f}°C. Analizando..."
            print(status_msg)
            socketio.emit('update_status', {'data': status_msg})
            
            baseline_readings_hr.clear()
            baseline_readings_temp.clear()
        
        return 

    # --- LÓGICA DE DECISIÓN (SOLO SI LA LÍNEA BASE ESTÁ LISTA) ---
    hr_threshold = baseline_hr * 1.20 
    temp_threshold = baseline_temp - 0.5 
    
    indicadores = []
    if current_hr > hr_threshold:
        indicadores.append(f"Ritmo cardíaco elevado ({current_hr:.1f}bpm)")
    if current_temp_avg < temp_threshold:
        indicadores.append(f"Temperatura baja ({current_temp_avg:.1f}°C)")

    decision = "DATOS"
    if indicadores:
        decision = "MINTIENDO"
    
    print(f"Análisis: {decision}, Razones: {', '.join(indicadores) or 'N/A'}")
    
    socketio.emit('new_decision', {
        'decision': decision,
        'reasons': indicadores,
        'hr': round(current_hr, 1),
        'temp_avg': round(current_temp_avg, 1),
        'temp1': round(current_temp1, 1),
        'temp2': round(current_temp2, 1),
        'ecg_data': ecg_raw_batch
    })

# --- LÓGICA MQTT ---
def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT: Conectado al broker.")
        client.subscribe(MQTT_TOPIC)
        print(f"MQTT: Suscrito a {MQTT_TOPIC}")
        socketio.emit('update_status', {'data': 'Conectado al servidor. Esperando datos...'})
    else:
        print(f"MQTT: Error de conexión, código: {rc}")

def on_mqtt_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        ecg_data_raw = data['DatosECG']
        temp_data_1 = data['DatosTemp1']
        temp_data_2 = data['DatosTemp2']
        process_ecg_batch(ecg_data_raw, temp_data_1, temp_data_2)
    except Exception as e:
        print(f"Error procesando mensaje MQTT: {e}")

def mqtt_thread():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_mqtt_connect
    # --- ¡CORRECCIÓN DEL TYPO! ---
    client.on_message = on_mqtt_message 
    
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    USE_SIMULATOR = False 

    if USE_SIMULATOR:
        print("El simulador está inactivo.")
    else:
        print("Iniciando cliente MQTT para recibir datos reales del ESP32...")
        mqtt_client_thread = threading.Thread(target=mqtt_thread)
        mqtt_client_thread.daemon = True
        mqtt_client_thread.start()
    
    print(f"Servidor web iniciado en http://0.0.0.0:5000")
    
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)