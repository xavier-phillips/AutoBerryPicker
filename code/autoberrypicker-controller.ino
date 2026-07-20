#include <Servo.h>

// Pin assignments
const int ROTATION_PIN = 8;
const int ELEVATION_PIN = 10;
const int GRIP_PIN = 9;
const int ACTUATOR_IN1_PIN = 2;
const int ACTUATOR_IN2_PIN = 3;

// Default positions
const int HOME_ROTATION = 90;
const int HOME_ELEVATION = 60;
const int HOME_GRIP = 40;

// Servo objects
Servo rotationServo;
Servo elevationServo;
Servo gripServo;

// Serial input buffer
char buffer[32];
byte bufferIndex = 0;

void setup() {
  Serial.begin(9600);

  pinMode(ACTUATOR_IN1_PIN, OUTPUT);
  pinMode(ACTUATOR_IN2_PIN, OUTPUT);

  Serial.println("Attaching servos...");

  rotationServo.attach(ROTATION_PIN);
  elevationServo.attach(ELEVATION_PIN);
  gripServo.attach(GRIP_PIN);

  Serial.print("Rotation servo attached: ");
  Serial.println(rotationServo.attached());

  Serial.print("Elevation servo attached: ");
  Serial.println(elevationServo.attached());

  Serial.print("Grip servo attached: ");
  Serial.println(gripServo.attached());

  // Move to starting position
  rotationServo.write(HOME_ROTATION);
  elevationServo.write(HOME_ELEVATION);
  gripServo.write(HOME_GRIP);
  delay(1000);

  // Retract actuator on startup
  digitalWrite(ACTUATOR_IN1_PIN, LOW);
  digitalWrite(ACTUATOR_IN2_PIN, HIGH);
  delay(5000);

  digitalWrite(ACTUATOR_IN1_PIN, LOW);
  digitalWrite(ACTUATOR_IN2_PIN, LOW);

  // Prevent rotation servo from holding position when idle
  rotationServo.detach();

  Serial.println("Arduino ready - S:");
}

void loop() {
  while (Serial.available() > 0) {
    char incomingChar = Serial.read();

    if (incomingChar == '\n' || incomingChar == '\r') {
      if (bufferIndex > 0) {
        buffer[bufferIndex] = '\0';
        processCommand();
      }
      bufferIndex = 0;
    } 
    else {
      if (bufferIndex < (sizeof(buffer) - 1)) {
        buffer[bufferIndex++] = incomingChar;
      } 
      else {
        Serial.println("Buffer overflow!");
        bufferIndex = 0;
      }
    }
  }
}

void processCommand() {
  if (bufferIndex == 0) return;

  char component = buffer[0];
  int value = atoi(&buffer[1]);

  switch (component) {

    case 'w':
      elevationServo.write(50);
      Serial.println("Simple elevation UP command");
      break;

    case 's':
      elevationServo.write(30);
      Serial.println("Simple elevation DOWN command");
      break;

    case 'R':
      // Attach rotation servo when needed
      if (!rotationServo.attached()) {
        rotationServo.attach(ROTATION_PIN);
        delay(50);
      }

      rotationServo.write(value);
      break;

    case 'E':
      Serial.print("E command - Buffer: '");
      Serial.print(buffer);
      Serial.print("', Value: ");
      Serial.println(value);

      if (!elevationServo.attached()) {
        Serial.println("Elevation servo detached, reattaching...");
        elevationServo.attach(ELEVATION_PIN);
        delay(50);
      }

      elevationServo.write(value);

      Serial.print("Elevation set to: ");
      Serial.println(value);
      break;

    case 'G':
      gripServo.write(value);
      break;

    case 'K':
      if (rotationServo.attached()) {
        rotationServo.detach();
      }
      break;

    case 'P':
      // Polar command format: P<angle>,<radius>
      char* comma = strchr(buffer, ',');

      if (comma != NULL) {
        *comma = '\0';

        int angle = atoi(&buffer[1]);
        int radius = atoi(comma + 1);

        if (angle >= 0 && angle <= 180 && radius >= 30 && radius <= 90) {

          Serial.print("Polar command - Angle: ");
          Serial.print(angle);
          Serial.print(", Radius: ");
          Serial.println(radius);

          if (!rotationServo.attached()) {
            rotationServo.attach(ROTATION_PIN);
            delay(50);
          }

          rotationServo.write(angle);
          elevationServo.write(radius);

          Serial.print("Rotation: ");
          Serial.print(angle);
          Serial.print(", Elevation: ");
          Serial.println(radius);

        } else {
          Serial.print("Invalid polar values - Angle: ");
          Serial.print(angle);
          Serial.print(", Radius: ");
          Serial.println(radius);
        }

      } else {
        Serial.print("Invalid polar command format: ");
        Serial.println(buffer);
      }

      break;

    case 'A':
      if (value > 0) {
        digitalWrite(ACTUATOR_IN1_PIN, HIGH);
        digitalWrite(ACTUATOR_IN2_PIN, LOW);
      } 
      else if (value < 0) {
        digitalWrite(ACTUATOR_IN1_PIN, LOW);
        digitalWrite(ACTUATOR_IN2_PIN, HIGH);
      } 
      else {
        digitalWrite(ACTUATOR_IN1_PIN, LOW);
        digitalWrite(ACTUATOR_IN2_PIN, LOW);
      }
      break;
  }
}