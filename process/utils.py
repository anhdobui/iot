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

# sử dụng model yolov8 để detect phương tiện
model = YOLO('../model/yolov8n.pt')

green_light_duration = 5  # Thời gian bật đèn xanh
red_light_duration = 5  # Thời gian bật đèn đỏ
current_light_duration = green_light_duration  # Thời gian bật đèn hiện tại
light_timer = 0  # Đếm thời gian bật đèn

# Khởi tạo MQTT Client
client = mqtt.Client()
# Kết nối máy chủ MQTT
client.connect(broker_address, port, 20)

# hàm gửi tín hiệu
def push_message_to_mqtt(value):
    if not client.is_connected():
        client.connect(broker_address, port, 60)
    print("pushMessageToMQTT", value)
    client.publish(topic, value)

# Biến chia sẻ giữa các luồng
shared_queue = Queue()
# hàm gửi tín hiệu mqtt mỗi 10s,tín hiệu gửi đi nằm ở đầu Queue, sau đó clear Queue để giải phóng dung lượng
def mqtt_sender():
    while True:
        message = shared_queue.get() #lấy tín hiệu trong queue
        push_message_to_mqtt(message) # gọi hàm gửi tín hiệu 
        shared_queue.task_done() #giải phóng dung lượng queue
        time.sleep(10) # tạo độ trễ đến lần gửi tiếp theo

# Tạo một luồng riêng biệt để gửi MQTT messages
mqtt_thread = threading.Thread(target=mqtt_sender)
mqtt_thread.start()

light_timer = 5  # Khởi tạo đếm thời gian

# hàm xác định và in ra trạng thái maù đèn
def update_traffic_light(frame, traffic_light_status, countdown_timer):
    global light_timer

    red_color = (0, 0, 255)
    green_color = (0, 255, 0)


    if traffic_light_status == 'Green':
        color = green_color
        status_value = 0
    else:
        color = red_color
        status_value = 1


    # Kiểm tra nếu đã đủ thời gian để gửi tín hiệu mới
    if light_timer <= 0:
        
        light_timer = 5  # Đặt lại đếm thời gian

        # Cập nhật giá trị trong danh sách

    #in ra màn hình màu đèn giao thông
    cv2.putText(frame, traffic_light_status, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2, cv2.LINE_AA)
    cv2.putText(frame, f"{traffic_light_status} - {countdown_timer}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2, cv2.LINE_AA)
   
    return status_value

# hàm đếm số lượng xe
def count_cars_in_frame(frame):
    # Danh sách các lớp đối tượng mà mô hình có thể phát hiện
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

    # Thực hiện dự đoán với mô hình YOLO và truyền frame vào
    results = model(frame, stream=True)

    for r in results:
        boxes = r.boxes
        for box in boxes:
            # lấy ra tọa độ của đối tượng phát hiện
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            w, h = x2-x1, y2-y1
            conf = math.ceil((box.conf[0] * 100)) / 100

            cls = int(box.cls[0])
            currentClass = classNames[cls]

             # Kiểm tra nếu đối tượng là 'car', 'truck', 'Motorcycle' hoặc 'Bus' và độ chắc chắn lớn hơn 0.1
            if (currentClass == 'car' or currentClass == 'truck' or currentClass == 'Motorcycle' or currentClass == 'Bus') and conf > 0.1:
                car_count += 1
                # Hiển thị hình chữ nhật xung quanh đối tượng được phát hiện
                cvzone.cornerRect(frame, (x1, y1, w, h))
            elif currentClass == 'train' and conf > 0.1:
                is_train_detected = True
                cvzone.cornerRect(frame, (x1, y1, w, h))
    # print(is_train_detected)
    return car_count, is_train_detected

def create_quad_display(video_paths,case_video):
    # Tạo cửa sổ hiển thị Quad
    cv2.namedWindow('Quad Display', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Quad Display', 960, 720)

    green_light_duration = 5  # Đặt thời gian đèn xanh là 5 giây
    # Đặt thời gian đếm ngược ban đầu là thời gian đèn xanh
    countdown_timer = green_light_duration

    # Mảng chứa các đối tượng VideoCapture cho từng đường video
    video_captures = [cv2.VideoCapture(video_path) for video_path in video_paths]

    global light_timer

    while True:
        frames = []

        # Đọc frame từ mỗi đường video
        for cap in video_captures:
            ret, frame = cap.read()
            if not ret or frame is None or frame.size == 0:
                break
            frames.append(frame)
        # Kiểm tra xem có đủ 4 frames từ 4 đường video hay không
        if len(frames) != 4:
            break
        # Resize frame để có kích thước giống nhau
        h, w, _ = frames[0].shape
        h, w = h // 2, w // 2
        frames_resized = [cv2.resize(frame, (w, h)) for frame in frames]

        quad_frame = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)

        car_counts = []
        is_train_detected_list = []
        traffic_lights = []
        # Đếm số lượng xe và kiểm tra có xuất hiện tàu hỏa trong mỗi frame
        for i, frame in enumerate(frames_resized):
            car_count, is_train_detected = count_cars_in_frame(frame)
            car_counts.append(car_count)
            is_train_detected_list.append(is_train_detected)

            x, y = i % 2, i // 2
            y1, y2 = y * h, (y + 1) * h
            x1, x2 = x * w, (x + 1) * w
            quad_frame[y1:y2, x1:x2] = frame
        # Kiểm tra xem có tàu hỏa xuất hiện trong ít nhất một frame hay không
        any_train_detected = any(is_train_detected_list)

        # Xử lý trạng thái đèn giao thông cho mỗi frame
        for i, frame in enumerate(frames_resized):
           
               
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

        # Thực hiện đếm ngược thời gian nếu không có tàu hỏa
        if not any_train_detected:
            countdown_timer -= 1

            if countdown_timer < 0:
                countdown_timer = green_light_duration

            

            if countdown_timer < 0:
                countdown_timer = green_light_duration
                # Thực hiện các thao tác cần thiết khi chuyển từ đèn đỏ sang đèn xanh

        for i, frame in enumerate(frames_resized):
            x, y = i % 2, i // 2
            y1, y2 = y * h, (y + 1) * h
            x1, x2 = x * w, (x + 1) * w
            quad_frame[y1:y2, x1:x2] = frame
        
        #thêm tín hiệu vào queue 
        shared_queue.put(traffic_lights[case_video])
         #Duy trì tín hiệu trong queu < tránh tràn ram
        if shared_queue.qsize() > 2:
            shared_queue.get_nowait()
            
        #Hiển thị video 
        cv2.imshow('Quad Display', quad_frame)

        # Hiển thị frame Quad
        key = cv2.waitKey(1)
        # Đợi phím 'q' để thoát khỏi chương trình
        if key == ord('q'):
            break

        # Giảm đếm thời gian sau mỗi frame
        light_timer -= 1
        
    # Giải phóng tài nguyên và đóng cửa sổ
    for cap in video_captures:
        cap.release()
    cv2.destroyAllWindows()
