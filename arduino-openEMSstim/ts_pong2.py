import cv2
import mediapipe as mp
import numpy as np
import pygame
import random
import serial
import time

# Serial setup for NMES device
try:
    stim_serial = serial.Serial('COM12', 19200, timeout=1)
    time.sleep(2)
    print("Connected to NMES device.")
except serial.SerialException as e:
    stim_serial = None
    print(f"Serial connection failed: {e}")

# stimulation state & PWM intensity variables
stimulating = False
current_pwm = 128
pwm_step = 10
min_pwm = 0
max_pwm = 255

def start_stimulation():
    global stimulating
    if stim_serial and not stimulating:
        stim_serial.write(b'1')    # toggle channel on
        stimulating = True
        print("Stimulation STARTED")

def stop_stimulation():
    global stimulating, current_pwm
    if stim_serial and stimulating:
        stim_serial.write(b'1')    # toggle channel off
        stimulating = False
        print("Stimulation STOPPED")
        # reset our Python-side intensity
        current_pwm = 128

# Pygame setup
pygame.init()
GAME_WIDTH, GAME_HEIGHT = 640, 480
CAM_WIDTH, CAM_HEIGHT = 640, 480
SCREEN_WIDTH = GAME_WIDTH + CAM_WIDTH
SCREEN_HEIGHT = max(GAME_HEIGHT, CAM_HEIGHT)
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Arm-Controlled Pong with NMES")
clock = pygame.time.Clock()

# Game elements
PADDLE_WIDTH, PADDLE_HEIGHT = 15, 100
BALL_SIZE = 15
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED   = (255,   0,   0)
GREEN = (  0, 255,   0)

class Paddle:
    def __init__(self, x, y, color):
        self.rect = pygame.Rect(x, y, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.color = color

    def set_position(self, percent):
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
        if self.rect.top <= 0 or self.rect.bottom >= GAME_HEIGHT:
            self.dy *= -1

    def draw(self):
        pygame.draw.rect(screen, WHITE, self.rect)

# Initialize game objects
player_paddle = Paddle(GAME_WIDTH - 50, GAME_HEIGHT//2, GREEN)
ai_paddle     = Paddle(30,            GAME_HEIGHT//2, RED)
ball          = Ball()

game_active = True
paused = False
player_score = 0
ai_score     = 0
font     = pygame.font.SysFont('Arial', 30)
large_font = pygame.font.SysFont('Arial', 50)

# MediaPipe Pose
mp_pose    = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose       = mp_pose.Pose(min_detection_confidence=0.5,
                         min_tracking_confidence=0.5)

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arccos(np.clip(
        np.dot(a-b, c-b)/(
            np.linalg.norm(a-b)*np.linalg.norm(c-b)
        ), -1, 1
    ))
    return np.degrees(radians)

cap = cv2.VideoCapture(0)

def draw_button(text, x, y, w, h, inactive, active):
    mx, my = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    if x < mx < x+w and y < my < y+h:
        pygame.draw.rect(screen, active, (x,y,w,h))
        if click[0] == 1:
            return True
    else:
        pygame.draw.rect(screen, inactive, (x,y,w,h))
    txt = font.render(text, True, BLACK)
    rect = txt.get_rect(center=(x+w/2, y+h/2))
    screen.blit(txt, rect)
    return False

running = True
while running:
    ret, frame = cap.read()
    if ret:
        image  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image)

        if results.pose_landmarks and not paused and game_active:
            lm = results.pose_landmarks.landmark
            try:
                shoulder = [lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                            lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                elbow    = [lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                            lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
                wrist    = [lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                            lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]

                angle = calculate_angle(shoulder, elbow, wrist)
                percent_complete = np.interp(angle, [40, 90], [100, 0])
                percent_complete = np.clip(percent_complete, 0, 100)
                player_paddle.set_position(percent_complete)

                cv2.putText(frame, f"Angle: {int(angle)}°", (10,30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
                cv2.putText(frame, f"Completion: {int(percent_complete)}%", (10,70),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

            except Exception:
                pass

        # prepare camera frame for pygame
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = pygame.surfarray.make_surface(frame)
        frame = pygame.transform.flip(frame, True, False)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(BLACK)
    if ret:
        screen.blit(frame, (GAME_WIDTH, 0))

    if game_active and not paused:
        # AI movement
        ai_speed = 5
        if abs(ai_paddle.rect.centery - ball.rect.centery) > ai_speed:
            ai_paddle.rect.centery += ai_speed * np.sign(ball.rect.centery - ai_paddle.rect.centery)

        ball.move()

        # Collisions & scoring
        if ball.rect.colliderect(player_paddle.rect):
            ball.dx = -abs(ball.dx); player_score += 1
        if ball.rect.colliderect(ai_paddle.rect):
            ball.dx = abs(ball.dx); ai_score += 1
        if ball.rect.left <= 0 or ball.rect.right >= GAME_WIDTH:
            ball.reset()

        # --- NMES intensity logic ---
        ball_center   = ball.rect.centery
        paddle_center = player_paddle.rect.centery
        error_abs     = abs(ball_center - paddle_center)
        zone_margin   = 20
        misaligned    = paddle_center - zone_margin > ball_center or ball_center > paddle_center + zone_margin

        if misaligned:
            start_stimulation()
            # map error [0…GAME_HEIGHT] → [min_pwm…max_pwm]
            desired_pwm = int(np.interp(error_abs,
                                        [0, GAME_HEIGHT],
                                        [min_pwm, max_pwm]))
            if current_pwm < desired_pwm:
                stim_serial.write(b'u')
                current_pwm = min(current_pwm + pwm_step, max_pwm)
                print(f"PWM Increased → {current_pwm}")
            elif current_pwm > desired_pwm:
                stim_serial.write(b'j')
                current_pwm = max(current_pwm - pwm_step, min_pwm)
                print(f"PWM Decreased → {current_pwm}")

            # slow ball so user has time
            ball.dx *= 0.9
            instr = font.render("Move your arm to align with ball", True, WHITE)
            screen.blit(instr, (GAME_WIDTH//2-200, GAME_HEIGHT-100))

        else:
            stop_stimulation()
            if ball_center > player_paddle.rect.bottom + zone_margin:
                instr = font.render("Move arm DOWN (no stimulation)", True, WHITE)
                screen.blit(instr, (GAME_WIDTH//2-200, GAME_HEIGHT-100))

    # draw everything
    player_paddle.draw()
    ai_paddle.draw()
    ball.draw()

    screen.blit(font.render(f"Player: {player_score}", True, GREEN), (GAME_WIDTH-150, 20))
    screen.blit(font.render(f"AI: {ai_score}",     True, RED),   (50, 20))

    if draw_button("Pause" if not paused else "Resume",
                   20, GAME_HEIGHT-50, 100, 40, WHITE, (200,200,200)):
        paused = not paused
    if draw_button("Restart", 140, GAME_HEIGHT-50, 100, 40, WHITE, (200,200,200)):
        player_score = ai_score = 0
        ball.reset()
        paused = False
        game_active = True
    if draw_button("Quit", 260, GAME_HEIGHT-50, 100, 40, WHITE, (200,200,200)):
        running = False

    if paused:
        pause_text = large_font.render("PAUSED", True, WHITE)
        screen.blit(pause_text, (
            GAME_WIDTH//2 - pause_text.get_width()//2,
            GAME_HEIGHT//2 - pause_text.get_height()//2
        ))

    pygame.display.flip()
    clock.tick(60)

cap.release()
cv2.destroyAllWindows()
pygame.quit()
