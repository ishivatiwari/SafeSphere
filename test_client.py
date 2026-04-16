import requests
import json

# Define the endpoint
URL = "https://safesphere-api-321393039960.us-central1.run.app/analyze"

# Sample data provided in the prompt
data = [
  {"zone_id": "A1", "density": 85, "movement_speed": 1.2},
  {"zone_id": "B2", "density": 95, "movement_speed": 0.5}
]

print("Sending data to SafeSphere API...")
print(json.dumps(data, indent=2))
print("-" * 40)

try:
    response = requests.post(URL, json=data)
    response.raise_for_status() # Raise an exception for bad status codes
    
    print("Response received from SafeSphere API:")
    print("=" * 40)
    print(json.dumps(response.json(), indent=2))
    print("=" * 40)

except requests.exceptions.RequestException as e:
    print(f"Error connecting to API: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Detailed error: {e.response.text}")
