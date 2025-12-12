import pandas as pd
import numpy as np
import math
from time import time
import requests
import yfinance as yf
import warnings
from scipy import stats
import os
import json
from datetime import datetime, timezone, timedelta
from helpers import from_iso_to_unix_time
from helpers import get_published_asset_price
from helpers import convert_prices_to_time_format
from helpers import get_real_price_path
from helpers import calculate_crps_for_miner
from helpers import align_prediction_and_real_prices

def simulate_manual_price_paths(start_time: str, initial_price: float, time_increment: int, time_length: int, num_simulations: int):
  warnings.filterwarnings('ignore')

  end_date = datetime.fromisoformat(start_time)
  start_date = end_date - timedelta(days=3)
  # df = yf.download('BTC-USD', start=start_date, end=end_date, interval='1h')[['Close']]
  df = yf.download('BTC-USD', start=start_date, end=end_date, interval='5m')[['Close']]

  # Calculation of volatility
  volatility_days = 30
  df['pct_change'] = df['Close'].pct_change()*100
  print(df['pct_change'])
  df['stdev'] = df['pct_change'].rolling(volatility_days).std()

  df['vol'] = df['stdev']*(365**0.5)
  df.dropna(inplace=True)

  sigma = df.vol.mean() / 100
  
  print(f"😊😊😊 Sigma: {sigma}")

  # Maturity remains 1/365 (one day)
  T = 1/30

  # Risk-free rate calculation
  r = 0.0020 + 0.94 * 0.0438

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

  pct_changes = df['pct_change'].dropna().values
  # Calculate number of steps
  n_steps = int(time_length / time_increment)

  # Calculate target price parameters
  target_min, target_max = (95500, 97500)
  target_mid = (target_min + target_max) / 2
  required_total_return = (target_mid / initial_price - 1) * 100
  
  all_prices = []
  
  for _ in range(num_simulations):
    # Initialize path with starting price
    current_path = [initial_price]
    current_price = initial_price
    total_return = 0
    
     # Generate each step in the path
    for i in range(n_steps):
      # Sample a random historical change
      pct_change = np.random.choice(pct_changes)
      
      # Adjust the change to trend toward target
      remaining_steps = n_steps - i
      remaining_target_return = required_total_return - total_return
      bias = remaining_target_return / remaining_steps
      # adjusted_change = pct_change + bias
      adjusted_change = pct_change
      
      # Calculate new price
      current_price = current_price * (1 + adjusted_change/100)
      total_return += adjusted_change
      
      # Add to path
      current_path.append(float(current_price))
      
    all_prices.append(current_path)
    
  result = np.array(all_prices)
  # save to csv file
  np.savetxt("manual_paths.csv", result, delimiter=",")
  return result


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
    simulations = simulate_manual_price_paths(start_time, current_price, time_increment, time_length, num_simulations)

    predictions = convert_prices_to_time_format(
        simulations.tolist(), str(start_time), time_increment
    )
    # Create simulations directory in project root's public folder
    sim_dir = os.path.join("../../public/manual", str(int(datetime.fromisoformat(start_time).timestamp())))
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
    start_time = "2025-02-02T23:30:00+00:00"

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
    score_path = os.path.join("../../public/manual", str(publish_time), "score.json")
    with open(score_path, 'w') as f:
        json.dump(score_data, f, indent=2)

    print(f"Score data saved to: {score_path}")

if __name__ == "__main__":
    main()
