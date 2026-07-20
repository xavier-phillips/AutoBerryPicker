# AutoBerryPicker - Code

The code is split between an Arduino program and a Python program. The Arduino controls the motors, actuator, and sensors, while the Python program handles the camera input, strawberry detection, and PID tracking.

The original plan was to run the Python program on a Raspberry Pi 3, but during the final build it was run from a laptop instead (refer to the main README and Week 15).

## Files
- `autoberrypicker-controller.ino` - Arduino code that controls the MG996R servos and linear actuator through the L298N motor driver. It also reads data from the FSR and colour sensors and receives position commands from the Python program.
- `autopicker_control.py` - Python program that handles webcam input, strawberry detection using HSV colour masking, PID control for x/y tracking, and the GUI used for adjusting HSV and PID settings. PID settings can also be saved and loaded using JSON.

## Running it

### Arduino
1. Open `autoberrypicker-controller.ino` in the Arduino IDE.
2. Select Arduino Uno R3 as the board.
3. Upload the code and connect the Arduino to the computer running the Python program through USB serial.

### Python
1. Install Python 3 and the required libraries:
```

pip install opencv-python numpy

```
2. Run `autopicker_control.py` with a USB webcam connected (a Microsoft LifeCam 3000 was used during testing).
3. Before running the main program, use the HSV Tuner to adjust the colour detection settings for the current lighting conditions.

## Note
This code was created for a VCE Systems Engineering folio project (Top Designs 2026 selection). It is not intended as a maintained software package.