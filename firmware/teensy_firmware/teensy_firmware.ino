/*
  ControlForge Teensy Firmware (teensy_firmware.ino)

  Firmware for the Teensy 4.0/4.1 microcontroller to run the cart double pendulum.
  
  Functions:
  1. Decodes quadrature encoders (or reads magnetic AS5600 encoders).
  2. Runs a real-time control loop at 100Hz (dt = 10ms).
  3. Estimates joint and cart velocities using derivative filters.
  4. Reads serial command packets from the Python dashboard ("CMD,voltage\n").
  5. Computes onboard PID/LQR stabilization or applies the dashboard command.
  6. Emits telemetry packets in the ControlForge 6-state format:
     "timestamp,theta1,theta2,theta1_dot,theta2_dot,cart_pos,cart_vel"
  7. Enforces hardware emergency stop boundaries.
*/

#include <Arduino.h>

// ------------------------------------------------------------
// Pin Definitions
// ------------------------------------------------------------
// Motor Driver Pins (e.g. Cytron, IBT-2, or generic H-Bridge)
const int PIN_MOTOR_PWM = 3;
const int PIN_MOTOR_DIR = 4;

// Encoder Pins (Teensy supports hardware interrupts on all pins)
const int PIN_ENC_CART_A = 5;
const int PIN_ENC_CART_B = 6;
const int PIN_ENC_JOINT1_A = 7;
const int PIN_ENC_JOINT1_B = 8;
const int PIN_ENC_JOINT2_A = 9;
const int PIN_ENC_JOINT2_B = 10;

// Hardware E-Stop switch (Normally Closed, pulls LOW on trigger)
const int PIN_ESTOP_INPUT = 12;

// LED Status Indicator
const int PIN_STATUS_LED = 13;

// ------------------------------------------------------------
// Physical Constants & Conversion Factors
// ------------------------------------------------------------
// Encoders CPR (Counts Per Revolution)
const float ENCODER_JOINT_CPR = 4096.0; // e.g. 12-bit magnetic encoder
const float ENCODER_CART_CPR = 2000.0;  // e.g. optical encoder on track

// Conversion constants
const float RAD_PER_TICK = (2.0 * PI) / ENCODER_JOINT_CPR;
const float METERS_PER_TICK = 0.00005; // 0.05 mm per tick on cart timing belt

// ------------------------------------------------------------
// Volatile Encoder Counters (modified in ISRs)
// ------------------------------------------------------------
volatile long count_cart = 0;
volatile long count_joint1 = 0;
volatile long count_joint2 = 0;

// ------------------------------------------------------------
// State Variables
// ------------------------------------------------------------
float theta1 = 0.0;
float theta2 = 0.0;
float theta1_dot = 0.0;
float theta2_dot = 0.0;
float cart_pos = 0.0;
float cart_vel = 0.0;

// Previous values for derivative calculation
float prev_theta1 = 0.0;
float prev_theta2 = 0.0;
float prev_cart_pos = 0.0;

// Velocity filter coefficient (Low-pass filter alpha: 0.1 to 0.3)
const float FILTER_ALPHA = 0.25;

// Loop Timing
unsigned long last_loop_time = 0;
const unsigned long LOOP_PERIOD_MS = 10; // 100 Hz

// ------------------------------------------------------------
// Safety Limits & Watchdogs
// ------------------------------------------------------------
const float LIMIT_CART_POS_M = 1.45; // Max track travel limits (safety buffer)
bool estop_active = false;
String estop_cause = "";

// Serial input buffer
String input_buffer = "";

// ------------------------------------------------------------
// Interrupt Service Routines (ISRs) for Encoder Reading
// ------------------------------------------------------------
void isr_cart() {
  if (digitalRead(PIN_ENC_CART_A) == digitalRead(PIN_ENC_CART_B)) {
    count_cart++;
  } else {
    count_cart--;
  }
}

void isr_joint1() {
  if (digitalRead(PIN_ENC_JOINT1_A) == digitalRead(PIN_ENC_JOINT1_B)) {
    count_joint1++;
  } else {
    count_joint1--;
  }
}

void isr_joint2() {
  if (digitalRead(PIN_ENC_JOINT2_A) == digitalRead(PIN_ENC_JOINT2_B)) {
    count_joint2++;
  } else {
    count_joint2--;
  }
}

// ------------------------------------------------------------
// Setup
// ------------------------------------------------------------
void setup() {
  Serial.begin(115200);

  // Configure Motor Outputs
  pinMode(PIN_MOTOR_PWM, OUTPUT);
  pinMode(PIN_MOTOR_DIR, OUTPUT);
  analogWriteFrequency(PIN_MOTOR_PWM, 20000); // 20kHz quiet ultrasonic PWM
  analogWrite(PIN_MOTOR_PWM, 0);

  // Configure Status LED
  pinMode(PIN_STATUS_LED, OUTPUT);
  digitalWrite(PIN_STATUS_LED, HIGH);

  // Configure Safety E-stop input (Using internal pullup)
  pinMode(PIN_ESTOP_INPUT, INPUT_PULLUP);

  // Attach Encoder Interrupts
  pinMode(PIN_ENC_CART_A, INPUT_PULLUP);
  pinMode(PIN_ENC_CART_B, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_CART_A), isr_cart, CHANGE);

  pinMode(PIN_ENC_JOINT1_A, INPUT_PULLUP);
  pinMode(PIN_ENC_JOINT1_B, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_JOINT1_A), isr_joint1, CHANGE);

  pinMode(PIN_ENC_JOINT2_A, INPUT_PULLUP);
  pinMode(PIN_ENC_JOINT2_B, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_JOINT2_A), isr_joint2, CHANGE);

  last_loop_time = millis();
}

