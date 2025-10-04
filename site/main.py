import cv2
import numpy as np
import time

MORSE_CODE_DICT = {
    '.-\///': 'A',    # 2 символа + 3 слэша
    '-.../': 'B',     # 4 символа + 1 слэш
    '-.-./': 'C',     # 4 символа + 1 слэш
    '-..//': 'D',     # 3 символа + 2 слэша
    './///': 'E',     # 1 символ + 4 слэша
    '..-./': 'F',     # 4 символа + 1 слэш
    '--.//': 'G',     # 3 символа + 2 слэша
    '..../': 'H',     # 4 символа + 1 слэш
    '..///': 'I',     # 2 символа + 3 слэша
    '.---/': 'J',     # 4 символа + 1 слэш
    '-.-//': 'K',     # 3 символа + 2 слэша
    '.-../': 'L',     # 4 символа + 1 слэш
    '--///': 'M',     # 2 символа + 3 слэша
    '-.///': 'N',     # 2 символа + 3 слэша
    '---//': 'O',     # 3 символа + 2 слэша
    '.--./': 'P',     # 4 символа + 1 слэш
    '--.-/': 'Q',     # 4 символа + 1 слэш
    '.-.//': 'R',     # 3 символа + 2 слэша
    '...//': 'S',     # 3 символа + 2 слэша
    '-////': 'T',     # 1 символ + 4 слэша
    '..-//': 'U',     # 3 символа + 2 слэша
    '...-/': 'V',     # 4 символа + 1 слэш
    '.--//': 'W',     # 3 символа + 2 слэша
    '-..-/': 'X',     # 4 символа + 1 слэш
    '-.--/': 'Y',     # 4 символа + 1 слэш
    '--../': 'Z',     # 4 символа + 1 слэш
}

class MorseDecoder:
    def __init__(self):
        self.current_symbol = ''
        self.message = ''
        self.last_color = None
        self.last_change_time = time.time()
        self.color_active = False
        
    def add_color_signal(self, color):
        current_time = time.time()
        
        if color == 'red':
            self.current_symbol += '.'
            print(f"Обнаружена точка (.) | Текущая комбинация: {self.current_symbol}")
            
        elif color == 'blue':
            self.current_symbol += '-'
            print(f"Обнаружено тире (-) | Текущая комбинация: {self.current_symbol}")
        
        elif color == 'yellow':
            self.message = ''
            self.current_symbol = ''
        elif color == 'green':
            # Добавляем слэш, но не проверяем комбинацию сразу
            self.current_symbol += '/'
            print(f"Обнаружено (/) | Текущая комбинация: {self.current_symbol}")
        
        # Проверяем, достигли ли мы 5 символов
        if len(self.current_symbol) == 5:
            letter = MORSE_CODE_DICT.get(self.current_symbol, '?')
            self.message += letter
            print(f"Полная комбинация: {self.current_symbol} = {letter}")
            print(f"Текущее сообщение: {self.message}")
            self.current_symbol = ''
        
        self.last_change_time = current_time
        self.last_color = color


def get_color_ranges():
    ranges = {
        'red': [
            (np.array([0, 150, 100]), np.array([10, 255, 255])),  # Увеличена минимальная насыщенность и яркость
            (np.array([170, 150, 100]), np.array([180, 255, 255]))
        ],
        'green': [
            (np.array([50, 100, 100]), np.array([85, 255, 255]))  # Уже диапазон и выше минимальные значения
        ],
        'blue': [
            (np.array([100, 150, 100]), np.array([130, 255, 255]))  # Увеличена минимальная яркость
        ],
        'yellow': [
            (np.array([20, 150, 150]), np.array([130, 255, 255]))  # Желтый цвет
        ]
    }
    return ranges

