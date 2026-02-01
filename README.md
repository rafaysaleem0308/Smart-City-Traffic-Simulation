# 🏙️ Smart City Traffic Simulation

**Smart City Traffic Simulation** is a **Python/Pygame project** that models traffic flow in a city grid. The simulation includes **vehicles, buses, emergency vehicles, pedestrians, and traffic lights**. It uses **constraint-based optimization** to prioritize emergency vehicles and dynamically adjusts traffic light patterns for efficient traffic flow.

---

## 🌟 Features

- **Dynamic City Grid:** Simulates a **4x4 city grid** with intersections and roads.  
- **Vehicles & Pedestrians:** Randomly spawns **cars, buses, ambulances, and pedestrians**.  
- **Emergency Vehicle Prioritization:** Calculates the **shortest path** and optimizes traffic lights for **emergency routes**.  
- **Traffic Light Management:** Alternating **NS/EW traffic lights** with real-time visualization.  
- **Real-Time Simulation:** Vehicles move smoothly along roads with **progress tracking** and animated emojis.  
- **Statistics Panel:** Displays **total vehicles, light states, pedestrians, and emergency status**.  
- **Adjustable Simulation Speed:** Control vehicle speed dynamically during runtime.

---

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/smart-city-traffic-simulation.git
cd smart-city-traffic-simulation
2. Install dependencies
pip install pygame networkx python-constraint
3. Run the simulation
python traffic_simulation.py
🎮 Controls
Key	Action
R	Restart simulation
SPACE	Pause / Resume simulation
UP	Increase vehicle speed
DOWN	Decrease vehicle speed
🧩 Technologies Used
Python 3.10+

Pygame for GUI and animation

NetworkX for graph-based routing

python-constraint for traffic light optimization

Object-Oriented Programming (OOP) for modular design
