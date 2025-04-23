import pygame
import cv2
import mediapipe as mp
import math
import random
import time
import os

class ForearmBalloonGame:
    def __init__(self):
        pygame.init()
        self.setup_game()
        self.hands = mp.solutions.hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.cap = cv2.VideoCapture(0)
        self.load_best_score()
        
    def setup_game(self):
        # Game window setup
        self.game_width, self.game_height = 600, 500
        self.cam_width, self.cam_height = 400, 300
        self.screen_width = self.game_width + self.cam_width
        self.screen_height = max(self.game_height, self.cam_height)
        
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Forearm Balloon Game")
        
        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.BLUE = (100, 149, 237)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.YELLOW = (255, 255, 0)
        
        # Balloon properties
        self.balloon_radius = 30
        self.max_radius = 100
        self.min_radius = 20
        self.inflation_rate = 0.5
        self.deflation_rate = 0.2
        self.balloon_pos = (self.game_width // 2, self.game_height // 2)
        self.balloon_color = random.choice([
            (231, 76, 60), (35, 155, 86), (155, 89, 182),
            (243, 156, 18), (244, 208, 63), (46, 134, 193)
        ])
        
        # Game state
        self.score = 0
        self.best_score = 0
        self.game_active = True
        self.paused = False
        self.burst_animation = False
        self.burst_time = 0
        
        # Fonts
        self.font = pygame.font.SysFont('Arial', 24)
        self.big_font = pygame.font.SysFont('Arial', 48)
        
    def load_best_score(self):
        if os.path.exists('balloon_best_score.txt'):
            with open('balloon_best_score.txt', 'r') as f:
                try:
                    self.best_score = int(f.read())
                except:
                    self.best_score = 0
        else:
            self.best_score = 0
            
    def save_best_score(self):
        with open('balloon_best_score.txt', 'w') as f:
            f.write(str(self.best_score))
    
    def is_hand_closed(self, landmarks):
        """Check if hand is closed based on finger tip positions"""
        tip_ids = [8, 12, 16, 20]  # Finger tip landmarks (index to pinky)
        folded_fingers = 0
        
        for tip in tip_ids:
            if landmarks[tip].y > landmarks[tip - 2].y:  # Tip below PIP joint
                folded_fingers += 1
                
        return folded_fingers >= 3  # At least 3 fingers folded
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.paused = not self.paused
                elif event.key == pygame.K_r:
                    self.reset_game()
                elif event.key == pygame.K_q:
                    return False
        return True
    
    def update(self):
        if self.paused or not self.game_active or self.burst_animation:
            return
            
        # Process webcam frame
        ret, frame = self.cap.read()
        if not ret:
            return
            
        frame = cv2.flip(frame, 1)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(image)
        
        hand_closed = False
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                if self.is_hand_closed(hand_landmarks.landmark):
                    hand_closed = True
                    break
        
        # Update balloon size based on hand state
        if hand_closed:
            self.balloon_radius += self.inflation_rate
        else:
            self.balloon_radius -= self.deflation_rate
            
        # Keep balloon within bounds
        self.balloon_radius = max(self.min_radius, min(self.max_radius, self.balloon_radius))
        
        # Check for burst
        if self.balloon_radius >= self.max_radius:
            self.burst_animation = True
            self.burst_time = time.time()
            self.score += 1
            if self.score > self.best_score:
                self.best_score = self.score
                self.save_best_score()
    
    def draw(self):
        self.screen.fill(self.BLACK)
        
        # Draw webcam feed
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (self.cam_width, self.cam_height))
                frame = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
                self.screen.blit(frame, (self.game_width, 0))
        
        # Draw game area border
        pygame.draw.rect(self.screen, self.WHITE, (0, 0, self.game_width, self.game_height), 2)
        
        # Draw balloon or burst effect
        if self.burst_animation:
            current_time = time.time()
            if current_time - self.burst_time < 0.5:  # Burst animation duration
                self.draw_burst_effect()
            else:
                self.burst_animation = False
                self.balloon_radius = self.min_radius
                self.balloon_color = random.choice([
                    (231, 76, 60), (35, 155, 86), (155, 89, 182),
                    (243, 156, 18), (244, 208, 63), (46, 134, 193)
                ])
        else:
            self.draw_balloon()
        
        # Draw score
        score_text = self.font.render(f"Score: {self.score}", True, self.WHITE)
        best_text = self.font.render(f"Best: {self.best_score}", True, self.WHITE)
        self.screen.blit(score_text, (20, 20))
        self.screen.blit(best_text, (20, 50))
        
        # Draw instructions
        instructions = self.font.render("Close hand to inflate, open to deflate", True, self.WHITE)
        self.screen.blit(instructions, (self.game_width // 2 - instructions.get_width() // 2, 20))
        
        controls = self.font.render("P: Pause  R: Reset  Q: Quit", True, self.WHITE)
        self.screen.blit(controls, (self.game_width // 2 - controls.get_width() // 2, self.game_height - 30))
        
        # Draw pause message if paused
        if self.paused:
            pause_text = self.big_font.render("PAUSED", True, self.WHITE)
            self.screen.blit(pause_text, 
                           (self.game_width // 2 - pause_text.get_width() // 2, 
                            self.game_height // 2 - pause_text.get_height() // 2))
        
        pygame.display.flip()
    
    def draw_balloon(self):
        """Draw the balloon with string"""
        # Balloon body
        pygame.draw.circle(self.screen, self.balloon_color, 
                          self.balloon_pos, int(self.balloon_radius))
        
        # Balloon highlight
        highlight_pos = (
            self.balloon_pos[0] - self.balloon_radius // 3,
            self.balloon_pos[1] - self.balloon_radius // 3
        )
        pygame.draw.circle(self.screen, self.WHITE, highlight_pos, 
                          int(self.balloon_radius // 4))
        
        # Balloon string
        string_end = (
            self.balloon_pos[0],
            self.balloon_pos[1] + self.balloon_radius + 30
        )
        pygame.draw.line(self.screen, self.BLACK, self.balloon_pos, string_end, 2)
        
        # Percentage text
        percent = int(((self.balloon_radius - self.min_radius) / 
                      (self.max_radius - self.min_radius)) * 100)
        percent_text = self.font.render(f"{percent}%", True, self.BLACK)
        self.screen.blit(percent_text, 
                        (self.balloon_pos[0] - percent_text.get_width() // 2,
                         self.balloon_pos[1] - percent_text.get_height() // 2))
    
    def draw_burst_effect(self):
        """Draw balloon burst animation"""
        for i in range(12):
            angle = i * (math.pi / 6)
            end_x = int(self.balloon_pos[0] + math.cos(angle) * 50)
            end_y = int(self.balloon_pos[1] + math.sin(angle) * 50)
            pygame.draw.line(self.screen, self.balloon_color, 
                            self.balloon_pos, (end_x, end_y), 5)
        
        burst_text = self.big_font.render("POP!", True, self.RED)
        self.screen.blit(burst_text, 
                        (self.balloon_pos[0] - burst_text.get_width() // 2,
                         self.balloon_pos[1] - burst_text.get_height() // 2))
    
    def reset_game(self):
        self.score = 0
        self.balloon_radius = self.min_radius
        self.balloon_color = random.choice([
            (231, 76, 60), (35, 155, 86), (155, 89, 182),
            (243, 156, 18), (244, 208, 63), (46, 134, 193)
        ])
        self.burst_animation = False
        self.game_active = True
    
    def cleanup(self):
        self.cap.release()
        pygame.quit()
        cv2.destroyAllWindows()
    
    def run(self):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            clock.tick(60)
        
        self.cleanup()

if __name__ == "__main__":
    game = ForearmBalloonGame()
    game.run()