// ------------------------------------------------------------
// Set Motor Output Safely
// ------------------------------------------------------------
void write_motor_output(float control_voltage) {
  // Enforce ESTOP: If triggered, completely cut power to motor
  if (estop_active) {
    analogWrite(PIN_MOTOR_PWM, 0);
    digitalWrite(PIN_MOTOR_DIR, LOW);
    return;
  }

  // Map voltage (-12.0V to 12.0V) to PWM (0 - 255)
  // Clamp voltage to safe limits
  float clamped_v = max(-12.0f, min(12.0f, control_voltage));
  int pwm_val = abs((int)(clamped_v * (255.0 / 12.0)));
  
  if (clamped_v >= 0.0) {
    digitalWrite(PIN_MOTOR_DIR, HIGH);
  } else {
    digitalWrite(PIN_MOTOR_DIR, LOW);
  }
  
  analogWrite(PIN_MOTOR_PWM, pwm_val);
}

// ------------------------------------------------------------
// Main Loop
// ------------------------------------------------------------
void loop() {
  unsigned long current_time = millis();

  // Run real-time loop at 100Hz
  if (current_time - last_loop_time >= LOOP_PERIOD_MS) {
    float dt = (current_time - last_loop_time) / 1000.0f;
    last_loop_time = current_time;

    // 1. Read Raw Sensors
    noInterrupts(); // Temporarily disable interrupts to copy values atomically
    long c_cart = count_cart;
    long c_j1 = count_joint1;
    long c_j2 = count_joint2;
    interrupts();

    // 2. Convert to SI Units
    cart_pos = c_cart * METERS_PER_TICK;
    theta1 = c_j1 * RAD_PER_TICK;
    theta2 = c_j2 * RAD_PER_TICK;

    // 3. Compute Velocities with Derivative Low-Pass Filter
    float raw_cart_vel = (cart_pos - prev_cart_pos) / dt;
    float raw_theta1_vel = (theta1 - prev_theta1) / dt;
    float raw_theta2_vel = (theta2 - prev_theta2) / dt;

    cart_vel = FILTER_ALPHA * raw_cart_vel + (1.0f - FILTER_ALPHA) * cart_vel;
    theta1_dot = FILTER_ALPHA * raw_theta1_vel + (1.0f - FILTER_ALPHA) * theta1_dot;
    theta2_dot = FILTER_ALPHA * raw_theta2_vel + (1.0f - FILTER_ALPHA) * theta2_dot;

    // Save previous values
    prev_cart_pos = cart_pos;
    prev_theta1 = theta1;
    prev_theta2 = theta2;

    // 4. Safety Boundary Checks
    if (digitalRead(PIN_ESTOP_INPUT) == LOW) {
      estop_active = true;
      estop_cause = "Hardware ESTOP Switch Pressed";
    }
    else if (abs(cart_pos) > LIMIT_CART_POS_M) {
      estop_active = true;
      estop_cause = "Hardware limit exceeded: Cart position too large";
    }

    // Toggle status LED depending on state
    if (estop_active) {
      digitalWrite(PIN_STATUS_LED, (millis() / 250) % 2 == 0 ? HIGH : LOW); // Flash LED on ESTOP
    } else {
      digitalWrite(PIN_STATUS_LED, HIGH);
    }

    // 5. Read Control Messages from Serial
    float target_voltage = 0.0;
    while (Serial.available()) {
      char c = Serial.read();
      if (c == '\n') {
        input_buffer.trim();
        if (input_buffer.startsWith("CMD,")) {
          String val_str = input_buffer.substring(4);
          target_voltage = val_str.toFloat();
        }
        else if (input_buffer == "RESET") {
          estop_active = false;
          estop_cause = "";
        }
        input_buffer = "";
      } else {
        input_buffer += c;
      }
    }

    // 6. Actuate Motor
    write_motor_output(target_voltage);

    // 7. Send Telemetry Packet (6-state format: timestamp, theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel)
    Serial.print(current_time);
    Serial.print(",");
    Serial.print(theta1, 4);
    Serial.print(",");
    Serial.print(theta2, 4);
    Serial.print(",");
    Serial.print(theta1_dot, 4);
    Serial.print(",");
    Serial.print(theta2_dot, 4);
    Serial.print(",");
    Serial.print(cart_pos, 4);
    Serial.print(",");
    Serial.println(cart_vel, 4);
  }
}
