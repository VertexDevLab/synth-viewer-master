import pandas as pd
import numpy as np
import math
from time import time
import requests
import yfinance as yf
import warnings

import os
import json
from datetime import datetime, timezone, timedelta
from helpers import from_iso_to_unix_time
from helpers import get_published_asset_price
from helpers import convert_prices_to_time_format
from helpers import get_real_price_path
from helpers import calculate_crps_for_miner
from helpers import align_prediction_and_real_prices

def analyze_trend(df, lookback_window=24):
    """Analyze recent price trend and momentum"""
    # Calculate various trend indicators
    df['returns'] = df['Close'].pct_change()
    df['sma'] = df['Close'].rolling(window=lookback_window).mean()
    df['momentum'] = df['Close'] / df['Close'].shift(lookback_window) - 1
    
    # Get latest values - use .iloc[-1] to get scalar values
    current_price = float(df['Close'].iloc[-1])  # Convert to float
    sma = float(df['sma'].iloc[-1]) if pd.notna(df['sma'].iloc[-1]) else None
    momentum = float(df['momentum'].iloc[-1])  # Convert to float
    recent_returns = df['returns'].tail(lookback_window)
    
    # Calculate trend strength
    trend_strength = 0
    
    # Price vs SMA
    if sma is not None and current_price > sma:  # Compare scalar values
        trend_strength += 1
    else:
        trend_strength -= 1
        
    # Momentum
    if momentum > 0:
        trend_strength += 1
    else:
        trend_strength -= 1
        
    # Recent returns
    if recent_returns.mean() > 0:
        trend_strength += 1
    else:
        trend_strength -= 1
        
    return trend_strength, momentum

def simulate_monte_trend_price_paths(start_time: str, initial_price: float, time_increment: int, time_length: int, num_simulations: int):
  warnings.filterwarnings('ignore')

  end_date = datetime.fromisoformat(start_time)
  start_date = end_date - timedelta(days=10)
  df = yf.download('BTC-USD', start=start_date, end=end_date, interval='1h')[['Close']]
#   df = yf.download('BTC-USD', start=start_date, end=end_date, interval='15m')[['Close']]

  # Analyze trend
  trend_strength, momentum = analyze_trend(df)
  print(f"\nTrend Analysis:")
  print(f"Trend Strength: {trend_strength} (-3 to +3 scale)")
  print(f"Momentum: {momentum:.2%}")
  
  # Calculation of volatility
  volatility_range = 48
  df['pct_change'] = df['Close'].pct_change()*100
  df['stdev'] = df['pct_change'].rolling(volatility_range).std()

  df['vol'] = df['stdev']*(350**0.5)
  df.dropna(inplace=True)

  sigma = df.vol.mean() / 100

  # Maturity remains
  T = 1/24

  # Risk-free rate calculation
  base_r = 0.0020 + 0.94 * 0.0438
  r = base_r * momentum * 100

  # Number of 5-min intervals in a day (24 hours * 12 intervals per hour)
  # M = 24 * 12  # 288 five-minute intervals
  M = int(time_length / time_increment)

  S0 = initial_price

  # Length of time interval (now in 5-min intervals)
  dt = T / M

  print("S0, initial price: \t", S0)
  print("▶ S, volatility: \t", sigma)
  print("▶ r, riskless short rate: ", r)
  print("M, 5-min intervals: \t", M)
  print("I, paths simulating: \t", num_simulations)

  # Simulating I paths with M 5-min intervals
  S = S0 * np.exp(np.cumsum((r - 0.5 * sigma ** 2) * dt + sigma * math.sqrt(dt) * np.random.standard_normal((M + 1, num_simulations)), axis=0))
  S[0] = S0

  return S.T

def simulate_crypto_price_paths(
    current_price, time_increment, time_length, num_simulations, start_time: str | None = None
):

    """
    Simulate multiple crypto asset price paths.
    """
    
    if start_time is None:
        start_time = datetime.now().isoformat()
    
    # Get the real price path for the past 7 days
    duration = 86400 * 7
    real_price_path = get_real_price_path(duration=duration, time_increment=1, resolution=5, start_time=start_time)
    
    # Calculate the volatility of the asset price path
    sigma, mean, stdev = _calc_params(history_data=real_price_path)
    simulations = simulate_monte_trend_price_paths(start_time, current_price, time_increment, time_length, num_simulations)

    predictions = convert_prices_to_time_format(
        simulations.tolist(), str(start_time), time_increment
    )
    # Create simulations directory in project root's public folder
    sim_dir = os.path.join("../../public/monte-trend", str(int(datetime.fromisoformat(start_time).timestamp())))
    os.makedirs(sim_dir, exist_ok=True)
    
    # Save the array to a JSON file in the timestamped directory
    filepath = os.path.join(sim_dir, "simulation.json")
    with open(filepath, 'w') as f:
        json.dump({
            "metadata": {
                "current_price": float(current_price),
                "time_increment": time_increment,
                "time_length": time_length,
                "num_simulations": num_simulations,
                "start_time": start_time

            },
            "prediction": predictions
        }, f, indent=2)
    print(f"Results saved to: {filepath}")
    
    return predictions

def _calc_params(history_data: list[dict]):
    """
    Calculate the volatility of the asset price path.
    """
    
    prices = np.array([price['price'] for price in history_data])
    
    # Percent changes in prices
    pct_changes = np.diff(prices) / prices[:-1]
    
    stdev = pct_changes.std()
    mean = pct_changes.mean()
    sigma = stdev * np.sqrt(300 / (7 * 24 * 3600))

    return sigma, mean, stdev

def main():

    start_time = "2025-02-01T23:30:00+00:00"

    publish_time = int(datetime.fromisoformat(start_time).timestamp())
    current_price = get_published_asset_price(
        asset="BTC",
        publish_time=publish_time
    )

    print(current_price)
    if current_price is None:
        raise ValueError("Current price is None")
    predictions = simulate_crypto_price_paths(
        current_price=current_price,
        time_increment=300,
        time_length=86400,
        num_simulations=100,
        start_time=start_time
    )
    real_path_file = os.path.join("../../public/real", str(publish_time), "real.json")
    if not os.path.exists(real_path_file):
        transformed_data = get_real_price_path(start_time=start_time)

        # Create simulations directory in project root's public folder
        sim_dir = os.path.join("../../public/real", str(publish_time))
        os.makedirs(sim_dir, exist_ok=True)

        # Save the transformed data directly to real.json
        filepath = os.path.join(sim_dir, "real.json")
        with open(filepath, 'w') as f:
            json.dump(transformed_data, f, indent=2)
        
        print(f"Real price path saved to: {filepath}")
    
    real_price_path = []
    with open(real_path_file, 'r') as f:
        real_price_path = json.load(f)
        
    predictions_path, real_price_path = align_prediction_and_real_prices(predictions, real_price_path)

    crps_score, detailed_crps_data = calculate_crps_for_miner(np.array(predictions_path), np.array(real_price_path), 300)
    
    # Save scores to score.json
    score_data = {
        "total_score": float(crps_score),  # Convert numpy float to Python float
        "detailed_scores": detailed_crps_data
    }
    
    print(f"😊😊😊 Total score: {crps_score}")
    
    # Create path and save file
    score_path = os.path.join("../../public/monte-trend", str(publish_time), "score.json")
    with open(score_path, 'w') as f:
        json.dump(score_data, f, indent=2)
    
    print(f"Score data saved to: {score_path}")

if __name__ == "__main__":
    main()
