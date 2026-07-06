"""
WellFinanced — Feature 1: Predictive Income Forecasting
Uses an advanced Global LSTM model to predict a freelancer's income 
for the next 3-6 months with high accuracy.
"""

import pandas as pd
import numpy as np
import warnings
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings("ignore")

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_loader import load_income

def _calculate_stability_score(monthly_income: pd.Series) -> float:
    """Calculate income stability score (0-100)."""
    if len(monthly_income) < 2 or monthly_income.mean() == 0:
        return 0.0
    cv = monthly_income.std() / monthly_income.mean()
    score = max(0, min(100, 100 * (1 - cv / 2)))
    return round(score, 1)

def _calculate_platform_diversity(user_id: str) -> float:
    """Calculate Shannon entropy of platform usage as a diversity score."""
    income = load_income()
    user_income = income[income["user_id"] == user_id]
    if user_income.empty:
        return 0.0
    platform_counts = user_income["platform"].value_counts(normalize=True)
    entropy = -np.sum(platform_counts * np.log2(platform_counts + 1e-10))
    max_entropy = np.log2(len(platform_counts)) if len(platform_counts) > 1 else 1
    return round(entropy / max_entropy, 2) if max_entropy > 0 else 0.0

def _get_global_monthly_income() -> pd.DataFrame:
    """Fetch and aggregate monthly income for ALL users to build a robust global dataset."""
    income = load_income()
    monthly_all = []
    
    for uid, user_income in income.groupby('user_id'):
        monthly = user_income.groupby("month").agg(
            total_income=("amount", "sum"),
            num_projects=("amount", "count"),
            num_platforms=("platform", "nunique"),
        ).reset_index()

        full_range = pd.date_range(start=monthly["month"].min(), end=monthly["month"].max(), freq="MS")
        monthly = monthly.set_index("month").reindex(full_range, fill_value=0).reset_index()
        monthly.rename(columns={"index": "month"}, inplace=True)
        
        non_zero = monthly[monthly["total_income"] > 0]["total_income"]
        if len(non_zero) > 0:
            cap = non_zero.median() * 3
            monthly["total_income"] = monthly["total_income"].clip(upper=cap)
            
        monthly['user_id'] = uid
        monthly_all.append(monthly)

    return pd.concat(monthly_all, ignore_index=True)

def _prepare_global_features(df_all: pd.DataFrame) -> pd.DataFrame:
    """Engineer global features: month_of_year, lag_1, lag_2, rolling_mean_3."""
    df = df_all.copy()
    df = df.sort_values(by=['user_id', 'month'])
    
    df['month_of_year'] = df['month'].dt.month
    df['lag_1'] = df.groupby('user_id')['total_income'].shift(1)
    df['lag_2'] = df.groupby('user_id')['total_income'].shift(2)
    df['rolling_mean_3'] = df.groupby('user_id')['total_income'].transform(lambda x: x.rolling(3, min_periods=1).mean())
    
    df = df.dropna().copy()
    return df

