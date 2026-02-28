import pygame
import random
import math
import numpy as np

pygame.init()

# CONFIG
WIDTH, HEIGHT = 1200, 900
ROAD_WIDTH = 200
SAFE_DISTANCE = 50
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SMART CITY 4.0 – Fully Working 4-Way Intersection")

clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 18)

# COLORS
WHITE = (255,255,255)
BLACK = (30,30,30)
GRAY = (60,60,60)
GREEN = (0,200,0)
RED = (200,0,0)
YELLOW = (255,200,0)
BLUE = (0,120,255)
DARK_GRAY = (50,50,50)
ROAD_SHADE = (40,40,40)
LIGHT_POLE = (80,80,80)

# INTERSECTION CLASS
class RLSignal:
    def __init__(self, center):
        self.center = center
        self.directions = ["N","E","S","W"]
        self.current = "N"
        self.timer = 0
        self.green_time_base = 120
        self.green_time = self.green_time_base  # initialize green_time
        self.yellow_time = 50
        self.state = "GREEN"
        self.emergency_lock = False

    # Count waiting vehicles per direction
    def congestion(self, vehicles):
        counts = {d:0 for d in self.directions}
        for v in vehicles:
            if not v.crossed and not v.is_emergency:
                counts[v.direction] += 1
        return counts

    # Choose next green based on congestion
    def choose_next(self, vehicles):
        counts = self.congestion(vehicles)
        max_dir = max(counts, key=lambda x: counts[x])
        self.green_time = self.green_time_base + counts[max_dir]*5  # more cars = longer green
        return max_dir

    # Update signal state
    def update(self, vehicles):
        # Emergency override
        ambulance = None
        for v in vehicles:
            if v.is_emergency and not v.crossed:
                ambulance = v
                break
        if ambulance:
            self.current = ambulance.direction
            self.state = "GREEN"
            self.timer = 0
            self.emergency_lock = True
            return

        if self.emergency_lock:
            self.emergency_lock = False

        self.timer += 1
        if self.state == "GREEN" and self.timer > self.green_time:
            self.state = "YELLOW"
            self.timer = 0
        elif self.state == "YELLOW" and self.timer > self.yellow_time:
            next_dir = self.choose_next(vehicles)
            self.current = next_dir
            self.state = "GREEN"
            self.timer = 0

    def draw(self):
        cx, cy = self.center
        pole_width = 10
        pole_height = 60
        pygame.draw.rect(screen, LIGHT_POLE, (cx - ROAD_WIDTH//2 + 40, cy - ROAD_WIDTH//2 + 20, pole_width, pole_height))
        pygame.draw.rect(screen, LIGHT_POLE, (cx + ROAD_WIDTH//2 - 50, cy + ROAD_WIDTH//2 - 80, pole_width, pole_height))
        pygame.draw.rect(screen, LIGHT_POLE, (cx + ROAD_WIDTH//2 - 80, cy - ROAD_WIDTH//2 + 40, pole_height, pole_width))
        pygame.draw.rect(screen, LIGHT_POLE, (cx - ROAD_WIDTH//2 + 20, cy + ROAD_WIDTH//2 - 50, pole_height, pole_width))

        light_radius = 15
        offset = 30
        for d in self.directions:
            color = RED
            if self.current == d:
                color = GREEN if self.state=="GREEN" else YELLOW
            if d=="N":
                pygame.draw.circle(screen, color, (cx - ROAD_WIDTH//2 + 45, cy - offset), light_radius)
            if d=="S":
                pygame.draw.circle(screen, color, (cx + ROAD_WIDTH//2 - 45, cy + offset), light_radius)
            if d=="E":
                pygame.draw.circle(screen, color, (cx + offset, cy - ROAD_WIDTH//2 + 45), light_radius)
            if d=="W":
                pygame.draw.circle(screen, color, (cx - offset, cy + ROAD_WIDTH//2 - 45), light_radius)

# VEHICLE CLASS
class Vehicle:
    WIDTH = 40
    HEIGHT = 20
    STOP_BUFFER = 50

    def __init__(self, direction, intersection, emergency=False):
        self.direction = direction
        self.intersection = intersection
        self.is_emergency = emergency
        self.crossed = False
        self.in_intersection = False
        self.speed = random.uniform(2,3)
        self.velocity = 0
        self.acceleration = 0.05

        cx, cy = intersection.center
        if direction == "N":
            self.x, self.y = cx-40, -60
        elif direction == "S":
            self.x, self.y = cx+40, HEIGHT+60
        elif direction == "E":
            self.x, self.y = WIDTH+60, cy-40
        elif direction == "W":
            self.x, self.y = -60, cy+40

    def stop_line(self):
        cx, cy = self.intersection.center
        if self.direction=="N":
            return cy - ROAD_WIDTH//2 - self.STOP_BUFFER
        elif self.direction=="S":
            return cy + ROAD_WIDTH//2 + self.STOP_BUFFER
        elif self.direction=="E":
            return cx + ROAD_WIDTH//2 + self.STOP_BUFFER
        elif self.direction=="W":
            return cx - ROAD_WIDTH//2 - self.STOP_BUFFER

    def should_stop(self, vehicles):
        if self.is_emergency:
            return False

        # Stop at stop line if red or yellow
        sl = self.stop_line()
        if not self.in_intersection:
            if self.direction=="N" and self.y + self.HEIGHT >= sl:
                if self.direction != self.intersection.current or self.intersection.state=="YELLOW":
                    return True
            elif self.direction=="S" and self.y <= sl:
                if self.direction != self.intersection.current or self.intersection.state=="YELLOW":
                    return True
            elif self.direction=="E" and self.x <= sl:
                if self.direction != self.intersection.current or self.intersection.state=="YELLOW":
                    return True
            elif self.direction=="W" and self.x + self.WIDTH >= sl:
                if self.direction != self.intersection.current or self.intersection.state=="YELLOW":
                    return True

        # Safe distance only for vehicles ahead in the same lane
        for v in vehicles:
            if v==self or v.in_intersection:
                continue
            # N/S lane
            if self.direction in ["N","S"] and v.direction in ["N","S"]:
                if self.direction=="N" and 0 < v.y - self.y < SAFE_DISTANCE and abs(self.x - v.x) < ROAD_WIDTH//4:
                    return True
                if self.direction=="S" and 0 < self.y - v.y < SAFE_DISTANCE and abs(self.x - v.x) < ROAD_WIDTH//4:
                    return True
            # E/W lane
            elif self.direction in ["E","W"] and v.direction in ["E","W"]:
                if self.direction=="E" and 0 < self.x - v.x < SAFE_DISTANCE and abs(self.y - v.y) < ROAD_WIDTH//4:
                    return True
                if self.direction=="W" and 0 < v.x - self.x < SAFE_DISTANCE and abs(self.y - v.y) < ROAD_WIDTH//4:
                    return True

        return False

    def move(self):
        self.velocity = min(self.velocity + self.acceleration, self.speed)
        # Enter intersection
        if not self.in_intersection:
            cx, cy = self.intersection.center
            if self.direction=="N" and self.y + self.HEIGHT >= cy - ROAD_WIDTH//2:
                self.in_intersection = True
            elif self.direction=="S" and self.y <= cy + ROAD_WIDTH//2:
                self.in_intersection = True
            elif self.direction=="E" and self.x <= cx + ROAD_WIDTH//2:
                self.in_intersection = True
            elif self.direction=="W" and self.x + self.WIDTH >= cx - ROAD_WIDTH//2:
                self.in_intersection = True

        # Move forward
        if self.direction=="N":
            self.y += self.velocity
        elif self.direction=="S":
            self.y -= self.velocity
        elif self.direction=="E":
            self.x -= self.velocity
        elif self.direction=="W":
            self.x += self.velocity

        # Mark crossed
        cx, cy = self.intersection.center
        if self.direction=="N" and self.y >= cy + ROAD_WIDTH//2:
            self.crossed = True
        elif self.direction=="S" and self.y <= cy - ROAD_WIDTH//2:
            self.crossed = True
        elif self.direction=="E" and self.x <= cx - ROAD_WIDTH//2:
            self.crossed = True
        elif self.direction=="W" and self.x >= cx + ROAD_WIDTH//2:
            self.crossed = True

    def update(self, vehicles):
        if self.should_stop(vehicles):
            self.velocity = max(self.velocity - 0.1, 0)
        else:
            self.move()

    def draw(self):
        color = BLUE if self.is_emergency else WHITE
        shade = (max(color[0]-30,0), max(color[1]-30,0), max(color[2]-30,0))
        pygame.draw.rect(screen, color, (self.x, self.y, self.WIDTH, self.HEIGHT))
        pygame.draw.rect(screen, shade, (self.x, self.y, self.WIDTH, self.HEIGHT//2))
        if self.is_emergency and pygame.time.get_ticks()%300<150:
            pygame.draw.circle(screen, YELLOW, (int(self.x+10),int(self.y+10)),5)

# MAIN LOOP
intersection = RLSignal((WIDTH//2, HEIGHT//2))
vehicles = []
spawn_timer = 0
running = True

while running:
    clock.tick(FPS)
    screen.fill(GRAY)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Draw roads
    cx, cy = intersection.center
    pygame.draw.rect(screen, ROAD_SHADE, (cx-ROAD_WIDTH//2,0,ROAD_WIDTH,HEIGHT))
    pygame.draw.rect(screen, ROAD_SHADE, (0,cy-ROAD_WIDTH//2,WIDTH,ROAD_WIDTH))

    # Spawn vehicles
    spawn_timer += 1
    if spawn_timer > 40:
        direction = random.choice(["N","S","E","W"])
        emergency = random.random() < 0.05
        vehicles.append(Vehicle(direction, intersection, emergency))
        spawn_timer = 0

    # Update intersection
    intersection.update(vehicles)
    intersection.draw()

    # Update vehicles
    for v in vehicles[:]:
        v.update(vehicles)
        v.draw()
        if v.x<-200 or v.x>WIDTH+200 or v.y<-200 or v.y>HEIGHT+200:
            vehicles.remove(v)

    info = font.render(f"Vehicles: {len(vehicles)}", True, WHITE)
    screen.blit(info,(20,20))

    pygame.display.flip()

pygame.quit()