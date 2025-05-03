import pygame
import cv2
import mediapipe as mp
import math
import random
import time
import os
import serial

class ForearmBalloonGame:
    # State machine states
    WAIT_FOR_DROP    = 0
    ASSIST_RAMP_UP   = 1
    WAIT_FOR_OPEN    = 2
    ASSIST_RAMP_DOWN = 3

    def __init__(self, serial_port="COM12", baudrate=19200):
        pygame.init()
        self.setup_game()

        # Hand‐pose tracker
        self.hands = mp.solutions.hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.cap = cv2.VideoCapture(0)

        # High‐score file
        self.load_best_score()

        # Open serial to Arduino
        print(f"[Serial] Opening {serial_port} @ {baudrate}")
        self.ser = serial.Serial(serial_port, baudrate, timeout=0.1)
        time.sleep(2)
        print("[Serial] Ready")

        # NMES parameters
        self.current_intensity = 0
        self.max_intensity     = 255
        self.intensity_step    = 10

        # State‐machine
        # initialize last_peak to current fill %
        init_pct = int(((self.balloon_radius - self.min_radius) /
                        (self.max_radius - self.min_radius)) * 100)
        self.last_peak_percent = init_pct
        self.state             = self.WAIT_FOR_DROP
        self.close_start_time  = None

    def setup_game(self):
        # window + camera sizing
        self.game_width, self.game_height = 600, 500
        self.cam_width,  self.cam_height  = 400, 300
        self.screen = pygame.display.set_mode((
            self.game_width + self.cam_width,
            max(self.game_height, self.cam_height)
        ))
        pygame.display.set_caption("Forearm Balloon Game")

        # colors
        self.WHITE = (255,255,255)
        self.BLACK = (0,0,0)
        self.RED   = (255,0,0)

        # balloon properties
        self.balloon_radius = 30
        self.min_radius     = 20
        self.max_radius     = 100
        self.inflation_rate = 0.5
        self.deflation_rate = 0.2 * 0.25  # deflate 75% slower
        self.balloon_pos    = (
            self.game_width//2,
            self.game_height//2
        )
        self.balloon_color  = random.choice([
            (231,76,60),(35,155,86),(155,89,182),
            (243,156,18),(244,208,63),(46,134,193)
        ])

        # game state
        self.score      = 0
        self.best_score = 0
        self.paused     = False
        self.burst_anim = False
        self.burst_time = 0

        # fonts
        self.font     = pygame.font.SysFont('Arial', 24)
        self.big_font = pygame.font.SysFont('Arial', 48)

    def load_best_score(self):
        if os.path.exists('balloon_best_score.txt'):
            with open('balloon_best_score.txt','r') as f:
                try:    self.best_score = int(f.read())
                except: self.best_score = 0

    def save_best_score(self):
        with open('balloon_best_score.txt','w') as f:
            f.write(str(self.best_score))

    def is_hand_closed(self, landmarks):
        # count folded fingers (tips below pip joint)
        tips = [8,12,16,20]
        folded = sum(
            1 for t in tips
            if landmarks[t].y > landmarks[t-2].y
        )
        return folded >= 3

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_p:
                    self.paused = not self.paused
                elif e.key == pygame.K_r:
                    self.reset_game()
                elif e.key == pygame.K_q:
                    return False
        return True

    def send_nmes(self, cmd: bytes):
        """Send one-byte, print send/recv."""
        self.ser.write(cmd)
        print(f">>> {cmd.decode()}")
        time.sleep(0.05)
        while self.ser.in_waiting:
            resp = self.ser.readline().decode(errors='ignore').strip()
            if resp:
                print(f"<<< {resp}")

    def update(self):
        if self.paused or self.burst_anim:
            return

        # capture + hand detection
        ret, frame = self.cap.read()
        if not ret: return
        frame = cv2.flip(frame, 1)
        img   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res   = self.hands.process(img)

        hand_closed = False
        if res.multi_hand_landmarks:
            for hl in res.multi_hand_landmarks:
                if self.is_hand_closed(hl.landmark):
                    hand_closed = True
                    break

        # balloon inflate/deflate
        if hand_closed:
            self.balloon_radius += self.inflation_rate
        else:
            self.balloon_radius -= self.deflation_rate

        self.balloon_radius = max(
            self.min_radius,
            min(self.max_radius, self.balloon_radius)
        )

        # compute fill %
        percent = int(((self.balloon_radius - self.min_radius) /
                       (self.max_radius - self.min_radius)) * 100)

        # —— state machine for NMES assist —— 
        if self.state == self.WAIT_FOR_DROP:
            # rising peak?
            if percent > self.last_peak_percent:
                self.last_peak_percent = percent
            # drop ≥8% from peak?
            elif self.last_peak_percent - percent >= 8:
                self.state = self.ASSIST_RAMP_UP

        elif self.state == self.ASSIST_RAMP_UP:
            if not hand_closed:
                # first‐time toggle ON
                if self.current_intensity == 0:
                    self.send_nmes(b'1')
                # ramp up
                self.current_intensity = min(
                    self.current_intensity + self.intensity_step,
                    self.max_intensity
                )
                self.send_nmes(b'u')
            else:
                self.state = self.WAIT_FOR_OPEN

        elif self.state == self.WAIT_FOR_OPEN:
            if not hand_closed:
                self.state = self.ASSIST_RAMP_DOWN

        elif self.state == self.ASSIST_RAMP_DOWN:
            if self.current_intensity > 0:
                self.send_nmes(b'j')
                self.current_intensity = max(
                    0,
                    self.current_intensity - self.intensity_step
                )
            else:
                # toggle OFF
                self.send_nmes(b'1')
                # reset for next cycle
                self.state             = self.WAIT_FOR_DROP
                self.last_peak_percent = percent

        # check for burst
        if self.balloon_radius >= self.max_radius:
            self.burst_anim = True
            self.burst_time = time.time()
            self.score += 1
            if self.score > self.best_score:
                self.best_score = self.score
                self.save_best_score()

    def draw(self):
        # clear
        self.screen.fill(self.BLACK)

        # camera feed
        ret, frame = self.cap.read()
        if ret:
            f = cv2.flip(frame, 1)
            f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
            f = cv2.resize(f, (self.cam_width, self.cam_height))
            surf = pygame.surfarray.make_surface(f.swapaxes(0,1))
            self.screen.blit(surf, (self.game_width, 0))

        # border
        pygame.draw.rect(
            self.screen, self.WHITE,
            (0,0,self.game_width,self.game_height), 2
        )

        # balloon or burst
        if self.burst_anim:
            if time.time() - self.burst_time < 0.5:
                self._draw_burst()
            else:
                self.burst_anim = False
                self.balloon_radius = self.min_radius
                self.balloon_color  = random.choice([
                    (231,76,60),(35,155,86),(155,89,182),
                    (243,156,18),(244,208,63),(46,134,193)
                ])
        else:
            self._draw_balloon()

        # HUD: Score, Best, Fill %, Intensity
        y = 20
        fill_pct = int(((self.balloon_radius - self.min_radius) /
                       (self.max_radius - self.min_radius)) * 100)
        for line in [
            f"Score:     {self.score}",
            f"Best:      {self.best_score}",
            f"Fill %:    {fill_pct}",
            f"Intensity: {self.current_intensity} ({int(self.current_intensity/self.max_intensity*100)}%)"
        ]:
            txt = self.font.render(line, True, self.WHITE)
            self.screen.blit(txt, (20, y))
            y += 30

        # instructions
        inst = self.font.render(
            "Close hand to inflate · Open to deflate", True, self.WHITE
        )
        self.screen.blit(
            inst,
            (self.game_width//2 - inst.get_width()//2, 20)
        )
        ctrl = self.font.render("P:Pause  R:Reset  Q:Quit", True, self.WHITE)
        self.screen.blit(
            ctrl,
            (self.game_width//2 - ctrl.get_width()//2,
             self.game_height-30)
        )

        if self.paused:
            p = self.big_font.render("PAUSED", True, self.WHITE)
            self.screen.blit(
                p,
                (self.game_width//2 - p.get_width()//2,
                 self.game_height//2 - p.get_height()//2)
            )

        pygame.display.flip()

    def _draw_balloon(self):
        pygame.draw.circle(
            self.screen, self.balloon_color,
            self.balloon_pos, int(self.balloon_radius)
        )
        # highlight
        hp = (
            self.balloon_pos[0] - self.balloon_radius//3,
            self.balloon_pos[1] - self.balloon_radius//3
        )
        pygame.draw.circle(
            self.screen, self.WHITE, hp, int(self.balloon_radius//4)
        )
        # string
        end = (
            self.balloon_pos[0],
            self.balloon_pos[1] + self.balloon_radius + 30
        )
        pygame.draw.line(
            self.screen, self.BLACK,
            self.balloon_pos, end, 2
        )
        # percent label
        pct = int(((self.balloon_radius - self.min_radius) /
                   (self.max_radius - self.min_radius))*100)
        t = self.font.render(f"{pct}%", True, self.BLACK)
        self.screen.blit(
            t,
            (self.balloon_pos[0] - t.get_width()//2,
             self.balloon_pos[1] - t.get_height()//2)
        )

    def _draw_burst(self):
        for i in range(12):
            a = i * (math.pi/6)
            ex = int(self.balloon_pos[0] + math.cos(a)*50)
            ey = int(self.balloon_pos[1] + math.sin(a)*50)
            pygame.draw.line(
                self.screen, self.balloon_color,
                self.balloon_pos, (ex,ey), 5
            )
        pop = self.big_font.render("POP!", True, self.RED)
        self.screen.blit(
            pop,
            (self.balloon_pos[0]-pop.get_width()//2,
             self.balloon_pos[1]-pop.get_height()//2)
        )

    def reset_game(self):
        self.score             = 0
        self.balloon_radius    = self.min_radius
        self.burst_anim        = False
        self.state             = self.WAIT_FOR_DROP
        self.last_peak_percent = int(((self.balloon_radius - self.min_radius) /
                                      (self.max_radius - self.min_radius))*100)
        self.current_intensity = 0

    def cleanup(self):
        self.cap.release()
        self.ser.close()
        pygame.quit()
        cv2.destroyAllWindows()

    def run(self):
        clock   = pygame.time.Clock()
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