def forecast_income(user_id: str, months_ahead: int = 3) -> dict:
    """
    Main API: Train Global LSTM on the fly and forecast income for a user.
    """
    df_all = _get_global_monthly_income()
    df_features = _prepare_global_features(df_all)
    
    user_data = df_features[df_features['user_id'] == user_id]
    
    if user_data.empty or len(user_data) < 3:
        return {
            "predicted_income": [], "avg_predicted": 0, "stability_score": 0,
            "platform_diversity": 0, "model_used": "insufficient_data",
            "historical": [], "error": "Not enough data for forecasting (minimum 3 months required)."
        }

    features = ['lag_1', 'lag_2', 'rolling_mean_3', 'month_of_year', 'num_projects', 'num_platforms']
    
    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()
    
    X_global = df_features[features]
    y_global = df_features['total_income']
    
    X_scaled = scaler_X.fit_transform(X_global)
    y_scaled = scaler_y.fit_transform(y_global.values.reshape(-1, 1))
    
    X_lstm = X_scaled.reshape((X_scaled.shape[0], 1, X_scaled.shape[1]))
    
    # Define and train Global LSTM
    tf.random.set_seed(42)
    np.random.seed(42)
    model = Sequential([
        LSTM(64, activation='relu', input_shape=(1, X_lstm.shape[2])),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    model.fit(X_lstm, y_scaled, epochs=25, batch_size=16, verbose=0)
    
    # Iterative Prediction Logic
    last_row = user_data.iloc[-1]
    curr_lag1 = last_row['total_income']
    curr_lag2 = last_row['lag_1']
    curr_roll_hist = list(user_data['total_income'].tail(2).values) + [curr_lag1]
    
    recent_projects = user_data["num_projects"].tail(3).mean()
    recent_platforms = user_data["num_platforms"].tail(3).mean()
    
    last_month = user_data["month"].max()
    future_months = pd.date_range(start=last_month + pd.DateOffset(months=1), periods=months_ahead, freq="MS")
    
    preds = []
    std = user_data["total_income"].std()
    
    for m in future_months:
        roll_mean = np.mean(curr_roll_hist[-3:])
        
        feat_df = pd.DataFrame([[curr_lag1, curr_lag2, roll_mean, m.month, recent_projects, recent_platforms]], columns=features)
        feat_scaled = scaler_X.transform(feat_df)
        feat_lstm = feat_scaled.reshape(1, 1, len(features))
        
        p_scaled = model.predict(feat_lstm, verbose=0)[0][0]
        p = max(0, float(scaler_y.inverse_transform([[p_scaled]])[0][0]))
        
        preds.append({
            "month": m.strftime("%Y-%m"),
            "amount": round(p, 2),
            "lower_bound": round(max(0, p - 1.28 * std), 2),
            "upper_bound": round(p + 1.28 * std, 2),
        })
        
        curr_lag2 = curr_lag1
        curr_lag1 = p
        curr_roll_hist.append(p)
        
    avg_predicted = round(np.mean([p["amount"] for p in preds]), 2)
    stability_score = _calculate_stability_score(user_data["total_income"])
    platform_diversity = _calculate_platform_diversity(user_id)
    
    historical = [
        {"month": row["month"].strftime("%Y-%m"), "amount": round(row["total_income"], 2)}
        for _, row in df_all[df_all['user_id'] == user_id].iterrows()
    ]
    
    return {
        "predicted_income": preds,
        "avg_predicted": avg_predicted,
        "stability_score": stability_score,
        "platform_diversity": platform_diversity,
        "model_used": "global_lstm",
        "historical": historical
    }

def evaluate_forecast(user_id: str) -> dict:
    """
    Evaluate forecast accuracy using a chronological 80/20 train/test split.
    Trains on 80% of ALL users, tests specifically on the 20% belonging to user_id.
    """
    df_all = _get_global_monthly_income()
    df_features = _prepare_global_features(df_all)
    
    user_data = df_features[df_features['user_id'] == user_id]
    
    if user_data.empty or len(user_data) < 5:
        return {
            "error": "Need at least 5 months for evaluation.",
            "model_used": "insufficient_data"
        }
        
    train_list = []
    test_list = []
    
    for uid, group in df_features.groupby('user_id'):
        split_idx = int(len(group) * 0.8)
        if split_idx > 0:
            train_list.append(group.iloc[:split_idx])
            test_list.append(group.iloc[split_idx:])
            
    train_df = pd.concat(train_list)
    test_df = pd.concat(test_list)
    
    features = ['lag_1', 'lag_2', 'rolling_mean_3', 'month_of_year', 'num_projects', 'num_platforms']
    
    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()
    
    X_train = scaler_X.fit_transform(train_df[features])
    y_train = scaler_y.fit_transform(train_df['total_income'].values.reshape(-1, 1))
    
    X_test = scaler_X.transform(test_df[features])
    y_test = test_df['total_income'].values
    
    X_train_lstm = X_train.reshape((X_train.shape[0], 1, X_train.shape[1]))
    X_test_lstm = X_test.reshape((X_test.shape[0], 1, X_test.shape[1]))
    
    tf.random.set_seed(42)
    np.random.seed(42)
    model = Sequential([
        LSTM(64, activation='relu', input_shape=(1, X_train_lstm.shape[2])),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    model.fit(X_train_lstm, y_train, epochs=25, batch_size=16, verbose=0)
    
    # Evaluate ONLY on the requested user's test set
    user_test_mask = test_df['user_id'] == user_id
    if user_test_mask.sum() == 0:
        return {"error": f"No test data available for {user_id}."}
        
    X_user_test = X_test_lstm[user_test_mask]
    y_user_actual = y_test[user_test_mask]
    months_user = test_df[user_test_mask]['month']
    
    preds_scaled = model.predict(X_user_test, verbose=0)
    preds = scaler_y.inverse_transform(preds_scaled).flatten()
    
    mae = mean_absolute_error(y_user_actual, preds)
    rmse = np.sqrt(mean_squared_error(y_user_actual, preds))
    r2 = r2_score(y_user_actual, preds)
    
    non_zero = y_user_actual > 0
    if non_zero.any():
        mape = np.mean(np.abs((y_user_actual[non_zero] - preds[non_zero]) / y_user_actual[non_zero])) * 100
    else:
        mape = 0.0
        
    acc = max(0, 100 - mape)
    
    actuals_list = [
        {"month": m.strftime("%Y-%m"), "amount": round(float(a), 2)}
        for m, a in zip(months_user, y_user_actual)
    ]
    preds_list = [
        {"month": m.strftime("%Y-%m"), "amount": round(float(p), 2)}
        for m, p in zip(months_user, preds)
    ]
    
    return {
        "mae": round(float(mae), 2),
        "mape": round(float(mape), 2),
        "rmse": round(float(rmse), 2),
        "r2_score": round(float(r2), 4),
        "accuracy": round(float(acc), 2),
        "n_train": len(train_df[train_df['user_id'] == user_id]),
        "n_test": len(y_user_actual),
        "model_used": "global_lstm",
        "actuals": actuals_list,
        "predictions": preds_list,
    }

if __name__ == "__main__":
    print("Testing Global LSTM Forecast...")
    result = forecast_income("user_0001", months_ahead=3)
    if "error" in result:
        print(result["error"])
    else:
        print(f"Model used: {result['model_used']}")
        print(f"Stability score: {result['stability_score']}")
        print(f"Average predicted income: {result['avg_predicted']:,.2f}")
        print("Predictions:")
        for p in result["predicted_income"]:
            print(f"  {p['month']}: {p['amount']:,.2f}")
            
    print("\n" + "="*40)
    print("Testing Global LSTM Evaluation...")
    print("="*40)
    eval_result = evaluate_forecast("user_0001")
    if "error" in eval_result:
        print(eval_result["error"])
    else:
        print(f"MAE: {eval_result['mae']:,.2f} EGP")
        print(f"R² Score: {eval_result['r2_score']}")
        print(f"Estimated Accuracy: {eval_result['accuracy']}%")
        print("\nActual vs Predicted:")
        for a, p in zip(eval_result["actuals"], eval_result["predictions"]):
            print(f"  {a['month']}: actual={a['amount']:,.2f}, predicted={p['amount']:,.2f}")
