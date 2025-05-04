## Hi there 👋
# Home-Based Smart NMES Device

A collaborative project with Barrow Neurological Institute to deliver a game-driven, home-based NeuroMuscular Electrical Stimulation (NMES) system. By combining real-time computer vision, adaptive stimulation control, and interactive games, our platform makes rehabilitation engaging, safe, and effective.

---

## 📑 Table of Contents
1. [Overview](#overview)  
2. [Features & Benefits](#features--benefits)  
3. [Hardware Architecture](#hardware-architecture)  
4. [Software Architecture](#software-architecture)  
5. [Working Principles](#working-principles)  
   - [Motion Tracking Pipeline](#motion-tracking-pipeline)  
   - [NMES Control Logic](#nmes-control-logic)  
6. [Interactive Game Modes](#interactive-game-modes)  
7. [Usage Instructions](#usage-instructions)  
8. [Contributing](#contributing)  
9. [License](#license)  

---

## Overview
The Smart NMES platform integrates:  
- A commercial NMES stimulator (manual max intensity safeguard)  
- An Arduino Nano–based PCB (MOSFETs, potentiometer/digital potentiometer)  
- A Bluetooth (or USB) serial link  
- A USB camera for computer vision  
- A Python application using OpenCV, MediaPipe & Pygame  

It guides users through therapeutic exercises via three games, automatically increasing stimulation when motion stalls and resetting upon full range completion.

---

## Features & Benefits
| Feature                          | Benefit                                                  |
|----------------------------------|----------------------------------------------------------|
| Real-time pose & hand tracking  | Accurate feedback in any user orientation                |
| Adaptive intensity control       | Personalized assistance exactly when needed              |
| Multiple game modes              | Keeps therapy engaging & varied                          |
| Wireless communication           | Flexible setup without tangled cables                    |
| Manual max intensity safeguard   | Prevents overstimulation                                 |
| Visual feedback & logging        | Enables progress tracking and data analysis              |

---

## Hardware Architecture
1. **NMES Stimulator** (commercial)  
   - Pre‑set to a safe maximum manual intensity.  
2. **Arduino Nano & Custom PCB**  
   - Drives MOSFETs and potentiometer (or digital pot).  
   - Receives `u`/`j` commands to increase/decrease intensity.  
3. **Bluetooth Module**  
   - Serial data link between PC and Arduino.  
4. **USB Webcam**  
   - Captures live video for motion tracking.  

---

## Software Architecture
- **app.py (Python 3.x)**  
  - **OpenCV**: Frame capture and preprocessing.  
  - **MediaPipe**: Pose and hand landmark detection.  
  - **Pygame**: Game rendering and UI.  
  - **PySerial**: Serial communication with Arduino.  

**Flow:**  
1. **Init**: Load libraries, open serial port, initialize models.  
2. **Loop**:  
   - Grab frame → detect landmarks → compute angles.  
   - Evaluate against target range and timing.  
   - Decide to send `'u'` (up) or `'j'` (down) commands.  
   - Render visuals & intensity gauge.  
3. **Exit**: Close camera, serial port, and windows.  

---

## Working Principles

### Motion Tracking Pipeline
1. **Landmark Detection**  
   - **MediaPipe Pose** for arm flexion/extension.  
   - **MediaPipe Hands** for finger flexion/extension.  
2. **Angle Computation**  
   - Calculate joint angles in degrees (elbow or PIP/DIP joints).  
3. **Stuck & Full-Range Detection**  
   - Detect minimal angle change over a set interval (e.g., 3s).  
   - Lock out stimulation on downward movement until reset.  

### NMES Control Logic
- **Intensity Levels**: 0% → 100% in 10% increments.  
- **Increase**: If motion stalls below target range for >3s or moves against gravity.  
- **Hold**: Maintain current intensity until user resumes motion.  
- **Reset**: Upon reaching full flexion/extension (100% range).  

---

## Interactive Game Modes

### 1. Range of Motion Game
Guide the user through full arm flexion and extension cycles. Stalled motion triggers gradual intensity ramp‑up.

### 2. Ping Pong Game
Deflect a green paddle to hit a ball; a predictive blue marker shows the target. Missing slows the ball and increases stimulation until correct position is reached.

### 3. Balloon Filling Game
Perform finger flexion/extension to inflate a virtual balloon. If inflation stops, NMES intensity increases until motion resumes.

> **Demo Videos:**  
> - [Game 1: Range of Motion](https://youtu.be/y0tVo8uiLJE)  
> - [Game 2: Ping Pong](https://youtu.be/1X4XvW03p7I)  
> - [Game 3: Balloon Filling](https://youtu.be/d7rLdNfFJ88)  

---

## Usage Instructions
1. Set NMES device to a safe manual max intensity.  
2. Pair Arduino’s Bluetooth (or connect via USB).  
3. Install Python dependencies:  
   ```bash
   pip install -r requirements.txt
reference : https://github.com/PedroLopes/openEMSstim
https://bitbucket.org/MaxPfeiffer/letyourbodymove/wiki/Home/ToolKitArduinoSoftware
