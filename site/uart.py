import serial
import threading
import time
import subprocess
import sys
from flask import Flask, render_template
from flask_socketio import SocketIO
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

serial_ports = {
    0: {'ser': None, 'thread': None, 'port': '/dev/ttyUSB0'},
    1: {'ser': None, 'thread': None, 'port': '/dev/ttyUSB1'}
}

camera_process = None

def log_message(message):
    """Функция для логирования в консоль и на фронтенд"""

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

def init_serial(port_number):
    """Инициализация последовательного порта"""
    port_config = serial_ports[port_number]
    
    if not os.path.exists(port_config['port']):
        log_message(f"Порт {port_config['port']} не существует!")
        return False
    
    log_message(f"Попытка подключения к {port_config['port']}...")
    
    try:
        port_config['ser'] = serial.Serial(
            port=port_config['port'], 
            baudrate=9600, 
            timeout=1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        time.sleep(2)
        
        port_config['ser'].reset_input_buffer()
        port_config['ser'].reset_output_buffer()
        
        log_message(f"✅ Успешно подключено к {port_config['port']}")
        log_message(f"Порт открыт: {port_config['ser'].is_open}")
        log_message(f"Настройки: {port_config['ser'].get_settings()}")
        
        return True
        
    except Exception as e:
        log_message(f"❌ Ошибка подключения к {port_config['port']}: {str(e)}")
        return False

def serial_reader(port_number):
    """Чтение данных из последовательного порта"""
    port_config = serial_ports[port_number]    
    buffer = ""
    
    while port_config['ser'] and port_config['ser'].is_open:
        try:
            in_waiting = port_config['ser'].in_waiting
            if in_waiting > 0:
                raw_data = port_config['ser'].read(in_waiting)
                try:
                    chunk = raw_data.decode('utf-8', errors='ignore')
                    buffer += chunk
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if '\r' in line:
                            line = line.replace('\r', '')
                            
                        if line:
                            socketio.emit('com_data', {
                                'port': port_number, 
                                'message': f'🎨 {line}'
                            })
                            
                except Exception as decode_error:
                    print(f"[DEBUG] Ошибка декодирования: {decode_error}")
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"[DEBUG] ❌ Критическая ошибка чтения порта {port_number}: {str(e)}")
            socketio.emit('com_data', {
                'port': port_number, 
                'message': f'❌ Ошибка чтения: {str(e)}'
            })
            break

def test_serial_ports():
    """Функция для тестирования доступных портов"""
    log_message("=== ТЕСТИРОВАНИЕ ПОРТОВ ===")
    
    import glob
    available_ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    log_message(f"Доступные порты в системе: {available_ports}")
    
    for port_number, config in serial_ports.items():
        log_message(f"Проверка порта {port_number}: {config['port']}")
        if os.path.exists(config['port']):
            log_message(f"✅ Порт {config['port']} существует")
        else:
            log_message(f"❌ Порт {config['port']} не существует")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('com_command')
def handle_com_command(data):
    """Обработка команд, отправляемых в последовательный порт"""
    port_number = data.get('port', 0)
    command = data.get('command', '')
    
    log_message(f"Получена команда для порта {port_number}: '{command}'")
    
    port_config = serial_ports.get(port_number)
    if port_config and port_config['ser'] and port_config['ser'].is_open:
        try:
            port_config['ser'].write((command + '\n').encode())
            log_message(f"Команда отправлена в порт {port_number}")
            socketio.emit('com_data', {
                'port': port_number, 
                'message': f'📤 Отправлено: {command}'
            })
        except Exception as e:
            log_message(f"Ошибка отправки команды: {e}")
            socketio.emit('com_data', {
                'port': port_number, 
                'message': f'❌ Ошибка отправки: {str(e)}'
            })
    else:
        log_message(f"Порт {port_number} не доступен для отправки")
        socketio.emit('com_data', {
            'port': port_number, 
            'message': f'⚠️ Последовательный порт не открыт'
        })

@socketio.on('start_camera')
def handle_start_camera():
    """Запуск системы камеры по запросу от клиента"""
    socketio.emit('camera_log', '🎥 Запуск системы камеры...')
    camera_thread = threading.Thread(target=capture_camera_output, daemon=True)
    camera_thread.start()

@socketio.on('manual_test')
def handle_manual_test(data):
    """Ручное тестирование портов"""
    port_number = data.get('port', 0)
    log_message(f"Ручной тест порта {port_number}")
    
    port_config = serial_ports.get(port_number)
    if port_config and port_config['ser']:
        log_message(f"Состояние порта {port_number}: открыт={port_config['ser'].is_open}")
        log_message(f"Байт в буфере: {port_config['ser'].in_waiting}")
    else:
        log_message(f"Порт {port_number} не инициализирован")

@socketio.on('connect')
def handle_connect():
    log_message("Клиент подключился")

@socketio.on('disconnect')
def handle_disconnect():
    log_message("Клиент отключился")

if __name__ == '__main__':
    test_serial_ports()
    
    for port_number in serial_ports.keys():
        if init_serial(port_number):
            serial_thread = threading.Thread(
                target=serial_reader, 
                args=(port_number,), 
                daemon=True
            )
            serial_thread.start()
            serial_ports[port_number]['thread'] = serial_thread
        else:
            log_message(f"Не удалось инициализировать порт {port_number}")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)