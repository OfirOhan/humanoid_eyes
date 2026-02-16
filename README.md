# Nico - The AI Animatronic Robot

Nico is a voice-activated, computer-vision-powered animatronic robot head. It uses **Deep Learning** to detect human emotions and mimic them, and **Google Speech Recognition** to understand voice commands in real-time.

## 🧠 Features
* **Emotion Mimicry:** Detects if you are Happy, Sad, or Angry and physically mimics the expression.
* **Voice Control:** Understands natural language commands (e.g., "Nico, look right").
* **Face Tracking:** Follows your face in real-time using servos.
* **Fuzzy Logic:** Understands commands even if they aren't spoken perfectly (e.g., "Imitate" vs "Emulate").

## 🛠️ Hardware Requirements
* **Microcontroller:** Arduino Uno / Nano / Mega
* **Driver:** PCA9685 16-Channel PWM Servo Driver
* **Motors:** 6x MG90S Micro Servos (or equivalent)
* **Power:** 5V 2A Power Supply (Phone Charger or Battery)
* **Sensors:** Webcam (Video), Microphone (Audio)

### 🔌 Wiring Diagram (PCA9685)
| Servo Name | Channel (Pin) | Description |
| :--- | :---: | :--- |
| **Right Eyelid Lower** | 0 | Bottom lid, Right Eye |
| **Right Eyelid Upper** | 3 | Top lid, Right Eye |
| **Eyes Y-Axis** | 6 | Up / Down Movement |
| **Eyes X-Axis** | 8 | Left / Right Movement |
| **Left Eyelid Upper** | 11 | Top lid, Left Eye |
| **Left Eyelid Lower** | 15 | Bottom lid, Left Eye |

> **Note:** The PCA9685 connects to Arduino via I2C (SDA -> A4, SCL -> A5 on Uno).

## 💻 Installation

### 1. Arduino Setup
1.  Install the **Adafruit PWM Servo Driver** library via Library Manager.
2.  Upload the `nico_arduino.ino` sketch to your board.
3.  **Close the Arduino IDE** (otherwise Python cannot connect).

### 2. Python Setup
1.  Install Python 3.8 - 3.10.
2.  Install dependencies:
    ```bash
    pip install opencv-python pyserial SpeechRecognition pyaudio torch facial-emotion-recognition
    ```
3.  Connect your Arduino and check the **COM Port** (Update `ARDUINO_PORT` in `nico_brain.py`).

## 🚀 How to Run
Run the main Python script:
```bash
python emotion_recognition.py