import cv2
import numpy as np
import serial
import time

# Configuration
SERIAL_PORT = 'COM5'
BAUD_RATE = 9600
CAMERA_INDEX = 2
FRAME_WIDTH = 320
FRAME_HEIGHT = 240
FRAME_CENTER_X = FRAME_WIDTH // 2
FRAME_CENTER_Y = FRAME_HEIGHT // 2

# Vision parameters
L_H = 177; U_H = 2
L_S = 120; U_S = 255
L_V = 70; U_V = 255
MIN_CONTOUR_AREA = 500
erode_kernel = np.ones((5, 5), np.uint8)
closing_kernel = np.ones((9, 9), np.uint8)
erode_iterations = 1
dilate_iterations = 2

# Controller tuning
SMOOTHING_FACTOR = 0.7
CENTER_THRESHOLD_PIXELS = 8
P_GAIN_X = 0.04/2; D_GAIN_X = 0.10/2
P_GAIN_Y = 0.03/2; D_GAIN_Y = 0.07/2
MAX_ADJUSTMENT_X = 4.0
MAX_ADJUSTMENT_Y = 1.0
ROTATION_MIN = 0; ROTATION_MAX = 180
ELEVATION_MIN = 0; ELEVATION_MAX = 45

# Pick routine
FRAMES_TO_LOCK = 15
PICK_OFFSET_DEGREES = -35
ACTUATOR_EXTEND_TIME = 3
GRIP_OPEN = 40
GRIP_CLOSED = 180
DROPOFF_ROTATION = 170
DROPOFF_ELEVATION = 20

# Send a command to the Arduino
def send_command(ser, cmd):
    print(f"Sending: {cmd}")
    ser.write(f"{cmd}\n".encode())

# Pick routine
def execute_pick_routine(ser, final_rotation, final_elevation):
    print("\n--- LOCKED ON: EXECUTING PICK ROUTINE ---")

    pick_elevation = final_elevation + PICK_OFFSET_DEGREES
    pick_elevation = max(ELEVATION_MIN, min(ELEVATION_MAX, pick_elevation))

    send_command(ser, f"E{int(pick_elevation)}")
    time.sleep(1.0)

    send_command(ser, "A1")
    time.sleep(ACTUATOR_EXTEND_TIME)
    send_command(ser, "A0")

    send_command(ser, f"G{GRIP_CLOSED}")
    time.sleep(1.0)

    send_command(ser, "A-1")
    time.sleep(ACTUATOR_EXTEND_TIME)
    send_command(ser, "A0")

    send_command(ser, f"G{GRIP_OPEN}")
    time.sleep(1.0)

    print("--- PICK ROUTINE COMPLETE ---\n")

# Initialisation
try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
    time.sleep(2)
    print("Arduino connection established.")
except serial.SerialException as e:
    exit(f"FATAL: Could not connect to Arduino. {e}")

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

if not cap.isOpened():
    exit("FATAL: Could not open camera.")

# Main loop
current_rotation = 90
current_elevation = 15
previous_error_x = 0
previous_error_y = 0
smoothed_x = FRAME_CENTER_X
smoothed_y = FRAME_CENTER_Y
frame_counter = 0
COMMAND_INTERVAL = 2
STATE = "SEARCHING"
lock_on_counter = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    if STATE == "SEARCHING" or STATE == "LOCKING":
        frame_counter += 1

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower1 = np.array([L_H, L_S, L_V])
        upper1 = np.array([179, U_S, U_V])
        lower2 = np.array([0, L_S, L_V])
        upper2 = np.array([U_H, U_S, U_V])

        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)

        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, closing_kernel)
        mask = cv2.erode(mask, erode_kernel, iterations=erode_iterations)
        mask = cv2.dilate(mask, erode_kernel, iterations=dilate_iterations)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_contour = None
        if contours:
            best_contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(best_contour) < MIN_CONTOUR_AREA:
                best_contour = None

        if best_contour is not None:
            STATE = "LOCKING"

            ((x, y), radius) = cv2.minEnclosingCircle(best_contour)
            center_x = int(x)
            center_y = int(y)

            smoothed_x = SMOOTHING_FACTOR * center_x + (1 - SMOOTHING_FACTOR) * smoothed_x
            smoothed_y = SMOOTHING_FACTOR * center_y + (1 - SMOOTHING_FACTOR) * smoothed_y

            error_x = smoothed_x - FRAME_CENTER_X
            error_y = FRAME_CENTER_Y - smoothed_y

            if abs(error_x) > CENTER_THRESHOLD_PIXELS or abs(error_y) > CENTER_THRESHOLD_PIXELS:
                lock_on_counter = 0

                proportional_x = P_GAIN_X * error_x
                derivative_x = D_GAIN_X * (error_x - previous_error_x)
                adjustment_x = proportional_x + derivative_x

                proportional_y = P_GAIN_Y * error_y
                derivative_y = D_GAIN_Y * (error_y - previous_error_y)
                adjustment_y = proportional_y + derivative_y

                adjustment_x = max(-MAX_ADJUSTMENT_X, min(MAX_ADJUSTMENT_X, adjustment_x))
                adjustment_y = max(-MAX_ADJUSTMENT_Y, min(MAX_ADJUSTMENT_Y, adjustment_y))

                current_rotation -= adjustment_x
                current_elevation -= adjustment_y

                current_rotation = max(ROTATION_MIN, min(ROTATION_MAX, current_rotation))
                current_elevation = max(ELEVATION_MIN, min(ELEVATION_MAX, current_elevation))

                if frame_counter % COMMAND_INTERVAL == 0:
                    send_command(arduino, f"R{int(current_rotation)}")
                    send_command(arduino, f"E{int(current_elevation)}")

            else:
                lock_on_counter += 1

            previous_error_x = error_x
            previous_error_y = error_y

            cv2.circle(frame, (int(smoothed_x), int(smoothed_y)), 7, (0, 255, 0), -1)

        else:
            STATE = "SEARCHING"
            lock_on_counter = 0
            previous_error_x = 0
            previous_error_y = 0

        if lock_on_counter >= FRAMES_TO_LOCK:
            STATE = "PICKING"
            execute_pick_routine(arduino, current_rotation, current_elevation)
            STATE = "SEARCHING"
            lock_on_counter = 0
            current_rotation = 90
            current_elevation = 15

    dz_top_left = (
        FRAME_CENTER_X - CENTER_THRESHOLD_PIXELS,
        FRAME_CENTER_Y - CENTER_THRESHOLD_PIXELS,
    )
    dz_bottom_right = (
        FRAME_CENTER_X + CENTER_THRESHOLD_PIXELS,
        FRAME_CENTER_Y + CENTER_THRESHOLD_PIXELS,
    )

    cv2.rectangle(frame, dz_top_left, dz_bottom_right, (0, 255, 255), 1)

    status_text = f"State: {STATE} | Lock: {lock_on_counter}/{FRAMES_TO_LOCK}"
    cv2.putText(frame, status_text, (5, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    cv2.imshow("Camera Feed", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
print("Exiting and moving to safe position...")

send_command(arduino, "R90")
send_command(arduino, "E15")

time.sleep(2)

cap.release()
cv2.destroyAllWindows()
arduino.close()