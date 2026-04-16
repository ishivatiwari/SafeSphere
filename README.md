# 🚨 SafeSphere AI

### Predictive Crowd Intelligence System for Large-Scale Events

SafeSphere AI is a real-time AI-powered system designed to **prevent stampedes, optimize crowd movement, and enhance safety** at large-scale events like the Kumbh Mela.

It leverages intelligent decision-making to analyze crowd density, detect risks, and provide actionable insights for authorities and attendees.

---

## 🌍 Problem Statement

Managing massive gatherings is extremely challenging due to:

* Unpredictable crowd surges
* High waiting times and congestion
* Lack of real-time coordination
* Risk of stampedes and safety hazards

SafeSphere AI addresses these issues using **predictive intelligence and real-time analysis**.

---

## 💡 Solution Overview

SafeSphere AI acts as a **central AI command system** that:

* Monitors crowd density across zones
* Detects high-risk and critical areas
* Predicts potential stampede situations
* Suggests dynamic rerouting strategies
* Generates real-time alerts

---

## 🧠 Key Features

* 📊 **Crowd Density Analysis**
* ⚠️ **Risk Detection (High / Critical / Stampede Risk)**
* 🔮 **Predictive Intelligence (Trend Analysis)**
* 🔀 **Smart Crowd Rerouting**
* 📢 **Real-Time Alerts & Recommendations**
* 🧩 **Structured JSON Output for Integration**

---

## 🏗️ Architecture (Prototype)

```
Simulated Crowd Data → AI Agent (Antigravity + Gemini) → Cloud Run API → JSON Response
```

> ⚡ Currently uses simulated data, but designed to integrate with CCTV, IoT sensors, and telecom signals.

---

## 🚀 Tech Stack

* **AI Agent Framework:** Antigravity
* **LLM:** Gemini
* **Backend:** Python (FastAPI / Flask)
* **Deployment:** Google Cloud Run
* **API Communication:** REST

---

## 📡 API Usage

### Endpoint

```
POST /analyze
```

### Request Body

```json
{
  "zones": [
    {"zone_id": "A1", "density": 85, "movement_speed": 1.2},
    {"zone_id": "B2", "density": 95, "movement_speed": 0.4}
  ]
}
```

### Sample Response

```json
{
  "zone_status": [
    {
      "zone_id": "B2",
      "density_level": "Critical",
      "risk_level": "Stampede Risk",
      "trend": "Increasing"
    }
  ],
  "actions": [
    "Redirect crowd from Zone B2 to Zone C1",
    "Open additional exit gates in Zone B2"
  ],
  "alerts": [
    "Avoid Zone B2 due to heavy congestion"
  ]
}
```

---

## 🛠️ Setup & Deployment

### 1. Clone the Repository

```
git clone https://github.com/YOUR_USERNAME/safesphere-api.git
cd safesphere-api
```

### 2. Install Dependencies

```
pip install -r requirements.txt
```

### 3. Set Environment Variables

```
GEMINI_API_KEY=your_api_key_here
```

### 4. Run Locally

```
python app.py
```

### 5. Deploy (Cloud Run)

```
gcloud run deploy safesphere-api --source .
```

---

## 🔐 Security Note

* API keys are stored using environment variables
* In production, use **Secret Manager** for secure handling

---

## 🎯 Use Cases

* Religious gatherings (e.g., Kumbh Mela)
* Sports stadiums
* Concerts and festivals
* Public events and rallies

---

## 📈 Future Enhancements

* Real-time CCTV integration
* IoT sensor-based crowd tracking
* Live dashboard with heatmaps
* Emergency response automation
* Multi-agent orchestration

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

## 📌 Disclaimer

This is a prototype system built for demonstration purposes.
It uses simulated data but is designed for real-world scalability.

---

## 👨‍💻 Author

Developed by Shiva

---

## ⭐ If you like this project

Give it a ⭐ on GitHub and share your feedback!
