import serial
import threading
import time
import subprocess
import sys
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

ser = None
serial_thread = None
camera_process = None

def capture_camera_output():
    """Запускает main.py и захватывает его вывод"""
    global camera_process
    
    try:
        camera_process = subprocess.Popen(
            [sys.executable, 'main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        socketio.emit('camera_log', '🚀 Запуск системы распознавания азбуки Морзе...')
        
        for line in iter(camera_process.stdout.readline, ''):
            if line.strip():
                socketio.emit('camera_log', line.strip())
                
        camera_process.stdout.close()
        return_code = camera_process.wait()
        
        if return_code:
            socketio.emit('camera_log', f'❌ Процесс завершился с кодом: {return_code}')
            
    except Exception as e:
        socketio.emit('camera_log', f'❌ Ошибка запуска main.py: {str(e)}')

def init_serial(port='/dev/ttyUSB0', baudrate=9600):
    global ser
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        socketio.emit('com_data', f'✅ Подключено к {port} на {baudrate} бод')
        return True
    except Exception as e:
        socketio.emit('com_data', f'❌ Ошибка подключения: {str(e)}')
        return False

def serial_reader():
    """Чтение данных из последовательного порта"""
    while ser and ser.is_open:
        try:
            if ser.in_waiting > 0:
                data = ser.readline().decode('utf-8').strip()
                if data:
                    socketio.emit('com_data', f'ESP32: {data}')
        except Exception as e:
            socketio.emit('com_data', f'❌ Ошибка чтения: {str(e)}')
            break

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('com_command')
def handle_com_command(command):
    """Обработка команд, отправляемых в последовательный порт"""
    global ser
    if ser and ser.is_open:
        try:
            ser.write((command + '\r\n').encode())
            socketio.emit('com_data', f'📤 Отправлено: {command}')
        except Exception as e:
            socketio.emit('com_data', f'❌ Ошибка отправки: {str(e)}')
    else:
        socketio.emit('com_data', '⚠️ Последовательный порт не открыт')

@socketio.on('start_camera')
def handle_start_camera():
    """Запуск системы камеры по запросу от клиента"""
    socketio.emit('camera_log', '🎥 Запуск системы камеры...')
    camera_thread = threading.Thread(target=capture_camera_output, daemon=True)
    camera_thread.start()

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    if init_serial(port='/dev/ttyUSB0'):
        serial_thread = threading.Thread(target=serial_reader, daemon=True)
        serial_thread.start()
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)