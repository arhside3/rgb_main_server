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
            print("Полный сброс сообщения и текущей комбинации")
        
        elif color == 'green':
            self.current_symbol += '/'
            print(f"Обнаружено (/) | Текущая комбинация: {self.current_symbol}")
        
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
            (np.array([0, 100, 80]), np.array([8, 255, 255])),     # Яркий красный
            (np.array([172, 100, 80]), np.array([180, 255, 255])), # Яркий красный (другой край)
            (np.array([0, 50, 40]), np.array([8, 255, 150])),
            (np.array([172, 50, 40]), np.array([180, 255, 150]))
        ],
        'yellow': [
            (np.array([20, 120, 120]), np.array([30, 255, 255])),  # Чистый желтый
            (np.array([15, 100, 100]), np.array([35, 255, 255]))
        ],
        'green': [
            (np.array([40, 80, 80]), np.array([80, 255, 255]))     # Зеленый
        ],
        'blue': [
            (np.array([100, 80, 80]), np.array([130, 255, 255]))   # Синий
        ]
    }
    return ranges

def detect_color(frame, color_ranges):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    dominant_color = None
    max_area = 0
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    avg_brightness = np.mean(gray)
    
    color_areas = {}
    
    for color_name, ranges in color_ranges.items():
        total_mask = None
        
        for lower, upper in ranges:
            mask = cv2.inRange(hsv, lower, upper)
            
            if total_mask is None:
                total_mask = mask
            else:
                total_mask = cv2.bitwise_or(total_mask, mask)
        
        kernel = np.ones((5, 5), np.uint8)
        total_mask = cv2.morphologyEx(total_mask, cv2.MORPH_CLOSE, kernel)
        total_mask = cv2.morphologyEx(total_mask, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(total_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        max_contour_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_contour_area:
                max_contour_area = area
        
        if max_contour_area > 200 and avg_brightness > 30:
            color_areas[color_name] = max_contour_area
    
    if color_areas:
        dominant_color = max(color_areas, key=color_areas.get)
    
    return dominant_color

def main():
    cap = cv2.VideoCapture(2)
    decoder = MorseDecoder()
    color_ranges = get_color_ranges()
    
    print("Запуск системы распознавания азбуки Морзе...")
    print("Красный = точка (.), Синий = тире (-), Зеленый = слэш (/), Желтый = полный сброс")
    print("Каждая буква должна состоять из 5 символов!")
    print("Комбинация НЕ сбрасывается при пропадании цвета - только при наборе 5 символов или желтом цвете")
    print("Нажмите 'q' для выхода")
    
    last_detected_color = None
    color_persistance_time = 0
    no_color_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        detected_color = detect_color(frame, color_ranges)
        
        current_time = time.time()
        
        if detected_color:
            no_color_count = 0
            if detected_color != last_detected_color:
                if current_time - color_persistance_time > 0.5:
                    decoder.add_color_signal(detected_color)
                    last_detected_color = detected_color
                    color_persistance_time = current_time
        else:
            no_color_count += 1
            if no_color_count > 3:
                last_detected_color = None
        
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
        
        if len(decoder.current_symbol) > 0:
            cv2.putText(frame, "STATUS: Waiting for next color...", (10, 180), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        cv2.imshow('Morse Code Recognition', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"Финальное сообщение: {decoder.message}")

def debug_colors():
    cap = cv2.VideoCapture(2)
    color_ranges = get_color_ranges()
    
    print("Режим отладки цветов. Нажмите 'q' для выхода")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        for color_name, ranges in color_ranges.items():
            total_mask = None
            for lower, upper in ranges:
                mask = cv2.inRange(hsv, lower, upper)
                if total_mask is None:
                    total_mask = mask
                else:
                    total_mask = cv2.bitwise_or(total_mask, mask)
            
            masked_frame = cv2.bitwise_and(frame, frame, mask=total_mask)
            
            contours, _ = cv2.findContours(total_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            total_area = sum(cv2.contourArea(contour) for contour in contours)
            
            cv2.putText(masked_frame, f"{color_name} (area: {total_area:.0f})", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow(f'Mask {color_name}', masked_frame)
        
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        hsv_center = hsv[center_y, center_x]
        bgr_center = frame[center_y, center_x]
        
        cv2.circle(frame, (center_x, center_y), 5, (0, 255, 0), 2)
        cv2.putText(frame, f"HSV: {hsv_center}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"BGR: {bgr_center}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow('Original with center point', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()