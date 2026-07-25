import time

import cv2

print("1. Init VideoCapture...")
# На RPi 5 іноді краще явно вказати бекенд V4L2
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

# Налаштування роздільної здатності (як у твоєму проекті)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("❌ Error: Could not open camera.")
    exit()

print("2. Camera opened. Warming up (2 sec)...")
time.sleep(2)

print("3. Capturing frame...")
ret, frame = cap.read()

if ret:
    print(f"✅ Frame captured! Shape: {frame.shape}")
    filename = "check_cam_output.jpg"
    cv2.imwrite(filename, frame)
    print(f"   Saved to {filename}")
else:
    print("❌ Error: Can't receive frame (stream end?).")

print("4. Releasing...")
cap.release()
print("Done.")