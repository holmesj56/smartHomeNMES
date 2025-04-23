import cv2
import mediapipe as mp
import numpy as np
import pygame
import random

# Initialize pygame
pygame.init()
GAME_WIDTH, GAME_HEIGHT = 640, 480
CAM_WIDTH, CAM_HEIGHT = 640, 480
SCREEN_WIDTH = GAME_WIDTH + CAM_WIDTH
SCREEN_HEIGHT = max(GAME_HEIGHT, CAM_HEIGHT)
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Arm-Controlled Pong")
clock = pygame.time.Clock()

# Game elements
PADDLE_WIDTH, PADDLE_HEIGHT = 15, 100
BALL_SIZE = 15
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

class Paddle:
    def __init__(self, x, y, color):
        self.rect = pygame.Rect(x, y, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.color = color
    
    def set_position(self, percent):
        """0% = bottom, 100% = top"""
        y_pos = GAME_HEIGHT - PADDLE_HEIGHT - (percent/100 * (GAME_HEIGHT - PADDLE_HEIGHT))
        self.rect.y = max(0, min(GAME_HEIGHT - PADDLE_HEIGHT, y_pos))
    
    def draw(self):
        pygame.draw.rect(screen, self.color, self.rect)

class Ball:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.rect = pygame.Rect(GAME_WIDTH//2, GAME_HEIGHT//2, BALL_SIZE, BALL_SIZE)
        self.dx = 7 * random.choice([1, -1])
        self.dy = 7 * random.choice([1, -1])
    
    def move(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        
        # Wall collision
        if self.rect.top <= 0 or self.rect.bottom >= GAME_HEIGHT:
            self.dy *= -1
    
    def draw(self):
        pygame.draw.rect(screen, WHITE, self.rect)

# Initialize game objects
player_paddle = Paddle(GAME_WIDTH - 50, GAME_HEIGHT//2, GREEN)
ai_paddle = Paddle(30, GAME_HEIGHT//2, RED)
ball = Ball()

# Game state
game_active = True
paused = False
player_score = 0
ai_score = 0
font = pygame.font.SysFont('Arial', 30)
large_font = pygame.font.SysFont('Arial', 50)

# MediaPipe setup
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arccos(np.clip(np.dot(a-b, c-b)/(np.linalg.norm(a-b)*np.linalg.norm(c-b)), -1, 1))
    return np.degrees(radians)

cap = cv2.VideoCapture(0)

def draw_button(text, x, y, width, height, inactive_color, active_color):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    
    if x < mouse[0] < x + width and y < mouse[1] < y + height:
        pygame.draw.rect(screen, active_color, (x, y, width, height))
        if click[0] == 1:
            return True
    else:
        pygame.draw.rect(screen, inactive_color, (x, y, width, height))
    
    text_surf = font.render(text, True, BLACK)
    text_rect = text_surf.get_rect(center=(x + width/2, y + height/2))
    screen.blit(text_surf, text_rect)
    return False

running = True
while running:
    # Process webcam frame
    ret, frame = cap.read()
    if ret:
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image)
        
        if results.pose_landmarks and not paused and game_active:
            landmarks = results.pose_landmarks.landmark
            try:
                # Get right arm landmarks
                shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, 
                           landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                         landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
                wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                         landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
                
                angle = calculate_angle(shoulder, elbow, wrist)
                percent_complete = np.interp(angle, [40, 90], [100, 0])
                percent_complete = max(0, min(100, percent_complete))
                player_paddle.set_position(percent_complete)
                
                # Display angle info on camera feed
                cv2.putText(frame, f"Angle: {int(angle)}°", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, f"Completion: {int(percent_complete)}%", (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
            except Exception as e:
                pass
        
        # Convert camera frame to pygame surface
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = pygame.surfarray.make_surface(frame)
        frame = pygame.transform.flip(frame, True, False)
    
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # Clear screen
    screen.fill(BLACK)
    
    # Draw camera feed on the right side
    if ret:
        screen.blit(frame, (GAME_WIDTH, 0))
    
    # Draw game elements on the left side
    if game_active and not paused:
        # AI paddle movement
        target_y = ball.rect.centery - PADDLE_HEIGHT//2
        ai_speed = 5
        if abs(ai_paddle.rect.centery - ball.rect.centery) > ai_speed:
            if ai_paddle.rect.centery < ball.rect.centery:
                ai_paddle.rect.y += ai_speed
            else:
                ai_paddle.rect.y -= ai_speed
        
        # Ball movement
        ball.move()
        
        # Paddle collisions
        if ball.rect.colliderect(player_paddle.rect):
            ball.dx = -abs(ball.dx)
            player_score += 1
        
        if ball.rect.colliderect(ai_paddle.rect):
            ball.dx = abs(ball.dx)
            ai_score += 1
        
        # Scoring
        if ball.rect.left <= 0:
            ball.reset()
        elif ball.rect.right >= GAME_WIDTH:
            ball.reset()
    
    # Draw game elements
    player_paddle.draw()
    ai_paddle.draw()
    ball.draw()
    
    # Draw scores
    player_text = font.render(f"Player: {player_score}", True, GREEN)
    ai_text = font.render(f"AI: {ai_score}", True, RED)
    screen.blit(player_text, (GAME_WIDTH - 150, 20))
    screen.blit(ai_text, (50, 20))
    
    # Draw buttons
    if draw_button("Pause" if not paused else "Resume", 20, GAME_HEIGHT - 50, 100, 40, WHITE, (200, 200, 200)):
        paused = not paused
    
    if draw_button("Restart", 140, GAME_HEIGHT - 50, 100, 40, WHITE, (200, 200, 200)):
        player_score = 0
        ai_score = 0
        ball.reset()
        paused = False
        game_active = True
    
    if draw_button("Quit", 260, GAME_HEIGHT - 50, 100, 40, WHITE, (200, 200, 200)):
        running = False
    
    # Draw pause message
    if paused:
        pause_text = large_font.render("PAUSED", True, WHITE)
        screen.blit(pause_text, (GAME_WIDTH//2 - pause_text.get_width()//2, 
                               GAME_HEIGHT//2 - pause_text.get_height()//2))
    
    pygame.display.flip()
    clock.tick(60)

cap.release()
cv2.destroyAllWindows()
pygame.quit()