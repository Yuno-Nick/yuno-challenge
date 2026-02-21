# Oasis Rides - Real-Time Fraud Detection Pipeline

A real-time fraud detection pipeline and intelligence dashboard for Oasis Rides, a ride-hailing platform operating across Nigeria, Kenya, and South Africa.

## Architecture

```
                    +-------------------+
                    |  Transaction CSV  |
                    |  (1,200+ txns)    |
                    +--------+----------+
                             |
                    +--------v----------+
                    |  FastAPI Backend   |
                    |  - Stream Simulator|
                    |  - Fraud Pipeline  |
                    |  - Risk Scoring    |
                    |  - ML Model        |
                    +--------+----------+
                             |
                    +--------v----------+
                    |  Supabase (PG)    |
                    |  - transactions   |
                    |  - risk_assessments|
                    |  - ml_models      |
                    +--------+----------+
                             |
                    +--------v----------+
                    |  Streamlit        |
                    |  Dashboard        |
                    |  - Real-time      |
                    |  - Pattern Charts |
                    |  - ML Metrics     |
                    |  - Advanced Detect|
                    +-------------------+
```

## Tech Stack

- **Backend**: Python FastAPI
- **Dashboard**: Streamlit + Plotly
- **Database**: Supabase (PostgreSQL)
- **ML**: scikit-learn (Random Forest + Isolation Forest)
- **Deployment**: Render (Docker)

## Fraud Detection Approach

### Rule-Based Indicators (Core)
| Indicator | What it Detects | Weight |
|-----------|----------------|--------|
| Velocity | 10+ transactions per user/card in 1-2 hours | 25% |
| Geographic | Impossible travel (Lagos to Nairobi in 15 min) | 25% |
| Card Testing | Small probes (< $5) followed by large charges (> $50) | 20% |
| Amount | Z-score > 2-3 standard deviations from user average | 15% |
| Collusion | Same driver-passenger pair 8+ rides in a week | 5% |
| Account Takeover | New card + new country within 30 minutes | 5% |
| Fraud Ring | 3+ users sharing the same device | 5% |

### ML Scoring (Stretch Goal)
- **Model**: Random Forest (primary) + Isolation Forest (anomaly backup)
- **Features**: All 7 indicator scores + amount, distance, duration, hour, day of week
- **Hybrid Score**: `final = 0.4 * rule_score + 0.6 * ml_score`
- **Risk Levels**: Low (< 30), Medium (30-59), High (60+)

## Quick Start

### Prerequisites
- Python 3.11+
- Supabase account (free tier: https://supabase.com)

### 1. Clone and Install
```bash
cd yuno-challenge
pip install -r requirements.txt
```

### 2. Set Up Supabase
1. Create a new project at [supabase.com](https://supabase.com)
2. Go to SQL Editor and run the contents of `schema.sql`
3. Copy your project URL and anon key

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Supabase credentials:
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_KEY=your-anon-key
```

### 4. Generate Test Data
```bash
python data/generate_transactions.py
```
This generates 1,200+ transactions including planted fraud patterns.

### 5. Start the API
```bash
uvicorn app.main:app --reload --port 8000
```

### 6. Start the Dashboard
```bash
streamlit run dashboard/app.py
```

### 7. Run the Pipeline
1. Open the dashboard at http://localhost:8501
2. Click "Start" in the sidebar to begin processing
3. Watch transactions get processed in real-time with risk scores
4. Navigate to Pattern Analysis for fraud visualizations
5. Train the ML model on the ML Performance page

## Deployment on Render

### Option 1: Using render.yaml (Blueprint)
1. Push code to GitHub
2. Go to [render.com](https://render.com) > New > Blueprint
3. Connect your repo and select `render.yaml`
4. Add environment variables (SUPABASE_URL, SUPABASE_KEY)
5. Deploy

### Option 2: Manual
1. Create Web Service for API:
   - Docker, `Dockerfile.api`, port 8000
2. Create Web Service for Dashboard:
   - Docker, `Dockerfile.dashboard`, port 8501
   - Set `API_URL` env var to the API service URL

## Test Data

Generated dataset includes:
- **~1,000 normal transactions** across Lagos, Abuja, Nairobi, Mombasa, Johannesburg, Cape Town
- **6 card testing patterns**: 3-5 small transactions followed by large charges
- **4 velocity fraud users**: 10-15 transactions in 2-hour windows
- **3 geographic anomalies**: Impossible travel between countries in 15 minutes
- **3 collusion pairs**: 8-12 rides between same driver-passenger in a week
- **2 account takeovers**: New card + new country within 30 minutes
- **1 fraud ring**: 5 users sharing 2 devices with similar transaction amounts

## Dashboard Pages

1. **Home**: KPIs overview + pipeline controls
2. **Real-Time Monitor**: Live transaction feed + high-risk alerts with triggered rules
3. **Pattern Analysis**: 6 interactive charts (fraud by country, risk distribution, timeline, amounts, heatmap)
4. **ML Performance**: Model metrics (precision/recall/F1), confusion matrix, ROC curve, feature importance
5. **Advanced Detection**: Collusion pairs, account takeover signals, fraud ring network graph

## Written Summary

This system uses a hybrid approach combining rule-based fraud detection with machine learning to identify fraudulent ride-hailing transactions in real-time. The rule-based engine evaluates 7 indicators (velocity, geographic anomalies, amount anomalies, card testing, collusion, account takeover, and fraud rings) with weighted scoring, while the ML component (Random Forest) learns from labeled historical data to predict fraud probability. The hybrid score (40% rules + 60% ML) provides both interpretability and accuracy.

The system successfully detects all planted fraud patterns in the test data: card testing sequences are flagged with scores of 70-95, velocity fraud users hit 80-100, geographic anomalies (impossible travel) consistently score 100, and collusion patterns are identified through driver-passenger pair frequency analysis. The dashboard provides real-time visibility with auto-refreshing metrics, interactive charts, and detailed alert breakdowns showing exactly which rules triggered.

With more time, the most impactful improvement would be implementing a feedback loop where operations team decisions (confirm/dismiss alerts) feed back into the ML model for continuous retraining, improving precision over time and reducing false positives.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/transactions` | Ingest single transaction |
| POST | `/api/transactions/batch` | Ingest batch |
| GET | `/api/transactions` | List transactions |
| GET | `/api/dashboard/metrics` | Fraud metrics |
| GET | `/api/dashboard/alerts` | High-risk alerts |
| GET | `/api/dashboard/patterns` | Pattern data |
| POST | `/api/pipeline/start` | Start pipeline |
| POST | `/api/pipeline/stop` | Stop pipeline |
| GET | `/api/pipeline/status` | Pipeline status |
| POST | `/api/ml/train` | Train ML model |
| GET | `/api/ml/metrics` | Model metrics |
| GET | `/api/health` | Health check |
