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

def simulate_monte_claude_price_paths(initial_price: float, time_increment: int, time_length: int, num_simulations: int, sigma: float):
  T = 1/3

  # Risk-free rate calculation
  r = 0.0020 + 0.94 * 0.0438

  # Number of 5-min intervals in a day (24 hours * 12 intervals per hour)
  M = int(time_length / time_increment)

  S0 = initial_price

  # Length of time interval (now in 5-min intervals)
  dt = T / M

  # Simulating I paths with M 5-min intervals
  S = S0 * np.exp(np.cumsum((0 - 0.5 * sigma ** 2) * dt + sigma * math.sqrt(dt) * np.random.standard_normal((M + 1, num_simulations)), axis=0))
  S[0] = S0

  return S.T

def generate_simulations(
    current_price, time_increment, time_length, num_simulations, start_time: str | None = None
):

    """
    Simulate multiple crypto asset price paths.
    """
    
    if start_time is None:
        start_time = datetime.now().isoformat()

    end_date = datetime.fromisoformat(start_time)
    start_date = end_date - timedelta(days=30)
    volatility_days = 30

    df = yf.download('BTC-USD', start=start_date, end=end_date, interval='1h')[['Close']]
    # Check if we have enough data points

    if len(df['Close']) < 1:
        print(f"Not enough price data. Got {len(df['Close'])} data points. Using Pyth Network instead")

        history = get_real_price_path(duration=86400 * 30, resolution=60, start_time=start_date, time_increment=1)
        prices = [data["price"] for data in history]
        df = pd.DataFrame({"Close": prices})
        
    # Calculation of volatility
    df['pct_change'] = df['Close'].pct_change()*100
    print(f"😊😊😊 Percentage changes: {df['pct_change']}")
    df['stdev'] = df['pct_change'].rolling(volatility_days).std()

    df['vol'] = df['stdev']*(365**0.5)
    df.dropna(inplace=True)

    sigma = df.vol.mean() / 100
    print(f"😊😊😊 Sigma: {sigma}")
    # sigma = 0.195
    # Calculate the volatility of the asset price path
    # sigma= _calc_params(history_data=real_price_path)
    simulations = simulate_monte_claude_price_paths(current_price, time_increment, time_length, num_simulations, sigma)
    predictions = convert_prices_to_time_format(
        simulations.tolist(), str(start_time), time_increment
    )

    # Create simulations directory in project root's public folder
    sim_dir = os.path.join("../../public/monte-claude", str(int(datetime.fromisoformat(start_time).timestamp())))
    os.makedirs(sim_dir, exist_ok=True)
    
    # Save the array to a JSON file in the timestamped directory
    filepath = os.path.join(sim_dir, "simulation.json")
    with open(filepath, 'w') as f:
        json.dump({
            "variable": {
                "current_price": float(current_price),
                "time_increment": time_increment,
                "time_length": time_length,
                "num_simulations": num_simulations,
                "sigma": sigma,
                "start_time": start_time,
                "volatility_type": "unknown",
                "model": "monte-claude"
            },
            "prediction": predictions
        }, f, indent=2)

    print(f"Results saved to: {filepath}")
    
    return predictions

def main():

    start_time = "2025-02-26T00:29:00.000Z"

    publish_time = int(datetime.fromisoformat(start_time).timestamp())
    start_time_parsed = datetime.fromisoformat(start_time) - timedelta(days=1)
    current_price = get_real_price_path(asset="BTC", duration=86400, time_increment=5, resolution=1, start_time=start_time_parsed.isoformat())[-1]["price"]

    if current_price is None:
        raise ValueError("Current price is None")
    predictions = generate_simulations(
        current_price=current_price,
        time_increment=300,
        time_length=86400,
        num_simulations=100,
        start_time=start_time
    )
    real_path_file = os.path.join("../../public/real", str(publish_time), "real.json")
    if not os.path.exists(real_path_file):
        print(f"Real price path file does not exist. Fetching from Pyth Network")
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
    score_path = os.path.join("../../public/monte-claude", str(publish_time), "score.json", )
    os.makedirs(os.path.dirname(score_path), exist_ok=True)
    with open(score_path, 'w') as f:
        json.dump(score_data, f, indent=2)

    print(f"Score data saved to: {score_path}")

if __name__ == "__main__":
    main()
