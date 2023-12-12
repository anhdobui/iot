from ultralytics import YOLO
import cv2
import cvzone
import math
import numpy as np
from pathlib import Path
import time
import paho.mqtt.client as mqtt
import threading
from queue import Queue

broker_address = "broker.mqttdashboard.com"
port = 1883
topic = "ESP32/Led"

model = YOLO('../model/yolov8n.pt')

green_light_duration = 5  # Thời gian bật đèn xanh
red_light_duration = 5  # Thời gian bật đèn đỏ
current_light_duration = green_light_duration  # Thời gian bật đèn hiện tại
light_timer = 0  # Đếm thời gian bật đèn

client = mqtt.Client()
client.connect(broker_address, port, 20)

def connect_to_broker():
    # print("connectToBroker")
    client.connect(broker_address, port, 60)

def push_message_to_mqtt(value):
    if not client.is_connected():
        connect_to_broker()
    print("pushMessageToMQTT", value)
    client.publish(topic, value)

# Biến chia sẻ giữa các luồng
shared_queue = Queue()
def mqtt_sender():
    while True:
        message = shared_queue.get()
        # print(shared_queue)
        push_message_to_mqtt(message)
        shared_queue.task_done()
        time.sleep(10)

# Tạo một luồng riêng biệt để gửi MQTT messages
mqtt_thread = threading.Thread(target=mqtt_sender)
mqtt_thread.start()

light_timer = 5  # Khởi tạo đếm thời gian

