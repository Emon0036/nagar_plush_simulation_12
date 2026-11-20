from typing import Dict, Any, Tuple

class CityEnvironment:
    """
    Virtual 2D City Environment.
    Houses, workplaces, markets, banks, education centers, and city center
    laid out on an interactive grid map.
    """
    def __init__(self, width: int = 24, height: int = 16):
        self.width = width
        self.height = height
        self.hubs = {
            "housing": {
                "id": "housing",
                "name": "Residential Quarter",
                "category": "Living",
                "x": 2, "y": 2, "w": 5, "h": 4,
                "door": (4, 6),
                "color": "#3B82F6", # Blue
                "icon": "home",
                "description": "Housing and apartments for citizen families"
            },
            "workplace": {
                "id": "workplace",
                "name": "Industrial & Tech Park",
                "category": "Employment",
                "x": 10, "y": 2, "w": 5, "h": 4,
                "door": (12, 6),
                "color": "#10B981", # Emerald
                "icon": "building",
                "description": "Offices, software companies, and manufacturing hubs"
            },
            "market": {
                "id": "market",
                "name": "Central Bazaar",
                "category": "Commerce",
                "x": 18, "y": 2, "w": 4, "h": 4,
                "door": (18, 6),
                "color": "#F59E0B", # Amber
                "icon": "shopping-bag",
                "description": "Essential food, groceries, clothing, and retail markets"
            },
            "bank": {
                "id": "bank",
                "name": "City Commercial Bank",
                "category": "Finance",
                "x": 2, "y": 10, "w": 5, "h": 4,
                "door": (4, 10),
                "color": "#8B5CF6", # Purple
                "icon": "landmark",
                "description": "Savings deposits, business credit, and microfinance"
            },
            "education": {
                "id": "education",
                "name": "University & Academy",
                "category": "Education",
                "x": 10, "y": 10, "w": 5, "h": 4,
                "door": (12, 10),
                "color": "#06B6D4", # Cyan
                "icon": "graduation-cap",
                "description": "Higher education, vocational training, and skill development"
            },
            "city_center": {
                "id": "city_center",
                "name": "City Hall & Center",
                "category": "Governance",
                "x": 18, "y": 10, "w": 4, "h": 4,
                "door": (18, 10),
                "color": "#EC4899", # Pink
                "icon": "flag",
                "description": "Municipal government, civic administration, and public transit hub"
            }
        }

    def get_door(self, hub_name: str) -> Tuple[int, int]:
        hub = self.hubs.get(hub_name, self.hubs["housing"])
        return hub["door"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "hubs": self.hubs
        }

city_env = CityEnvironment()
