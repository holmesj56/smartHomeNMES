import cv2
import mediapipe as mp
import numpy as np
import serial
import time

# SERIAL Setup
arduino_port = 'COM12'  # Set your Arduino COM port
baud_rate = 19200
ser = serial.Serial(arduino_port, baudrate=baud_rate, timeout=1)
# Wait and flush startup logs
time.sleep(2)
ser.reset_input_buffer()

# Initialize MediaPipe pose
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# Intensity control parameters
current_intensity = 0
max_intensity = 255
intensity_step = max_intensity // 10  # 10% increments
channel_active = False

# Motion tracking state
last_angle = None
expecting_up = True
hold_start = None
full_hold_start = None

# Detection thresholds
small_thresh = 1.5      # degrees for stuck detection
hold_time = 3           # seconds to hold before boost
drop_thresh = 10       # percent drop triggers boost
full_min = 95           # percent for full contraction
rest_max = 5            # percent for rest position

# Helper: send command, wait for specific ack, ignore other logs
def send_cmd(cmd, timeout=1.0):
    # flush old data
    ser.reset_input_buffer()
    ser.write(f"{cmd}\r\n".encode())
    ser.flush()
    print(f">>> Sent: {cmd}")
    start = time.time()
    expected = None
    if cmd == 'u':
        expected = 'PWM Increased'
    elif cmd == 'j':
        expected = 'PWM Decreased'
    elif cmd == '1':
        # activation toggles, expect either active or inactive
        expected = 'Channel 1'
    while time.time() - start < timeout:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            continue
        print(f"<<< Arduino: {line}")
        if expected and expected in line:
            return line
    print(f"!!! No ack for '{cmd}' within {timeout}s")
    return None

# Channel control
def activate_channel():
    global channel_active
    if not channel_active:
        ack = send_cmd('1')
        if ack and 'active' in ack:
            channel_active = True
        else:
            print('!!! Activation failed')

def deactivate_channel():
    global channel_active
    if channel_active:
        ack = send_cmd('1')
        if ack and 'inactive' in ack:
            channel_active = False
        else:
            print('!!! Deactivation failed')

# Intensity commands
def increase_intensity():
    global current_intensity
    activate_channel()
    if current_intensity < max_intensity:
        ack = send_cmd('u')
        if ack:
            current_intensity = min(current_intensity + intensity_step, max_intensity)
            print(f"*** Intensity: {int((current_intensity/max_intensity)*100)}%")
        else:
            print('!!! Increase not acknowledged')

def reset_intensity():
    global current_intensity
    while current_intensity > 0:
        ack = send_cmd('j')
        if ack:
            current_intensity = max(current_intensity - intensity_step, 0)
            print(f"*** Intensity: {int((current_intensity/max_intensity)*100)}%")
        else:
            print('!!! Decrease not acknowledged')
            break
    deactivate_channel()
    print('*** Channel off')

# Angle calculation
def calc_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    cosv = np.dot(a-b, c-b) / (np.linalg.norm(a-b)*np.linalg.norm(c-b))
    cosv = np.clip(cosv, -1.0, 1.0)
    return np.degrees(np.arccos(cosv))

# Main loop
cap = cv2.VideoCapture(0)
with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img.flags.writeable = False
        res = pose.process(img)
        img.flags.writeable = True
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        try:
            lm = res.pose_landmarks.landmark
            s = [lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
            e = [lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x, lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
            w = [lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].x, lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
            angle = calc_angle(s, e, w)
            pct = np.interp(angle, (40, 90), (100, 0))
            pct = np.clip(pct, 0, 100)

            if last_angle is not None:
                delta = pct - last_angle
                if expecting_up:
                    if delta < -drop_thresh:
                        print('>>> Early drop')
                        increase_intensity()
                    if abs(delta) < small_thresh:
                        if hold_start is None:
                            hold_start = time.time()
                        elif time.time() - hold_start > hold_time:
                            print('>>> Stuck hold')
                            increase_intensity()
                            hold_start = None
                    else:
                        hold_start = None
                    if pct >= full_min:
                        if full_hold_start is None:
                            full_hold_start = time.time()
                        elif time.time() - full_hold_start > hold_time:
                            print('>>> Full reached')
                            reset_intensity()
                            expecting_up = False
                            full_hold_start = None
                else:
                    if pct <= rest_max:
                        print('>>> Rest reached')
                        expecting_up = True
            last_angle = pct

            phase = 'Move Up' if expecting_up else 'Move Down'
            col = (0,255,0) if expecting_up else (0,0,255)
            cv2.putText(img, phase, (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, col, 3)
            cv2.putText(img, f'{int(pct)}%', (50,100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
            cv2.putText(img, f'I:{int((current_intensity/max_intensity)*100)}%', (50,150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,255), 2)

        except Exception as e:
            print('Error:', e)

        mp_drawing.draw_landmarks(img, res.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        cv2.imshow('Trainer', img)
        if cv2.waitKey(10) & 0xFF == 27:
            break

cap.release()
ser.close()
cv2.destroyAllWindows()
