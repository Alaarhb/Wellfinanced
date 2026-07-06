# WellFinanced AI Engine 

<div align="center">
  <p><strong>The intelligent backend powering autonomous financial management for freelancers.</strong></p>
</div>

## 📌 Overview
WellFinanced is an AI-driven platform designed specifically for freelancers to conquer income volatility. This repository contains the **Core AI Engine**, featuring state-of-the-art Machine Learning models and RAG architectures that provide intelligent forecasting, cashflow smoothing, and personalized financial advice.

## ✨ Core AI Features

### 1. 📈 Predictive Income Forecasting (Global LSTM)
Freelance income is notoriously unstable. Instead of building weak local models, we utilize a **Global Panel Data Architecture**.
- **Model:** Deep Learning LSTM (Long Short-Term Memory) trained globally on thousands of data points across all users.
- **Features:** Autoregressive Lags, Rolling Averages, and Seasonality Extraction (`month_of_year`).
- **Output:** Predicts future income with an 80% Confidence Interval (Lower/Upper bounds) and computes a mathematical **Stability Score** (0-100) using the Coefficient of Variation.

### 2. 🌊 Intelligent Cashflow Smoothing
Analyzes historical expense patterns to categorize spending and recommends dynamic buffering strategies.
- **Model:** Time-Series Analysis and Clustering.
- **Goal:** Suggests an optimal "Cash Buffer" to survive dry months without taking on debt based on predicted income dips.

### 3. 💳 Autonomous Debt Prioritization
An intelligent algorithm that evaluates active debts (Credit Cards, Personal Loans) and prescribes the mathematically optimal payoff strategy.
- **Algorithms:** Supports both **Debt Avalanche** (interest-optimized) and **Debt Snowball** (psychology-optimized).
- **Goal:** Minimizes total interest paid while dynamically adjusting to the freelancer's fluctuating cashflow.

### 4. 🤖 RAG-Based Behavioral Financial Advisor
A personalized AI assistant that understands the freelancer's specific financial context.
- **Architecture:** Retrieval-Augmented Generation (RAG) using **ChromaDB** as a vector store.
- **Knowledge Base:** Indexed with professional financial advising literature and behavioral economics.
- **Goal:** Provides highly contextual, actionable advice based on the user's real-time financial health, debts, and forecasted income.

## 🛠️ Technology Stack
- **Data Manipulation:** `pandas`, `numpy`
- **Machine Learning:** `scikit-learn` (Random Forest, Clustering)
- **Deep Learning:** `TensorFlow`, `Keras` (LSTM Time-Series Forecasting)
- **Generative AI & NLP:** `LangChain`, `ChromaDB`, LLMs
- **Environment:** `Jupyter Notebooks` (for ML experimentation), `Python` (Production Modules)

## 📂 Project Structure
```text
WellFinanced/
├── data/                  # Mocked historical datasets (Income, Expenses, Users)
├── features/              # Production-ready AI modules
│   ├── income_forecast.py # Global LSTM Forecasting API
│   ├── cashflow_smoothing.py
│   ├── expense_analyzer.py
│   └── financial_advisor.py # RAG & Vector DB Logic
├── utils/                 # Shared data loaders and preprocessing scripts
├── knowledge/             # Documents used for RAG vectorization
└── create_nb.py           # Automated Jupyter Notebook generation for ML visualization
```

## 🚀 Getting Started

1. **Install dependencies:**
   ```bash
   pip install pandas numpy scikit-learn tensorflow langchain chromadb
   ```
2. **Test the Income Forecaster:**
   ```bash
   python features/income_forecast.py
   ```
3. **Generate the ML Visualization Notebook:**
   ```bash
   python create_nb.py
   ```
