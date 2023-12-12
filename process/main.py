import os
import threading
from utils import create_quad_display

# Lấy đường dẫn của thư mục hiện tại
current_folder = os.path.abspath(os.path.dirname(__file__))

# Kết hợp đường dẫn hiện tại với tên thư mục 'video'
video_folder = os.path.join(current_folder, "../video")

# Lấy danh sách tên tệp trong thư mục
video_files = os.listdir(video_folder)

# Lọc ra các tệp video (ví dụ: các tệp có phần mở rộng là .mp4)
video_files = [file for file in video_files if file.endswith(".mp4")]

# Tạo danh sách đường dẫn đầy đủ đến các video
video_paths = [os.path.join(video_folder, file) for file in video_files]

case_video = int(input("Chọn video của làn số 1:"))
create_display_thread = threading.Thread(target=create_quad_display, args=(video_paths,case_video,))

# Start the threads
create_display_thread.start()

create_display_thread.join()

