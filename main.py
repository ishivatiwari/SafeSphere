import os
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import genai
from google.genai import types

app = FastAPI(
    title="SafeSphere API", 
    description="Real-time crowd management AI Agent designed to prevent stampedes and manage large-scale events."
)

# --- Define Pydantic Models for Input ---
class ZoneInput(BaseModel):
    zone_id: str
    density: float
    movement_speed: float

# --- Define Pydantic Models for Output Schema ---
class ZoneStatus(BaseModel):
    zone_id: str
    density_level: str
    risk_level: str
    trend: str

class SafeSphereOutput(BaseModel):
    zone_status: List[ZoneStatus]
    actions: List[str]
    alerts: List[str]

# --- System Prompt Definition ---
SYSTEM_PROMPT = """You are SafeSphere, an intelligent crowd management system designed to prevent stampedes and manage large-scale events like Kumbh Mela.

Your job is to analyze crowd data across multiple zones and take real-time decisions to ensure safety and smooth movement.

=== YOUR TASK ===
For each zone:
1. Classify density:
   - 0–40 → Low
   - 41–70 → Medium
   - 71–90 → High
   - 91+ → Critical

2. Detect risk:
   - High density + low movement = High Risk
   - Critical density = Stampede Risk

3. Predict next state:
   - If density > 80 → Increasing risk
   - Else → Stable

4. Suggest actions:
   - Redirect crowd
   - Open alternative routes
   - Trigger alerts if critical

=== RULES ===
- Always prioritize human safety
- Keep responses structured and concise
- Avoid panic-inducing language
- Think like a real-time control system
"""

@app.post("/analyze", response_model=SafeSphereOutput)
def analyze_zones(zones: List[ZoneInput]):
    """
    Analyzes zone data using Gemini and returns structured risk assessments and actions.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500, 
            detail="GEMINI_API_KEY environment variable is not set. Please set it before running the server."
        )
    
    # Initialize the Gemini client
    client = genai.Client(api_key=api_key)
    
    # Format the input data
    input_data = [zone.model_dump() for zone in zones]
    user_prompt = f"=== INPUT ===\nYou will receive zone data in this format:\n{input_data}"

    try:
        # Note: We use gemini-2.5-flash as it is extremely fast and perfect for structured generation.
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=SafeSphereOutput,
                temperature=0.1, # Low temperature for more deterministic/logical outputs
            ),
        )
        
        # Parse the JSON string response back into our Pydantic model
        return SafeSphereOutput.model_validate_json(response.text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    # Cloud Run injects the PORT environment variable. Listen on it, defaulting to 8080 locally.
    port = int(os.environ.get("PORT", 8080))
    # Allow running the app directly via `python main.py`
    uvicorn.run("main:app", host="0.0.0.0", port=port)
