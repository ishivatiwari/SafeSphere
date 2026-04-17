# 🚨 SafeSphere AI

### Predictive Crowd Intelligence System for Large-Scale Events

SafeSphere AI is an AI-powered system designed to **predict, prevent, and manage crowd risks** in large-scale events like the Kumbh Mela.
It enables real-time decision-making to avoid stampedes, optimize crowd movement, and improve public safety.

---

## 🌍 Problem Statement

Large gatherings often suffer from:

* Sudden crowd surges
* Poor real-time visibility
* Lack of predictive intelligence
* High risk of stampedes

Traditional systems are **reactive**, responding only after congestion occurs.

---

## 💡 Solution

SafeSphere AI introduces a **predictive AI command system** that:

* Monitors crowd density across zones
* Detects high-risk and critical areas
* Predicts crowd buildup trends
* Suggests dynamic rerouting strategies
* Generates real-time alerts

---

## 🧠 Key Features

* 📊 Crowd Density Analysis
* ⚠️ Risk Detection (High / Critical / Stampede Risk)
* 🔮 Predictive Intelligence (Trend Forecasting)
* 🔀 Smart Crowd Rerouting
* 📢 Real-Time Alerts
* 🧩 Structured JSON API for easy integration

---

## 🏗️ System Architecture

```text
Simulated Data → AI Agent (Antigravity + Gemini) → Cloud Run API → JSON Response
```

### 🔗 Google Cloud Integration

* Deployed on **Google Cloud Run** (serverless, scalable)
* Uses **Gemini API** for AI decision-making
* Designed for integration with:

  * Google Firestore (real-time data storage)
  * Pub/Sub (event-driven updates)
  * Cloud Logging (monitoring & debugging)

---

## ⚙️ Efficiency & Performance

* Lightweight processing for **low-latency responses**
* Optimized decision logic to minimize compute overhead
* Designed for **real-time scalability** using serverless architecture
* Supports future enhancements like caching and batch processing

---

## 🔐 Security

* API keys managed via **environment variables**
* Secure deployment using Google Cloud infrastructure
* Designed with **controlled access patterns**

---

## ♿ Accessibility

* Simple and intuitive REST API
* Structured JSON responses for easy consumption
* Clear error handling and validation
* Designed for integration with dashboards and assistive systems

---

## 📡 API Usage

### Endpoint

```
POST /analyze
```

### Request Example

```json
{
  "zones": [
    {"zone_id": "A1", "density": 85, "movement_speed": 1.2},
    {"zone_id": "B2", "density": 95, "movement_speed": 0.4}
  ]
}
```

### Response Example

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
    "Redirect crowd from Zone B2 to Zone C1"
  ],
  "alerts": [
    "Avoid Zone B2 due to heavy congestion"
  ]
}
```

---

## 🧪 Testing

Basic test coverage is implemented to validate core functionality.

### Example Test Case

```python
def test_analyze_endpoint():
    response = client.post("/analyze", json={
        "zones": [{"zone_id": "A1", "density": 90, "movement_speed": 0.5}]
    })
    assert response.status_code == 200
```

### Test Coverage Includes:

* ✅ Normal scenarios
* ⚠️ High-risk scenarios
* ❗ Edge cases (empty input / invalid data)

---

## 🛠️ Setup & Deployment

### 1. Clone Repository

```
git clone https://github.com/YOUR_USERNAME/safesphere.git
cd safesphere
```

### 2. Install Dependencies

```
pip install -r requirements.txt
```

### 3. Configure Environment

```
GEMINI_API_KEY=your_api_key_here
```

### 4. Run Locally

```
python app.py
```

### 5. Deploy to Cloud Run

```
gcloud run deploy safesphere-api --source .
```

---

## 🎯 Use Cases

* Religious gatherings (e.g., Kumbh Mela)
* Sports stadiums
* Concerts and festivals
* Smart city crowd management

---

## 📈 Future Enhancements

* Real-time CCTV integration
* IoT sensor-based tracking
* Live dashboard with heatmaps
* Automated emergency response system
* Multi-agent orchestration

---

## 📌 Disclaimer

This is a prototype system using simulated data, designed for demonstration and scalability.

---

## 👨‍💻 Author

Developed by Shiva Tiwari

---

## ⭐ Support

If you find this project useful, consider giving it a ⭐ on GitHub!
