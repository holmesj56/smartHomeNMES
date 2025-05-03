import cv2
import mediapipe as mp
import numpy as np
import pygame
import random
import serial
import time

# ─── SERIAL SETUP ─────────────────────────────────────────────────────────
arduino_port = 'COM12'
baud_rate    = 19200
try:
    ser = serial.Serial(arduino_port, baudrate=baud_rate, timeout=1)
    time.sleep(2)
    ser.reset_input_buffer()
    print("Connected to NMES device.")
except Exception as e:
    ser = None
    print(f"Serial connection failed: {e}")

# ─── NMES STATE MACHINE ─────────────────────────────────────────────────
current_intensity = 0
max_intensity     = 255
intensity_step    = max_intensity // 10  # 10% steps

last_pct          = None
expecting_up      = True
hold_start        = None
full_hold_start   = None

small_thresh = 1.5    # ° for “stuck” detection
hold_time    = 3      # s to trigger bump when stuck/full
drop_thresh  = 10     # % drop triggers early‐drop bump
full_min     = 95     # % = full contraction
rest_max     = 5      # % = rest position

def send_cmd(cmd, timeout=1.0):
    """Write cmd, wait for ack containing key substring."""
    if not ser:
        return None
    ser.reset_input_buffer()
    ser.write(f"{cmd}\r\n".encode())
    ser.flush()
    start = time.time()
    expected = {'u': 'PWM Increased', 'j': 'PWM Decreased', '1': 'Channel 1'}.get(cmd)
    while time.time() - start < timeout:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            continue
        print(f"<<< Arduino: {line}")
        if expected and expected in line:
            return line
    print(f"!!! No ack for '{cmd}' within {timeout}s")
    return None

def activate_channel():
    """Toggle channel on, expect 'active' in the Arduino reply."""
    ack = send_cmd('1')
    if ack and 'active' in ack.lower():
        print("*** Channel ON")

def deactivate_channel():
    """Toggle channel off, expect 'inactive' in the Arduino reply."""
    ack = send_cmd('1')
    if ack and 'inactive' in ack.lower():
        print("*** Channel OFF")

def increase_intensity():
    global current_intensity
    if current_intensity < max_intensity:
        if send_cmd('u'):
            current_intensity = min(current_intensity + intensity_step, max_intensity)
            print(f"*** Intensity: {int((current_intensity/max_intensity)*100)}%")

def reset_intensity():
    global current_intensity
    while current_intensity > 0:
        if send_cmd('j'):
            current_intensity = max(current_intensity - intensity_step, 0)
            print(f"*** Intensity: {int((current_intensity/max_intensity)*100)}%")
        else:
            break
    deactivate_channel()

# ─── HELPERS ─────────────────────────────────────────────────────────────
def calc_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    cosv = np.dot(a-b, c-b)/(np.linalg.norm(a-b)*np.linalg.norm(c-b))
    cosv = np.clip(cosv, -1.0, 1.0)
    return np.degrees(np.arccos(cosv))

def predict_intersection(ball, target_x):
    """Simulate ball path until x crosses target_x, reflecting off walls."""
    x, y = ball.rect.centerx, ball.rect.centery
    dx, dy = ball.dx, ball.dy
    while True:
        if (dx>0 and x>=target_x) or (dx<0 and x<=target_x):
            break
        x += dx; y += dy
        if y <= 0 or y >= GAME_HEIGHT:
            dy *= -1
    return y

# ─── PYGAME + MEDIAPIPE SETUP ────────────────────────────────────────────
pygame.init()
GAME_WIDTH, GAME_HEIGHT = 640, 480
CAM_WIDTH,  CAM_HEIGHT  = 640, 480
SCREEN = pygame.display.set_mode((GAME_WIDTH+CAM_WIDTH, GAME_HEIGHT))
pygame.display.set_caption("Arm-Controlled Pong + NMES")
clock = pygame.time.Clock()

PADDLE_W, PADDLE_H = 15, 100
BALL_SIZE = 15
WHITE = (255,255,255)
BLACK = (0,0,0)
RED   = (255,0,0)
GREEN = (0,255,0)
BLUE  = (0,0,255)

font       = pygame.font.SysFont('Arial', 24)
large_font = pygame.font.SysFont('Arial', 48)

mp_pose = mp.solutions.pose
pose    = mp_pose.Pose(min_detection_confidence=0.5,
                       min_tracking_confidence=0.5)

# ─── GAME OBJECTS ───────────────────────────────────────────────────────
class Paddle:
    def __init__(self, x, y, col):
        self.rect = pygame.Rect(x, y, PADDLE_W, PADDLE_H)
        self.col  = col
    def set_pos(self, pct):
        y = GAME_HEIGHT - PADDLE_H - (pct/100)*(GAME_HEIGHT-PADDLE_H)
        self.rect.y = int(np.clip(y, 0, GAME_HEIGHT-PADDLE_H))
    def draw(self):
        pygame.draw.rect(SCREEN, self.col, self.rect)

