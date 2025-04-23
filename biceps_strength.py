import cv2
import mediapipe as mp
import numpy as np

# Initialize MediaPipe pose
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

def calculate_angle(a, b, c):
    """Calculate angle between three points: elbow (b), shoulder (a), wrist (c)"""
    a = np.array(a)  # Shoulder
    b = np.array(b)  # Elbow
    c = np.array(c)  # Wrist

    radians = np.arccos(
        np.clip(np.dot((a - b), (c - b)) / 
                (np.linalg.norm(a - b) * np.linalg.norm(c - b)), -1.0, 1.0)
    )
    angle = np.degrees(radians)
    return angle

cap = cv2.VideoCapture(0)

with mp_pose.Pose(min_detection_confidence=0.5,
                  min_tracking_confidence=0.5) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Recolor the frame
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False

        # Make detection
        results = pose.process(image)

        # Recolor back to BGR
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        try:
            landmarks = results.pose_landmarks.landmark

            # Get coordinates for right arm
            shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                        landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
            elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                     landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
            wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                     landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]

            angle = calculate_angle(shoulder, elbow, wrist)

            # Convert angle to "completion" scale (180 = arm down, 40 = arm up)
            percent_complete = np.interp(angle,  (40, 90), (100, 0))
            percent_complete = max(0, min(100, percent_complete))

            # Show angle and scale
            cv2.putText(image, f'Angle: {int(angle)} deg', (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(image, f'Scale: {int(percent_complete)}%', (50, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # If complete
            if percent_complete >= 98:
                cv2.putText(image, 'Range Complete!', (50, 130),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

        except:
            pass

        # Draw pose landmarks
        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        cv2.imshow('Bicep Curl Tracker', image)

        if cv2.waitKey(10) & 0xFF == 27:  # Press ESC to exit
            break

cap.release()
cv2.destroyAllWindows()

