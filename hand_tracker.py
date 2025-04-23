import cv2
import mediapipe as mp
import numpy as np

class HandTracker:
    def __init__(self, static_image_mode=False, max_num_hands=2, 
                 min_detection_confidence=0.5, min_tracking_confidence=0.5):
        """
        Initialize the hand tracker with MediaPipe Hands.
        
        Parameters:
            static_image_mode: Whether to treat images as static or video frames
            max_num_hands: Maximum number of hands to detect
            min_detection_confidence: Minimum confidence for hand detection
            min_tracking_confidence: Minimum confidence for hand tracking
        """
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=static_image_mode,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

    @staticmethod
    def calculate_angle(a, b, c):
        """
        Calculate the angle between three points (in degrees).
        
        Parameters:
            a, b, c: Points as [x,y] or [x,y,z] coordinates
        Returns:
            Angle in degrees between vectors ba and bc
        """
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)
        
        radians = np.arccos(np.clip(
            np.dot(a-b, c-b) / (np.linalg.norm(a-b) * np.linalg.norm(c-b)), 
            -1.0, 1.0
        ))
        return np.degrees(radians)

    @staticmethod
    def calculate_distance(a, b):
        """
        Calculate Euclidean distance between two points.
        
        Parameters:
            a, b: Points as [x,y] or [x,y,z] coordinates
        Returns:
            Euclidean distance between points
        """
        return np.linalg.norm(np.array(a) - np.array(b))

    def process_frame(self, frame, draw_landmarks=True):
        """
        Process a frame to detect hand landmarks.
        
        Parameters:
            frame: Input BGR image frame
            draw_landmarks: Whether to draw landmarks on output frame
        Returns:
            results: MediaPipe hands results
            output_frame: Frame with landmarks drawn (if requested)
        """
        # Convert the BGR image to RGB
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        
        # Process the image
        results = self.hands.process(image)
        
        # Convert back to BGR for drawing
        image.flags.writeable = True
        output_frame = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        # Draw hand landmarks if requested
        if draw_landmarks and results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    output_frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
        
        return results, output_frame

    def get_landmark_positions(self, results, frame_width, frame_height):
        """
        Get normalized landmark positions converted to pixel coordinates.
        
        Parameters:
            results: MediaPipe hands results
            frame_width: Width of the frame
            frame_height: Height of the frame
        Returns:
            List of lists containing landmark positions in pixel coordinates,
            or None if no hands detected
        """
        if not results.multi_hand_landmarks:
            return None
            
        landmarks = []
        for hand_landmarks in results.multi_hand_landmarks:
            hand = []
            for landmark in hand_landmarks.landmark:
                x = min(int(landmark.x * frame_width), frame_width - 1)
                y = min(int(landmark.y * frame_height), frame_height - 1)
                z = landmark.z
                hand.append([x, y, z])
            landmarks.append(hand)
            
        return landmarks

    def is_hand_closed(self, landmarks, threshold=0.8):
        """
        Detect if hand is closed based on finger tip distances to palm.
        
        Parameters:
            landmarks: List of landmark positions
            threshold: Ratio of fingers that need to be closed (0-1)
        Returns:
            True if hand is considered closed, False otherwise
        """
        if not landmarks or len(landmarks) < 21:
            return False
            
        # Palm base (wrist)
        palm_base = landmarks[0]
        
        # Finger tips (index, middle, ring, pinky)
        tips = [landmarks[i] for i in [8, 12, 16, 20]]
        
        # Calculate distances from tips to palm base
        distances = [self.calculate_distance(tip, palm_base) for tip in tips]
        
        # Reference distance (length from wrist to middle finger base)
        ref_distance = self.calculate_distance(
            landmarks[0], landmarks[9]  # Wrist to middle finger MCP
        )
        
        # Normalize distances
        normalized = [d / ref_distance for d in distances]
        
        # Count how many fingers are closed (normalized distance < 1.0)
        closed_fingers = sum(1 for d in normalized if d < 1.0)
        
        return closed_fingers >= threshold * len(tips)

    def release(self):
        """Release resources."""
        self.hands.close()

# Example usage
if __name__ == "__main__":
    tracker = HandTracker()
    cap = cv2.VideoCapture(0)
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.flip(frame, 1)
        results, output_frame = tracker.process_frame(frame)
        
        if results.multi_hand_landmarks:
            landmarks = tracker.get_landmark_positions(results, frame.shape[1], frame.shape[0])
            
            if landmarks:
                # Example: Calculate angle between index, wrist, and pinky
                angle = tracker.calculate_angle(
                    landmarks[0][8],  # Index tip
                    landmarks[0][0],  # Wrist
                    landmarks[0][20]   # Pinky tip
                )
                
                cv2.putText(output_frame, f"Angle: {angle:.1f}°", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Check if hand is closed
                if tracker.is_hand_closed(landmarks[0]):
                    cv2.putText(output_frame, "HAND CLOSED", (10, 70),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        cv2.imshow('Hand Tracking', output_frame)
        
        if cv2.waitKey(10) & 0xFF == 27:  # ESC key
            break
    
    cap.release()
    tracker.release()
    cv2.destroyAllWindows()