def update_traffic_light(frame, traffic_light_status, countdown_timer):
    global light_timer

    red_color = (0, 0, 255)
    green_color = (0, 255, 0)
    yellow_color = (0, 255, 255)

    if traffic_light_status == 'Green':
        color = green_color
        status_value = 0
    elif traffic_light_status == 'Red':
        color = red_color
        status_value = 1
    else:
        color = yellow_color
        status_value = 1

    # Kiểm tra nếu đã đủ thời gian để gửi tín hiệu mới
    if light_timer <= 0:
        
        light_timer = 5  # Đặt lại đếm thời gian

        # Cập nhật giá trị trong danh sách

    cv2.putText(frame, traffic_light_status, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2, cv2.LINE_AA)
    cv2.putText(frame, f"{traffic_light_status} - {countdown_timer}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2, cv2.LINE_AA)
   
    return status_value


def count_cars_in_frame(frame):
    classNames = ["person","bicycle","car","motorcycle","airplane","bus","train","truck",
              "boat","traffic light","fire hydrant","stop sign","parking meter","bench",
              "bird","cat","dog","horse","sheep","cow","elephant","bear","zebra","giraffe",
              "backpack","umbrella","handbag","tie","suitcase","frisbee","skis","snowboard",
              "sports ball","kite","baseball bat","baseball glove","skateboard","surfboard",
              "tennis racket","bottle","wine glass","cup","fork","knife","spoon","bowl","banana",
              "apple","sandwich","orange","broccoli","carrot","hot dog","pizza","donut","cake","chair",
              "couch","potted plant","bed","dining table","toilet","tv","laptop","mouse","remote","keyboard",
              "cell phone","microwave","oven","toaster","sink","refrigerator","book","clock","vase","scissors",
              "teddy bear","hair drier","toothbrush"]

    car_count = 0  
    is_train_detected = False

    results = model(frame, stream=True)

    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            w, h = x2-x1, y2-y1
            conf = math.ceil((box.conf[0] * 100)) / 100

            cls = int(box.cls[0])
            currentClass = classNames[cls]

            if (currentClass == 'car' or currentClass == 'truck' or currentClass == 'Motorcycle' or currentClass == 'Bus') and conf > 0.1:
                car_count += 1
                cvzone.cornerRect(frame, (x1, y1, w, h))
            elif currentClass == 'train' and conf > 0.1:
                is_train_detected = True
                cvzone.cornerRect(frame, (x1, y1, w, h))
    # print(is_train_detected)
    return car_count, is_train_detected

def create_quad_display(video_paths,case_video):
    cv2.namedWindow('Quad Display', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Quad Display', 960, 720)

    green_light_duration = 5  # Đặt thời gian đèn xanh là 5 giây
    yellow_light_duration = 5  # Đặt thời gian đèn vàng là 2 giây
    countdown_timer = green_light_duration
    is_yellow_light = False  # Biến để kiểm tra trạng thái đèn vàng
    video_captures = [cv2.VideoCapture(video_path) for video_path in video_paths]

    global light_timer

    while True:
        frames = []

        for cap in video_captures:
            ret, frame = cap.read()
            if not ret or frame is None or frame.size == 0:
                break
            frames.append(frame)

        if len(frames) != 4:
            break

        h, w, _ = frames[0].shape
        h, w = h // 2, w // 2
        frames_resized = [cv2.resize(frame, (w, h)) for frame in frames]

        quad_frame = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)

        car_counts = []
        is_train_detected_list = []
        traffic_lights = []

        for i, frame in enumerate(frames_resized):
            car_count, is_train_detected = count_cars_in_frame(frame)
            car_counts.append(car_count)
            is_train_detected_list.append(is_train_detected)

            x, y = i % 2, i // 2
            y1, y2 = y * h, (y + 1) * h
            x1, x2 = x * w, (x + 1) * w
            quad_frame[y1:y2, x1:x2] = frame

        any_train_detected = any(is_train_detected_list)

        for i, frame in enumerate(frames_resized):
            if is_yellow_light:
                # Hiển thị đèn vàng nếu đang ở trạng thái đèn vàng
                value = update_traffic_light(frame, 'Yellow', countdown_timer)
                cv2.putText(quad_frame, f'Traffic Light {i + 1}: Yellow', (20, 20 + (i + 1) * 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                traffic_lights.append(value)
            else:
                # Xác định trạng thái đèn giao thông dựa trên quy tắc mới
                if any_train_detected:
                    # Trường hợp có tàu hỏa, đèn xanh nếu có tàu hỏa và ngược lại
                    traffic_light_status = 'Green' if is_train_detected_list[i] else 'Red'
                else:
                    # Trường hợp không có tàu hỏa, ảnh có số lượng xe lớn nhất sẽ có đèn xanh, các ảnh khác có đèn đỏ
                    max_car_count_index = np.argmax(car_counts)
                    traffic_light_status = 'Green' if i == max_car_count_index else 'Red'

                # Cập nhật đèn giao thông và hiển thị trên frame
                value = update_traffic_light(frame, traffic_light_status, countdown_timer)
                cv2.putText(quad_frame, f'Traffic Light {i + 1}: {traffic_light_status}', (20, 20 + (i + 1) * 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                traffic_lights.append(value)
        
        print(traffic_lights)

        if not any_train_detected:
            if is_yellow_light:
                countdown_timer -= 1

                if countdown_timer < 0:
                    countdown_timer = green_light_duration
                    is_yellow_light = False
            else:
                countdown_timer -= 1

                if countdown_timer < 0:
                    countdown_timer = yellow_light_duration
                    is_yellow_light = True

        for i, frame in enumerate(frames_resized):
            x, y = i % 2, i // 2
            y1, y2 = y * h, (y + 1) * h
            x1, x2 = x * w, (x + 1) * w
            quad_frame[y1:y2, x1:x2] = frame
        
        shared_queue.put(traffic_lights[case_video])
        if shared_queue.qsize() > 2:
            shared_queue.get_nowait()

        cv2.imshow('Quad Display', quad_frame)

        key = cv2.waitKey(1)
        if key == ord('q'):
            break

        # Giảm đếm thời gian sau mỗi frame
        light_timer -= 1

    for cap in video_captures:
        cap.release()
    cv2.destroyAllWindows()
