import pygame
import random
import networkx as nx
from collections import defaultdict
from constraint import Problem

# Initialize pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
GRID_SIZE = 4  # For a 4x4 grid (16 intersections)
INTERSECTION_SIZE = 60
ROAD_WIDTH = 25
FPS = 60
VEHICLE_SPEED = 2  # Normalized speed
TRAFFIC_LIGHT_CHANGE_INTERVAL = 300  # 5 seconds at 60 FPS

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
LIGHT_BLUE = (200, 230, 255)
GREEN_WAVE = (0, 200, 0, 100)
DARK_GREEN = (0, 150, 0)
BRIGHT_RED = (255, 50, 50)

class CityGrid:
    def __init__(self):
        self.size = GRID_SIZE
        self.intersections = [f'I{i+1}' for i in range(self.size*self.size)]
        self.roads = self._create_road_network()
        self.traffic_lights = {i: {'NS': 'red', 'EW': 'red', 'timer': 0} for i in self.intersections}
        self.vehicles = defaultdict(list)
        self.vehicle_positions = {}  # Track vehicle positions between intersections
        self.vehicle_routes = {}
        self.pedestrians = defaultdict(int)
        self.emergency_route = []
        self.emergency_vehicle_pos = 0
        self.stats = {
            'total_vehicles': 0,
            'cars': 0,
            'buses': 0,
            'emergency_vehicles': 0,
            'pedestrians': 0,
            'green_lights': 0,
            'red_lights': 0,
            'emergency_active': False,
            'active_signals': []
        }
        
    def _create_road_network(self):
        roads = []
        for row in range(self.size):
            for col in range(self.size-1):
                roads.append((f'I{row*self.size + col + 1}', f'I{row*self.size + col + 2}'))
        for col in range(self.size):
            for row in range(self.size-1):
                roads.append((f'I{row*self.size + col + 1}', f'I{(row+1)*self.size + col + 1}'))
        return roads
    
    def add_random_vehicles(self):
        for intersection in self.intersections:
            if random.random() < 0.1:  # 10% chance to add vehicles
                vehicle_types = ['car']*5 + ['bus']*2 + ['ambulance']*1
                vehicles = random.sample(vehicle_types, random.randint(1, 2))
                self.vehicles[intersection].extend(vehicles)  # Use extend instead of direct assignment
                
                for vehicle in vehicles:
                    vehicle_id = f"{intersection}_{vehicle}_{len([v for v in self.vehicles[intersection] if v == vehicle])}"
                    possible_routes = [road for road in self.roads if intersection in road]
                    if possible_routes:
                        route = random.choice(possible_routes)
                        next_intersection = route[0] if route[1] == intersection else route[1]
                        self.vehicle_routes[vehicle_id] = (intersection, next_intersection)
                        # Initialize vehicle positions
                        self.vehicle_positions[vehicle_id] = {
                            'current': intersection,
                            'next': next_intersection,
                            'progress': 0,
                            'speed': VEHICLE_SPEED * (0.8 if vehicle == 'bus' else 1.2 if vehicle == 'ambulance' else 1.0)
                        }
                
                self.stats['cars'] += vehicles.count('car')
                self.stats['buses'] += vehicles.count('bus')
                self.stats['emergency_vehicles'] += vehicles.count('ambulance')
                self.stats['total_vehicles'] = self.stats['cars'] + self.stats['buses'] + self.stats['emergency_vehicles']
    
    def add_random_pedestrians(self):
        for intersection in self.intersections:
            if random.random() < 0.2:
                pedestrians = random.randint(1, 3)
                self.pedestrians[intersection] = pedestrians
                self.stats['pedestrians'] += pedestrians
    
    def set_emergency_route(self, start, end):
        G = nx.Graph()
        G.add_edges_from(self.roads)
        try:
            self.emergency_route = nx.shortest_path(G, start, end)
            self.emergency_vehicle_pos = 0
            self.stats['emergency_active'] = True
        except nx.NetworkXNoPath:
            self.emergency_route = []
            self.stats['emergency_active'] = False
    
    def update_emergency_vehicle(self):
        if self.emergency_route and self.emergency_vehicle_pos < len(self.emergency_route)-1:
            self.emergency_vehicle_pos += VEHICLE_SPEED * 1.5  # Emergency vehicles are faster
    
    def update_vehicle_positions(self):
        vehicles_to_remove = []
        
        for vehicle_id, pos_info in list(self.vehicle_positions.items()):
            current = pos_info['current']
            next_intersection = pos_info['next']
            
            # Check if the traffic light allows movement
            can_move = True
            if current in self.traffic_lights:
                # Determine direction
                current_idx = self.intersections.index(current)
                next_idx = self.intersections.index(next_intersection)
                
                if next_idx == current_idx + 1:  # Moving east
                    can_move = self.traffic_lights[current]['EW'] == 'green'
                elif next_idx == current_idx - 1:  # Moving west
                    can_move = self.traffic_lights[current]['EW'] == 'green'
                elif next_idx == current_idx + self.size:  # Moving south
                    can_move = self.traffic_lights[current]['NS'] == 'green'
                elif next_idx == current_idx - self.size:  # Moving north
                    can_move = self.traffic_lights[current]['NS'] == 'green'
            
            if can_move:
                pos_info['progress'] += pos_info['speed']
                
                # If vehicle reached next intersection
                if pos_info['progress'] >= 100:
                    vehicles_to_remove.append((vehicle_id, current, next_intersection))
                    
                    # Assign new route
                    possible_routes = [road for road in self.roads if next_intersection in road]
                    if possible_routes:
                        route = random.choice(possible_routes)
                        new_next = route[0] if route[1] == next_intersection else route[1]
                        self.vehicle_routes[vehicle_id] = (next_intersection, new_next)
                        self.vehicle_positions[vehicle_id] = {
                            'current': next_intersection,
                            'next': new_next,
                            'progress': 0,
                            'speed': pos_info['speed']
                        }
        
        # Process vehicle movements after iteration to avoid modifying dict during iteration
        for vehicle_id, current, next_intersection in vehicles_to_remove:
            vehicle_type = vehicle_id.split('_')[1]
            if vehicle_type in self.vehicles[current]:
                self.vehicles[current].remove(vehicle_type)
            self.vehicles[next_intersection].append(vehicle_type)
    
    def update_traffic_lights(self):
        for intersection, lights in self.traffic_lights.items():
            lights['timer'] += 1
            if lights['timer'] >= TRAFFIC_LIGHT_CHANGE_INTERVAL:
                lights['timer'] = 0
                # Simple alternating pattern
                if lights['NS'] == 'green':
                    lights['NS'] = 'red'
                    lights['EW'] = 'green'
                else:
                    lights['NS'] = 'green'
                    lights['EW'] = 'red'
        
        self.update_traffic_light_stats()
    
    def update_traffic_light_stats(self):
        green = 0
        red = 0
        active_signals = []
        for intersection in self.intersections:
            if self.traffic_lights[intersection]['NS'] == 'green':
                green += 1
                active_signals.append(f"{intersection} NS")
            else:
                red += 1
            if self.traffic_lights[intersection]['EW'] == 'green':
                green += 1
                active_signals.append(f"{intersection} EW")
            else:
                red += 1
        self.stats['green_lights'] = green
        self.stats['red_lights'] = red
        self.stats['active_signals'] = active_signals

