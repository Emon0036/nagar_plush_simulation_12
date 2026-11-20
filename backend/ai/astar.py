import heapq
import math
from typing import List, Tuple, Dict, Optional, Set

GridCoord = Tuple[int, int]

class AStarPathfinder:
    """
    A* Search Pathfinding Algorithm for virtual city navigation.
    Guides autonomous citizen agents through walkable road networks
    between functional city hubs (Homes, Workplaces, Markets, Banks, Schools).
    """
    def __init__(self, width: int = 24, height: int = 16):
        self.width = width
        self.height = height
        self.obstacles: Set[GridCoord] = set()
        self.road_nodes: Set[GridCoord] = set()
        self._init_default_city_layout()

    def _init_default_city_layout(self):
        """
        Creates a realistic urban street grid with building blocks and intersecting avenues.
        Walkable roads form the primary transit grid, while building interiors connect at doorways.
        """
        # Define building zones as obstacles to pass through (doors act as access nodes)
        # Hub footprints (x_start, y_start, width, height)
        self.building_zones = {
            "housing": {"box": (2, 2, 5, 4), "door": (4, 6), "label": "Residential Quarter"},
            "workplace": {"box": (10, 2, 5, 4), "door": (12, 6), "label": "Industrial & Tech Park"},
            "market": {"box": (18, 2, 4, 4), "door": (18, 6), "label": "Central Bazaar"},
            "bank": {"box": (2, 10, 5, 4), "door": (4, 10), "label": "Commercial Bank"},
            "education": {"box": (10, 10, 5, 4), "door": (12, 10), "label": "University & Academy"},
            "city_center": {"box": (18, 10, 4, 4), "door": (18, 10), "label": "City Hall & Center"}
        }

        # Mark building interiors as obstacles (except doors)
        for hub_key, hub_data in self.building_zones.items():
            bx, by, bw, bh = hub_data["box"]
            dx, dy = hub_data["door"]
            for x in range(bx, bx + bw):
                for y in range(by, by + bh):
                    if (x, y) != (dx, dy):
                        self.obstacles.add((x, y))

    def heuristic(self, a: GridCoord, b: GridCoord, mode: str = "manhattan") -> float:
        if mode == "euclidean":
            return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
        # Default Manhattan distance for city grid
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_neighbors(self, node: GridCoord) -> List[GridCoord]:
        x, y = node
        candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        valid = []
        for nx, ny in candidates:
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if (nx, ny) not in self.obstacles:
                    valid.append((nx, ny))
        return valid

    def find_path(self, start: GridCoord, goal: GridCoord) -> List[GridCoord]:
        """
        Computes the shortest collision-free path from start to goal using A*.
        Returns a list of coordinates [(x0, y0), (x1, y1), ..., (xn, yn)].
        """
        if start == goal:
            return [start]
        
        # If start or goal is an obstacle, find closest adjacent walkable cell
        if start in self.obstacles:
            start_neighbors = self.get_neighbors(start)
            if start_neighbors:
                start = start_neighbors[0]
        if goal in self.obstacles:
            goal_neighbors = self.get_neighbors(goal)
            if goal_neighbors:
                goal = goal_neighbors[0]

        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from: Dict[GridCoord, Optional[GridCoord]] = {start: None}
        cost_so_far: Dict[GridCoord, float] = {start: 0.0}

        while frontier:
            _, current = heapq.heappop(frontier)

            if current == goal:
                break

            for neighbor in self.get_neighbors(current):
                new_cost = cost_so_far[current] + 1.0 # Uniform step cost on grid
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + self.heuristic(neighbor, goal)
                    heapq.heappush(frontier, (priority, neighbor))
                    came_from[neighbor] = current

        # Reconstruct path
        if goal not in came_from:
            # Fallback direct step if unreachable
            return [start, goal]

        path = []
        curr: Optional[GridCoord] = goal
        while curr is not None:
            path.append(curr)
            curr = came_from.get(curr)
        path.reverse()
        return path

    def get_hub_door(self, hub_name: str) -> GridCoord:
        if hub_name in self.building_zones:
            return self.building_zones[hub_name]["door"]
        return (4, 6) # Default to residential door

pathfinder = AStarPathfinder()
