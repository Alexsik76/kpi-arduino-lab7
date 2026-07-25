
import cv2

print("Init Camera...")
cap = cv2.VideoCapture(0)
# На RPi 5 іноді треба явно вказати бекенд, якщо є конфлікт
# cap = cv2.VideoCapture(0, cv2.CAP_V4L2) 

if not cap.isOpened():
    print("Cannot open camera")
else:
    print("Camera OK. Reading frame...")
    ret, frame = cap.read()
    if ret:
        print(f"Frame captured: {frame.shape}")
    cap.release()
print("Done.")