class TrafficOptimizer:
    def __init__(self, city):
        self.city = city
    
    def optimize_lights(self):
        problem = Problem()
        
        for intersection in self.city.intersections:
            problem.addVariable(f"{intersection}_NS", ['red', 'green'])
            problem.addVariable(f"{intersection}_EW", ['red', 'green'])
        
        # Basic constraint: no conflicting green lights
        for intersection in self.city.intersections:
            problem.addConstraint(
                lambda ns, ew: not (ns == 'green' and ew == 'green'),
                (f"{intersection}_NS", f"{intersection}_EW")
            )
        
        # Emergency route priority
        if self.city.emergency_route:
            for i in range(len(self.city.emergency_route)-1):
                current = self.city.emergency_route[i]
                next_node = self.city.emergency_route[i+1]
                if int(next_node[1:]) - int(current[1:]) == 1:  # Moving east-west
                    problem.addConstraint(lambda a: a == 'green', (f"{current}_EW",))
                    problem.addConstraint(lambda a: a == 'green', (f"{next_node}_EW",))
                else:  # Moving north-south
                    problem.addConstraint(lambda a: a == 'green', (f"{current}_NS",))
                    problem.addConstraint(lambda a: a == 'green', (f"{next_node}_NS",))
        
        solution = problem.getSolution()
        if solution:
            for intersection in self.city.intersections:
                self.city.traffic_lights[intersection]['NS'] = solution[f"{intersection}_NS"]
                self.city.traffic_lights[intersection]['EW'] = solution[f"{intersection}_EW"]
                self.city.traffic_lights[intersection]['timer'] = 0  # Reset timer
            
            self.city.update_traffic_light_stats()
            return True
        return False

