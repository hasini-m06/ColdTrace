# 🌡️ ColdTrace: AI-Driven Vaccine Cold Chain Risk Predictor

ColdTrace is a full-stack, predictive intelligence platform designed to proactively monitor and protect vaccine cold chains across Primary Health Centres (PHCs). By leveraging live meteorological data, historical power outage statistics, and machine learning, ColdTrace predicts the risk of vaccine spoilage *before* it happens.

---

## ✨ Key Features
- **Live Heatwave Tracking**: Integrates with the Open-Meteo API to fetch real-time 48-hour temperature forecasts for exact PHC GPS coordinates.
- **Machine Learning Risk Engine**: A Scikit-Learn `RandomForestClassifier` continuously analyzes weather deltas, historical wastage, and power reliability to generate predictive risk scores (0-100).
- **Automated Email Alerts**: Background cron jobs automatically dispatch tabular HTML email digests to subscribed health officials via the Resend API when high-risk thresholds are breached.
- **Geospatial Dashboard**: An interactive, dynamic dark-mode map built with React-Leaflet to visualize high-risk (Red), medium-risk (Amber), and safe (Green) zones instantly.
- **Secure Official Access**: JWT-secured authentication with role-based access, allowing registered officials to monitor specific facilities and customize alert subscriptions.
- **100% Serverless Deployment**: Configured for unified, full-stack deployment on Vercel (React Frontend + Python FastAPI Serverless Backend) with zero cold-starts.

## 🛠️ Tech Stack
**Frontend:**
- React 19 + Vite
- React-Leaflet (Geospatial Mapping)
- Recharts (Historical Trend Visualization)
- Axios (API Client)

**Backend (Python Serverless):**
- FastAPI (High-performance Async API)
- Scikit-Learn & Pandas (Machine Learning & Data Processing)
- APScheduler (Automated Data Cycles)
- SQLite (Relational Database)
- PyJWT & Passlib (Secure Authentication)

**External APIs & Data Sources:**
- [Open-Meteo](https://open-meteo.com/): Live 48-hour temperature forecasts.
- [OpenStreetMap Overpass API](https://overpass-api.de/): Dynamic geospatial fetching of PHC locations.
- [Data.gov.in](https://data.gov.in/): (Optional) Indian Government HMIS API for district-level wastage and power outage statistics.

---

## 🚀 Local Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/ColdTrace.git
cd ColdTrace
```

### 2. Backend Setup
```bash
# Navigate to backend
cd backend

# Create a virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # (On Windows use: venv\Scripts\activate)
pip install -r ../requirements.txt

# Create a .env file and add your secret keys (see .env.example)
# E.g., JWT_SECRET_KEY, ALLOW_INSECURE_DEV_KEY=true, RESEND_API_KEY
```

### 3. Frontend Setup
```bash
# Open a new terminal, navigate to frontend
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```

### 4. Running the application
- Start the FastAPI backend: `cd backend && uvicorn main:app --reload`
- Access the web app at `http://localhost:5173`

---

## 🌐 Production Deployment (Vercel)
This project is configured out-of-the-box for **Vercel Full-Stack Deployment**. 
Simply import the root directory to Vercel, ensure your environment variables are set in the Vercel dashboard, and Vercel will automatically build the Vite frontend and host the FastAPI endpoints via Python Serverless functions (`api/index.py`).
