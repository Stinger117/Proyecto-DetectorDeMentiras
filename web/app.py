from flask import Flask, render_template, send_file, request
from flask_socketio import SocketIO
from datetime import datetime
import io

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ---------------------------
# Configuración de Flask
# ---------------------------
app = Flask(__name__)
socketio = SocketIO(app)

# ---------------------------
# Datos del paciente
# ---------------------------
paciente_actual = {
    "nombre": None,
    "edad": None,
    "id": None,
    "notas": None,
}

# Historial de mediciones para el PDF
historial_mediciones = []

# ---------------------------
# Métricas en tiempo real
# ---------------------------
latest_metrics = {
    "bpm": 0,
    "sdnn": 0,
    "rmssd": 0,
    "pnn50": 0,
    "temp_1": 0,
    "temp_2": 0,
    "status": "Esperando datos..."
}

# Señal de ECG filtrado (solo memoria reciente)
ecg_filtered = []

# ---------------------------
# Rutas Flask
# ---------------------------

@app.route('/')
def index():
    # Sirve la plantilla index.html
    return render_template('index.html')


@app.route('/set_paciente', methods=['POST'])
def set_paciente():
    """
    Espera un JSON como:
    {
      "nombre": "Juan Pérez",
      "edad": 30,
      "id": "P001",
      "notas": "Comentario opcional"
    }
    """
    global paciente_actual
    data = request.get_json() or {}

    paciente_actual["nombre"] = data.get("nombre")
    paciente_actual["edad"] = data.get("edad")
    paciente_actual["id"] = data.get("id")
    paciente_actual["notas"] = data.get("notas")

    return {"status": "ok", "message": "Paciente actualizado correctamente"}


@app.route('/api/sensores', methods=['POST'])
def api_sensores():
    """
    Recibe datos desde la API externa.

    Espera un JSON como:
    {
      "filter_ecg": 0.123,
      "bpm": 72,
      "sdnn": 40,
      "rmssd": 30,
      "pnn50": 12,
      "temp_1": 36.1,
      "temp_2": 36.3,
      "status": "Analizando..."
    }
    """
    global latest_metrics, ecg_filtered, historial_mediciones

    data = request.get_json(silent=True) or {}

    # ---------- 1) ECG FILTRADO -> gráfica ----------
    filter_ecg = data.get("filter_ecg")
    if filter_ecg is not None:
        try:
            value = float(filter_ecg)
            ecg_filtered.append(value)

            # Nos quedamos solo con los últimos 500 puntos
            if len(ecg_filtered) > 500:
                ecg_filtered = ecg_filtered[-500:]

            # Mandamos el último punto al frontend
            socketio.emit('update_chart', {"ecg": value})
        except (TypeError, ValueError):
            # Si viene un dato raro, lo ignoramos
            pass

    # ---------- 2) Actualizar métricas ----------
    for key in list(latest_metrics.keys()):
        if key in data and data[key] is not None:
            latest_metrics[key] = data[key]

    # Actualizar tarjetas de BPM y temperaturas
    socketio.emit('new_decision', {
        "hr":    latest_metrics["bpm"],     # lo usamos como BPM
        "temp1": latest_metrics["temp_1"],
        "temp2": latest_metrics["temp_2"],
        "sdnn":  latest_metrics["sdnn"],
        "rmssd": latest_metrics["rmssd"],
        "pnn50": latest_metrics["pnn50"]
    })

    # Actualizar mensaje de estado (caja de arriba)
    socketio.emit('update_status', {"data": latest_metrics["status"]})

    # ---------- 3) Guardar en historial para el PDF ----------
    historial_mediciones.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "heartRate": latest_metrics["bpm"],
        "temperature": latest_metrics["temp_1"],
        "decision": latest_metrics["status"],
        "reasons": [],
        "temp1": latest_metrics["temp_1"],
        "temp2": latest_metrics["temp_2"],
    })

    return {"ok": True, "message": "Datos recibidos correctamente"}, 200


@app.route('/reporte_pdf')
def reporte_pdf():
    """
    Genera un PDF con los datos del paciente actual y
    el historial de mediciones almacenado.
    """
    if not historial_mediciones:
        return "No hay mediciones para generar el reporte.", 400

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesizes=letter)
    width, height = letter

    y = height - 50

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Reporte de Polígrafo")
    y -= 30

    # Datos del paciente
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Paciente: {paciente_actual.get('nombre') or 'N/D'}")
    y -= 16
    c.drawString(50, y, f"Edad: {paciente_actual.get('edad') or 'N/D'}")
    y -= 16
    c.drawString(50, y, f"ID: {paciente_actual.get('id') or 'N/D'}")
    y -= 16
    c.drawString(50, y, f"Notas: {paciente_actual.get('notas') or '-'}")
    y -= 24

    # Resumen
    c.drawString(50, y, f"Total de mediciones: {len(historial_mediciones)}")
    y -= 24

    # Encabezado tabla
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50,  y, "Fecha/Hora")
    c.drawString(160, y, "HR (bpm)")
    c.drawString(230, y, "Temp1 (°C)")
    c.drawString(320, y, "Temp2 (°C)")
    c.drawString(410, y, "Estado")
    y -= 14
    c.setFont("Helvetica", 10)

    for m in historial_mediciones:
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica-Bold", 11)
            c.drawString(50,  y, "Fecha/Hora")
            c.drawString(160, y, "HR (bpm)")
            c.drawString(230, y, "Temp1 (°C)")
            c.drawString(320, y, "Temp2 (°C)")
            c.drawString(410, y, "Estado")
            y -= 14
            c.setFont("Helvetica", 10)

        c.drawString(50,  y, m.get("timestamp", ""))
        c.drawString(160, y, str(m.get("heartRate", "")))

        temp1 = m.get("temp1", m.get("temperature", 0))
        temp2 = m.get("temp2", 0)

        try:
            c.drawString(230, y, f"{float(temp1):.2f}")
        except (TypeError, ValueError):
            c.drawString(230, y, "-")

        try:
            c.drawString(320, y, f"{float(temp2):.2f}")
        except (TypeError, ValueError):
            c.drawString(320, y, "-")

        c.drawString(410, y, m.get("decision", ""))
        y -= 12

        reasons = m.get("reasons") or []
        if reasons:
            razones_texto = "; ".join(reasons)
            if y < 40:
                c.showPage()
                y = height - 50
            c.drawString(60, y, f"Razones: {razones_texto}")
            y -= 12

    c.showPage()
    c.save()
    buffer.seek(0)

    nombre_base = (paciente_actual.get("nombre") or "paciente").strip().replace(" ", "_")
    filename = f"reporte_{nombre_base}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


# ---------------------------
# Main
# ---------------------------
if __name__ == '__main__':
    print("Servidor web iniciado en http://0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