class Simulation:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Smart City Traffic Simulation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 18)
        self.big_font = pygame.font.SysFont('Arial', 28)
        self.vehicle_font = pygame.font.SysFont('Segoe UI Emoji', 24)
        self.signal_font = pygame.font.SysFont('Arial', 14, bold=True)
        self.city = CityGrid()
        self.optimizer = TrafficOptimizer(self.city)
        self.time = 0
        self.running = True
        self.setup_simulation()
    
    def setup_simulation(self):
        self.city.add_random_vehicles()
        self.city.add_random_pedestrians()
        
        if random.random() < 0.3:
            start, end = random.sample(self.city.intersections, 2)
            self.city.set_emergency_route(start, end)
        
        self.optimizer.optimize_lights()
    
    def draw_intersection(self, x, y, intersection_id):
        pygame.draw.rect(self.screen, LIGHT_BLUE, 
                         (x - INTERSECTION_SIZE//2, y - INTERSECTION_SIZE//2, 
                          INTERSECTION_SIZE, INTERSECTION_SIZE), border_radius=5)
        pygame.draw.rect(self.screen, BLUE, 
                         (x - INTERSECTION_SIZE//2, y - INTERSECTION_SIZE//2, 
                          INTERSECTION_SIZE, INTERSECTION_SIZE), 2, border_radius=5)
        
        label = self.big_font.render(intersection_id[1:], True, BLACK)
        self.screen.blit(label, (x - label.get_width()//2, y - label.get_height()//2))
        
        light_offset = INTERSECTION_SIZE//2 + 10
        pygame.draw.rect(self.screen, BLACK, (x - 8, y - light_offset, 16, 25), border_radius=3)
        pygame.draw.circle(self.screen, 
                          DARK_GREEN if self.city.traffic_lights[intersection_id]['NS'] == 'green' else BRIGHT_RED,
                          (x, y - light_offset + 12), 8)
        
        pygame.draw.rect(self.screen, BLACK, (x + light_offset - 20, y - 8, 25, 16), border_radius=3)
        pygame.draw.circle(self.screen, 
                          DARK_GREEN if self.city.traffic_lights[intersection_id]['EW'] == 'green' else BRIGHT_RED,
                          (x + light_offset - 8, y), 8)
        
        if self.city.traffic_lights[intersection_id]['NS'] == 'green':
            text = self.signal_font.render("NS GREEN", True, DARK_GREEN)
            self.screen.blit(text, (x - text.get_width()//2, y - light_offset - 20))
        
        if self.city.traffic_lights[intersection_id]['EW'] == 'green':
            text = self.signal_font.render("EW GREEN", True, DARK_GREEN)
            self.screen.blit(text, (x + light_offset + 5, y - text.get_height()//2))
    
    def draw_road(self, start_pos, end_pos):
        pygame.draw.line(self.screen, GRAY, start_pos, end_pos, ROAD_WIDTH)
        pygame.draw.line(self.screen, WHITE, start_pos, end_pos, 2)
    
    def draw_vehicle(self, x, y, vehicle_type, destination=None, progress=0):
        if vehicle_type == 'car':
            icon = "🚗"
        elif vehicle_type == 'bus':
            icon = "🚌"
        elif vehicle_type == 'ambulance':
            icon = "🚑"
        
        text = self.vehicle_font.render(icon, True, BLACK)
        shadow = self.vehicle_font.render(icon, True, (100, 100, 100))
        self.screen.blit(shadow, (x - text.get_width()//2 + 2, y - text.get_height()//2 + 2))
        self.screen.blit(text, (x - text.get_width()//2, y - text.get_height()//2))
        
        if destination:
            dest_pos = self.get_intersection_position(destination)
            dx = dest_pos[0] - x
            dy = dest_pos[1] - y
            angle = pygame.math.Vector2(dx, dy).angle_to((1, 0))
            
            arrow_length = 30
            end_x = x + arrow_length * pygame.math.Vector2(1, 0).rotate(-angle).x
            end_y = y + arrow_length * pygame.math.Vector2(1, 0).rotate(-angle).y
            
            pygame.draw.line(self.screen, GREEN, (x, y), (end_x, end_y), 2)
            pygame.draw.circle(self.screen, GREEN, (int(end_x), int(end_y)), 4)
    
    def draw_moving_vehicle(self, vehicle_id, vehicle_type, start_pos, end_pos, progress):
        x = start_pos[0] + (end_pos[0] - start_pos[0]) * (progress / 100)
        y = start_pos[1] + (end_pos[1] - start_pos[1]) * (progress / 100)
        self.draw_vehicle(x, y, vehicle_type)
    
    def draw_pedestrians(self, x, y, count):
        for i in range(count):
            row = i // 2
            col = i % 2
            ped_x = x - 20 + col * 25
            ped_y = y + 20 + row * 25
            text = self.vehicle_font.render("🚶", True, BLACK)
            shadow = self.vehicle_font.render("🚶", True, (100, 100, 100))
            self.screen.blit(shadow, (ped_x - text.get_width()//2 + 1, ped_y - text.get_height()//2 + 1))
            self.screen.blit(text, (ped_x - text.get_width()//2, ped_y - text.get_height()//2))
    
    def draw_emergency_route(self):
        if not self.city.emergency_route:
            return
        
        route_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        for i in range(len(self.city.emergency_route)-1):
            start_pos = self.get_intersection_position(self.city.emergency_route[i])
            end_pos = self.get_intersection_position(self.city.emergency_route[i+1])
            
            dx = end_pos[0] - start_pos[0]
            dy = end_pos[1] - start_pos[1]
            length = (dx**2 + dy**2)**0.5
            if length > 0:
                perp_x = -dy/length * (ROAD_WIDTH//2 + 5)
                perp_y = dx/length * (ROAD_WIDTH//2 + 5)
                
                for offset in range(-2, 3):
                    offset_x = perp_x * offset
                    offset_y = perp_y * offset
                    pygame.draw.line(route_surface, GREEN_WAVE, 
                                   (start_pos[0] + offset_x, start_pos[1] + offset_y),
                                   (end_pos[0] + offset_x, end_pos[1] + offset_y), 
                                   3)
        
        self.screen.blit(route_surface, (0, 0))
        
        if self.city.emergency_vehicle_pos < len(self.city.emergency_route):
            idx = int(self.city.emergency_vehicle_pos)
            progress = self.city.emergency_vehicle_pos - idx
            
            if idx < len(self.city.emergency_route)-1:
                start_pos = self.get_intersection_position(self.city.emergency_route[idx])
                end_pos = self.get_intersection_position(self.city.emergency_route[idx+1])
                
                vehicle_x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
                vehicle_y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
                
                pulse = int(pygame.time.get_ticks() / 200) % 2
                size = 28 if pulse else 24
                font = pygame.font.SysFont('Segoe UI Emoji', size)
                text = font.render("🚑", True, (255, 50, 50))
                self.screen.blit(text, (vehicle_x - text.get_width()//2, vehicle_y - text.get_height()//2))
                
                route_text = self.font.render(f"Emergency Route: {self.city.emergency_route[idx]} → {self.city.emergency_route[idx+1]}", True, BRIGHT_RED)
                self.screen.blit(route_text, (20, SCREEN_HEIGHT - 30))
    
    def get_intersection_position(self, intersection_id):
        idx = self.city.intersections.index(intersection_id)
        row = idx // self.city.size
        col = idx % self.city.size
        
        x = (SCREEN_WIDTH - 300) // (self.city.size + 1) * (col + 1)
        y = SCREEN_HEIGHT // (self.city.size + 1) * (row + 1)
        
        return (x, y)
    
    def draw_stats_panel(self):
        panel_x = SCREEN_WIDTH - 280
        panel_y = 20
        panel_width = 260
        panel_height = SCREEN_HEIGHT - 40
        
        pygame.draw.rect(self.screen, (245, 245, 245), (panel_x, panel_y, panel_width, panel_height), border_radius=10)
        pygame.draw.rect(self.screen, (70, 70, 70), (panel_x, panel_y, panel_width, panel_height), 2, border_radius=10)
        
        title = self.big_font.render("Traffic Stats", True, (0, 80, 150))
        pygame.draw.rect(self.screen, (220, 230, 240), 
                         (panel_x + panel_width//2 - title.get_width()//2 - 10, panel_y + 5, 
                          title.get_width() + 20, title.get_height() + 10), border_radius=5)
        self.screen.blit(title, (panel_x + panel_width//2 - title.get_width()//2, panel_y + 10))
        
        y_offset = 60
        stats = [
            ("Time", f"{self.time//3600:02d}:{(self.time%3600)//60:02d}:{self.time%60:02d}"),
            ("Total Vehicles", self.city.stats['total_vehicles']),
            ("Cars", self.city.stats['cars']),
            ("Buses", self.city.stats['buses']),
            ("Ambulances", self.city.stats['emergency_vehicles']),
            ("Pedestrians", self.city.stats['pedestrians']),
            ("Green Lights", self.city.stats['green_lights']),
            ("Red Lights", self.city.stats['red_lights']),
            ("Emergency", "ACTIVE" if self.city.stats['emergency_active'] else "None")
        ]
        
        for label, value in stats:
            label_text = self.font.render(f"{label}:", True, (0, 0, 0))
            self.screen.blit(label_text, (panel_x + 15, panel_y + y_offset))
            
            color = (0, 100, 0) if label == "Green Lights" else \
                   (200, 0, 0) if label == "Red Lights" else \
                   (200, 0, 0) if label == "Emergency" and value == "ACTIVE" else \
                   (0, 0, 0)
            
            value_text = self.font.render(str(value), True, color)
            self.screen.blit(value_text, (panel_x + panel_width - 15 - value_text.get_width(), panel_y + y_offset))
            
            y_offset += 32
        
        y_offset += 20
        signals_title = self.font.render("Active Signals:", True, (0, 80, 150))
        self.screen.blit(signals_title, (panel_x + 15, panel_y + y_offset))
        y_offset += 30
        
        for signal in self.city.stats['active_signals']:
            signal_text = self.font.render(signal, True, DARK_GREEN)
            self.screen.blit(signal_text, (panel_x + 20, panel_y + y_offset))
            y_offset += 25
        
        y_offset += 20
        legend_title = self.font.render("Vehicle Legend:", True, (0, 80, 150))
        self.screen.blit(legend_title, (panel_x + 15, panel_y + y_offset))
        y_offset += 30
        
        legend_items = [
            ("🚗", "Car"),
            ("🚌", "Bus"),
            ("🚑", "Ambulance"),
            ("🚶", "Pedestrian"),
            ("→", "Moving to")
        ]
        
        for icon, text in legend_items:
            if icon == "→":
                pygame.draw.line(self.screen, GREEN, (panel_x + 20, panel_y + y_offset + 10), 
                               (panel_x + 40, panel_y + y_offset + 10), 2)
                pygame.draw.circle(self.screen, GREEN, (panel_x + 45, panel_y + y_offset + 10), 4)
            else:
                icon_text = self.vehicle_font.render(icon, True, BLACK)
                self.screen.blit(icon_text, (panel_x + 20, panel_y + y_offset))
            
            text_text = self.font.render(text, True, BLACK)
            self.screen.blit(text_text, (panel_x + 50, panel_y + y_offset))
            
            y_offset += 35
    
    def draw_time(self):
        hours = self.time // 3600
        minutes = (self.time % 3600) // 60
        seconds = self.time % 60
        time_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        pygame.draw.rect(self.screen, (230, 240, 255), (15, 15, 150, 40), border_radius=5)
        pygame.draw.rect(self.screen, (0, 80, 150), (15, 15, 150, 40), 2, border_radius=5)
        
        text = self.big_font.render(time_text, True, (0, 80, 150))
        self.screen.blit(text, (20, 20))
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.city = CityGrid()
                    self.optimizer = TrafficOptimizer(self.city)
                    self.setup_simulation()
                    self.time = 0
                elif event.key == pygame.K_SPACE:
                    self.running = not self.running
                elif event.key == pygame.K_UP:
                    global VEHICLE_SPEED
                    VEHICLE_SPEED = min(5, VEHICLE_SPEED + 0.5)
                elif event.key == pygame.K_DOWN:
                    VEHICLE_SPEED = max(0.5, VEHICLE_SPEED - 0.5)
    
    def update(self):
        if self.running:
            self.time += 1
            
            # Update traffic lights at regular intervals
            if self.time % TRAFFIC_LIGHT_CHANGE_INTERVAL == 0:
                self.city.update_traffic_lights()
                self.optimizer.optimize_lights()
            
            self.city.update_emergency_vehicle()
            self.city.update_vehicle_positions()
            
            if self.time % 600 == 0:  # Every 10 seconds
                self.city.add_random_vehicles()
                self.city.add_random_pedestrians()
    
    def draw(self):
        self.screen.fill((220, 230, 240))
        pygame.draw.rect(self.screen, (200, 220, 235), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT//2))
        
        # Draw roads
        for road in self.city.roads:
            start_pos = self.get_intersection_position(road[0])
            end_pos = self.get_intersection_position(road[1])
            self.draw_road(start_pos, end_pos)
        
        self.draw_emergency_route()
        
        # Draw intersections and vehicles
        for intersection in self.city.intersections:
            x, y = self.get_intersection_position(intersection)
            self.draw_intersection(x, y, intersection)
            
            # Draw vehicles at intersections
            for i, vehicle in enumerate(self.city.vehicles[intersection]):
                vehicle_id = f"{intersection}_{vehicle}_{i}"
                offset_x = -20 + (i % 2) * 40
                offset_y = -20 + (i // 2) * 40
                
                destination = None
                if vehicle_id in self.city.vehicle_routes:
                    _, destination = self.city.vehicle_routes[vehicle_id]
                
                self.draw_vehicle(x + offset_x, y + offset_y, vehicle, destination)
            
            # Draw moving vehicles between intersections
            for vehicle_id, pos_info in self.city.vehicle_positions.items():
                if pos_info['current'] == intersection:
                    start_pos = self.get_intersection_position(pos_info['current'])
                    end_pos = self.get_intersection_position(pos_info['next'])
                    self.draw_moving_vehicle(vehicle_id, vehicle_id.split('_')[1], 
                                           start_pos, end_pos, pos_info['progress'])
            
            # Draw pedestrians
            if self.city.pedestrians[intersection] > 0:
                self.draw_pedestrians(x, y, self.city.pedestrians[intersection])
        
        self.draw_stats_panel()
        self.draw_time()
        
        # Display current speed
        speed_text = self.font.render(f"Speed: {VEHICLE_SPEED:.1f}x (UP/DOWN to adjust)", True, BLACK)
        self.screen.blit(speed_text, (20, 70))
        
        pygame.display.flip()
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()

if __name__ == "__main__":
    simulation = Simulation()
    simulation.run()