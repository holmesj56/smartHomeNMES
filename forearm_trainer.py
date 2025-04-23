import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import os

class ForearmTrainer:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.data = []
        self.labels = []
        self.label_names = {
            0: "0% (Fully Open)",
            25: "25%",
            50: "50%",
            75: "75%",
            100: "100% (Fully Closed)"
        }
        self.current_label = "No label selected"
        self.cap = cv2.VideoCapture(0)
        
    def extract_features(self, landmarks):
        """Convert hand landmarks to feature vector"""
        features = []
        for landmark in landmarks.landmark:
            features.extend([landmark.x, landmark.y, landmark.z])
        return np.array(features)
    
    def collect_data(self, samples_per_label=20):
        print("\nForearm Trainer - Data Collection Mode")
        print("Press keys to capture samples:")
        print("0: Fully Open (0%)")
        print("1: 25% Closed")
        print("2: 50% Closed")
        print("3: 75% Closed")
        print("4: Fully Closed (100%)")
        print("s: Save data")
        print("q: Quit without saving")
        
        collecting = True
        while collecting and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                continue
                
            frame = cv2.flip(frame, 1)
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(image)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_drawing.draw_landmarks(
                        image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
            
            # Display instructions and status
            cv2.putText(image, f"Current label: {self.current_label}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(image, f"Samples collected: {len(self.data)}", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(image, "Press 0-4 to label, s to save, q to quit", (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow('Forearm Trainer - Data Collection', image)
            
            key = cv2.waitKey(10) & 0xFF
            
            if key == ord('q'):  # Quit
                collecting = False
                self.data = []
                self.labels = []
            elif key == ord('s'):  # Save
                if len(self.data) > 0:
                    self.save_data()
                    collecting = False
                else:
                    print("No data to save!")
            elif ord('0') <= key <= ord('4'):  # Label selection
                label = (key - ord('0')) * 25
                self.current_label = self.label_names[label]
                
                if results.multi_hand_landmarks:
                    landmarks = results.multi_hand_landmarks[0]
                    features = self.extract_features(landmarks)
                    self.data.append(features)
                    self.labels.append(label)
                    print(f"Collected sample for {self.current_label}")
            
        cv2.destroyAllWindows()
    
    def save_data(self):
        if len(self.data) == 0:
            print("No data to save!")
            return
        
        # Create DataFrame
        df = pd.DataFrame(self.data)
        df['label'] = self.labels
        
        # Save to file
        filename = 'forearm_data.csv'
        if os.path.exists(filename):
            # Append to existing file
            existing_df = pd.read_csv(filename)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            combined_df.to_csv(filename, index=False)
            print(f"Appended {len(df)} samples to {filename}")
        else:
            # Create new file
            df.to_csv(filename, index=False)
            print(f"Saved {len(df)} samples to {filename}")
        
        self.data = []
        self.labels = []
    
    def run(self):
        print("Starting Forearm Trainer...")
        self.collect_data()
        self.cap.release()

if __name__ == "__main__":
    trainer = ForearmTrainer()
    trainer.run()