def detect_color(frame, color_ranges):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    dominant_color = None
    max_area = 0
    
    # Добавим проверку общей яркости области
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    avg_brightness = np.mean(gray)
    
    for color_name, ranges in color_ranges.items():
        total_mask = None
        
        for lower, upper in ranges:
            mask = cv2.inRange(hsv, lower, upper)
            
            if total_mask is None:
                total_mask = mask
            else:
                total_mask = cv2.bitwise_or(total_mask, mask)
        
        # Улучшенная морфологическая обработка
        kernel = np.ones((7, 7), np.uint8)
        total_mask = cv2.morphologyEx(total_mask, cv2.MORPH_CLOSE, kernel)
        total_mask = cv2.morphologyEx(total_mask, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(total_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            # Увеличим минимальную площадь и добавим проверку яркости
            if area > 500 and avg_brightness > 50:  # Увеличена минимальная площадь
                if area > max_area:
                    max_area = area
                    dominant_color = color_name
    
    return dominant_color

def main():
    cap = cv2.VideoCapture(2)
    decoder = MorseDecoder()
    color_ranges = get_color_ranges()
    
    print("Запуск системы распознавания азбуки Морзе...")
    print("Красный = точка (.), Синий = тире (-), Зеленый = слэш (/)")
    print("Каждая буква должна состоять из 5 символов!")
    print("Нажмите 'q' для выхода")
    
    last_detected_color = None
    color_persistance_time = 0
    no_color_count = 0  # Счетчик кадров без цвета
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        detected_color = detect_color(frame, color_ranges)
        
        current_time = time.time()
        
        # Добавляем фильтр по стабильности
        if detected_color:
            no_color_count = 0
            if detected_color != last_detected_color:
                if current_time - color_persistance_time > 0.8:  # Увеличено время стабильности
                    decoder.add_color_signal(detected_color)
                    last_detected_color = detected_color
                    color_persistance_time = current_time
        else:
            no_color_count += 1
            # Если несколько кадров подряд нет цвета, сбрасываем last_detected_color
            if no_color_count > 2:
                last_detected_color = None
        
        # Автозавершение только если набрано 5 символов
        if len(decoder.current_symbol) > 0 and (current_time - decoder.last_change_time > 5.0):
            if len(decoder.current_symbol) == 5:
                letter = MORSE_CODE_DICT.get(decoder.current_symbol, '?')
                decoder.message += letter
                print(f"Автозавершение: {decoder.current_symbol} = {letter}")
            else:
                print(f"Таймаут: неполная комбинация {decoder.current_symbol} отброшена")
            
            print(f"Текущее сообщение: {decoder.message}")
            decoder.current_symbol = ''
        
        # Отображение информации
        cv2.putText(frame, f"Message: {decoder.message}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Current: {decoder.current_symbol}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Length: {len(decoder.current_symbol)}/5", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Last detected: {last_detected_color}", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Current frame: {detected_color}", (10, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.imshow('Morse Code Recognition', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"Финальное сообщение: {decoder.message}")

# Функция для калибровки цветов (опционально)
def calibrate_colors():
    """Функция для калибровки цветовых диапазонов под ваше освещение"""
    cap = cv2.VideoCapture(2)
    color_ranges = get_color_ranges()
    
    print("Режим калибровки. Нажмите 'q' для выхода")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Показываем маски для каждого цвета
        for color_name, ranges in color_ranges.items():
            total_mask = None
            for lower, upper in ranges:
                mask = cv2.inRange(hsv, lower, upper)
                if total_mask is None:
                    total_mask = mask
                else:
                    total_mask = cv2.bitwise_or(total_mask, mask)
            
            # Применяем маску к оригинальному изображению
            masked_frame = cv2.bitwise_and(frame, frame, mask=total_mask)
            cv2.putText(masked_frame, f"Mask: {color_name}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow(f'Mask {color_name}', masked_frame)
        
        cv2.imshow('Original', frame)
        cv2.imshow('HSV', hsv)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Если нужно провести калибровку, раскомментируйте следующую строку:
    # calibrate_colors()
    
    main()