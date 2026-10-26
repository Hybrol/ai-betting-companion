# ⚽ Portuguese AI Betting Companion & Paper-Trading Dashboard

An intelligent sports betting analysis companion and paper-trading platform specifically engineered for Portuguese licensed sportsbooks (**Betclic.pt**, **Betano.pt**, and **Solverde.pt**).

The companion leverages real-time odds ingestion, Poisson goal-expectation modeling, and multi-bookmaker market consensus to compute true outcome probabilities, calculate **Positive Expected Value (+EV)**, and recommend optimal bankroll stakes using the **Fractional Kelly Criterion**.

All simulated wagers are managed via an automated **fictional bankroll (paper trading)** system that tracks bankroll growth, Greens (Wins) vs Reds (Losses), Yield / ROI %, and drawdown.

---

## 🌟 Key Features

1. **Multi-Bookmaker Live Ingestion:**
   - Direct Angular SSR & REST API parsing for **Betclic.pt** and **Betano.pt**.
   - No brittle HTML scraping or expensive third-party APIs required.
   - Cross-bookmaker matching and entity normalization across major European leagues:
     - **Liga Portugal**
     - **Premier League**
     - **La Liga**
     - **Serie A**
     - **Bundesliga**
     - **UEFA Champions League**

2. **AI & Value Bet Engine:**
   - **Bivariate Poisson Goal Expectation:** Models team offensive and defensive ratings calibrated to league scoring baselines.
   - **Margin Removal (Fair Odds):** Strips bookmaker overround to derive true market implied probabilities.
   - **Positive EV (+EV) Detection:** Flags betting markets where $P_{\text{model}} \times \text{Odds} > 1.0 + \text{Threshold}$.
   - **Kelly Criterion Staking:** Dynamically sizes wagers based on edge and fictional bankroll size (default: 0.25x Quarter-Kelly with 5% max exposure cap).

3. **Paper-Trading & Bankroll Evolution:**
   - Starts with a customizable fictional bankroll (default: **1,000.00 €**).
   - Real-time resolution of match outcomes into **GREEN (Won)**, **RED (Lost)**, or **VOID (Push)**.
   - Full timeline history tracking cumulative P&L, Hit Rate %, ROI %, and peak-to-trough drawdown.

4. **Modern Full-Stack Architecture:**
   - **Backend:** Python 3.10+, FastAPI, SQLAlchemy, SQLite/PostgreSQL, APScheduler, httpx.
   - **Frontend:** Next.js (App Router), React, Tailwind CSS, Lucide Icons, Recharts.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+ & npm**
- **Git**

### 2. Backend Setup
```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
python run.py
```
* Backend API runs at: `http://localhost:8000`
* Interactive API Documentation (Swagger UI): `http://localhost:8000/docs`

### 3. Frontend Setup
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```
* Dashboard runs at: `http://localhost:3000`

---

## 📊 System Architecture

```
AI Betting Companion/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app & CORS configuration
│   │   ├── core/                # Settings & SQLAlchemy DB engine
│   │   ├── models/              # Schema: Matches, BookmakerOdds, Predictions, PaperBets, Bankroll
│   │   ├── scrapers/            # Real-time parsers for Betclic.pt, Betano.pt, Solverde.pt
│   │   ├── engine/              # Poisson predictor, EV scanner, Kelly staking, PaperTrader
│   │   └── api/                 # REST endpoints: /dashboard, /matches, /predictions, /paper-trading
│   ├── requirements.txt
│   └── run.py
├── frontend/                    # Next.js 14+ / React Dashboard
│   ├── src/
│   │   ├── app/                 # Pages: Overview, Matches & Odds, +EV Value Bets, Paper Bets
│   │   └── components/          # Recharts bankroll curve, Odds comparator, Bet slips
├── README.md
└── .gitignore
```

---

## 🛡️ License & Responsible Use
This software is intended strictly for mathematical modeling, statistical analysis, and simulated paper-trading education. Fictional bankroll trading involves zero real monetary risk.