class Ball:
    def __init__(self):
        self.reset()
    def reset(self):
        speed = 7
        self.dx = speed * random.choice([1, -1])
        self.dy = speed * random.choice([1, -1])
        self.base_dx = abs(self.dx)
        self.base_dy = abs(self.dy)
        self.rect = pygame.Rect(GAME_WIDTH//2,
                                GAME_HEIGHT//2,
                                BALL_SIZE, BALL_SIZE)
    def move(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        if self.rect.top <= 0 or self.rect.bottom >= GAME_HEIGHT:
            self.dy *= -1
    def draw(self):
        pygame.draw.rect(SCREEN, WHITE, self.rect)

player = Paddle(GAME_WIDTH-50, GAME_HEIGHT//2, GREEN)
ai     = Paddle(30, GAME_HEIGHT//2, RED)
ball   = Ball()

player_score = 0
ai_score     = 0
paused       = False
running      = True
last_pct     = None

cap = cv2.VideoCapture(0)
while running:
    ret, frame = cap.read()
    if not ret: break

    # Pose → paddle mapping
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = pose.process(img)
    pct = None
    if res.pose_landmarks:
        lm = res.pose_landmarks.landmark
        s = [lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
             lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
        e = [lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
             lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
        w = [lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
             lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
        angle = calc_angle(s, e, w)
        pct   = np.interp(angle, [40,90], [100,0])
        pct   = np.clip(pct, 0, 100)
        player.set_pos(pct)

        # NMES logic
        if last_pct is not None:
            delta = pct - last_pct
            if expecting_up:
                if delta < -drop_thresh:
                    increase_intensity()
                if abs(delta) < small_thresh:
                    if hold_start is None:
                        hold_start = time.time()
                    elif time.time()-hold_start > hold_time:
                        increase_intensity()
                        hold_start = None
                else:
                    hold_start = None
                if pct >= full_min:
                    if full_hold_start is None:
                        full_hold_start = time.time()
                    elif time.time()-full_hold_start > hold_time:
                        reset_intensity()
                        expecting_up    = False
                        full_hold_start = None
            else:
                if pct <= rest_max:
                    expecting_up = True
        last_pct = pct

    # Camera → Pygame surface
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = np.rot90(frame)
    surf  = pygame.surfarray.make_surface(frame)
    surf  = pygame.transform.flip(surf, True, False)

    for evt in pygame.event.get():
        if evt.type == pygame.QUIT:
            running = False
        elif evt.type == pygame.KEYDOWN and evt.key == pygame.K_p:
            paused = not paused

    SCREEN.fill(BLACK)
    if ret:
        SCREEN.blit(surf, (GAME_WIDTH, 0))

    # Game physics
    if not paused:
        # AI paddle
        if abs(ai.rect.centery - ball.rect.centery) > 5:
            ai.rect.centery += 5 * np.sign(ball.rect.centery - ai.rect.centery)
        ball.move()

        # Collisions & reset
        if ball.rect.colliderect(player.rect):
            ball.dx = -abs(ball.dx); player_score+=1
        if ball.rect.colliderect(ai.rect):
            ball.dx =  abs(ball.dx); ai_score    +=1
        if ball.rect.left<=0 or ball.rect.right>=GAME_WIDTH:
            ball.reset()

        # Slowdown while intensity > 0
        if current_intensity > 0:
            ball.dx *= 0.9
            ball.dy *= 0.9

    # Shadow ball + catch detection
    if ball.dx > 0:
        target_x = player.rect.left
        pred_y   = predict_intersection(ball, target_x)
        pygame.draw.circle(SCREEN, BLUE, (target_x, int(pred_y)), BALL_SIZE//2)
        if player.rect.collidepoint(target_x, int(pred_y)):
            # restore speed & reset NMES for next cycle
            ball.dx = np.sign(ball.dx)*ball.base_dx
            ball.dy = np.sign(ball.dy)*ball.base_dy
            reset_intensity()
            expecting_up     = True
            last_pct         = None
            hold_start       = None
            full_hold_start  = None

    # Draw everything
    player.draw()
    ai.draw()
    ball.draw()

    SCREEN.blit(font.render(f"Player: {player_score}", True, GREEN),
                (GAME_WIDTH-150, 20))
    SCREEN.blit(font.render(f"AI:     {ai_score}",     True, RED),
                (50, 20))

    # ** Always show intensity % at bottom of game area **
    SCREEN.blit(font.render(f"Intensity: {int((current_intensity/max_intensity)*100)}%", True, WHITE),
                (GAME_WIDTH+10, GAME_HEIGHT-40))

    pygame.display.flip()
    clock.tick(60)

cap.release()
if ser: ser.close()
cv2.destroyAllWindows()
pygame.quit()
