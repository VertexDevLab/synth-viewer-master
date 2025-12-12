from helpers import get_real_price_path, convert_prices_to_time_format, calculate_crps_for_miner, align_prediction_and_real_prices, from_iso_to_unix_time
from datetime import datetime, timedelta
import numpy as np
import json
import os

def analyze_last_day(end_time):
  start_time = datetime.fromisoformat(end_time) - timedelta(days=1)
  price_data = get_real_price_path(asset="BTC", duration=86400, start_time=start_time, resolution=1, time_increment=5)

  prices = np.array([data["price"] for data in price_data])
  price_diff = np.diff(prices) / prices[:-1] * 100

  min_diff = abs(np.min(price_diff))
  max_diff = abs(np.max(price_diff))
  avg_diff = abs(np.mean(price_diff))

  print(f"Min diff: {min_diff}, Max diff: {max_diff}, Avg diff: {avg_diff}")

  return avg_diff

def generate_single_path(initial_price: float, duration: int, time_increment: int, max_diff: float) -> list[float]:
  prices = [initial_price]
  for i in range(duration // time_increment):
    price_diff = np.random.uniform(-max_diff, max_diff)
    prices.append(prices[-1] * (1 + price_diff))
  return prices

def generate_multiple_paths(initial_price: float, duration: int, time_increment: int, max_diff: float, num_paths: int) -> list[list[float]]:
  paths = []
  for i in range(num_paths):
    paths.append(generate_single_path(initial_price, duration, time_increment, max_diff))
  return paths

def main():

  start_time = "2025-02-09T17:00:00+00:00"
  time_increment=300
  time_length=86400
  num_simulations=100
  start_time_parsed = datetime.fromisoformat(start_time) - timedelta(days=1)
  initial_price = get_real_price_path(asset="BTC", duration=86400, time_increment=5, resolution=1, start_time=start_time_parsed.isoformat())[-1]["price"]

  max_diff = analyze_last_day(start_time)

  paths = generate_multiple_paths(initial_price=initial_price, duration=86400, time_increment=300, max_diff=max_diff, num_paths=100)
  
  converted_paths = convert_prices_to_time_format(np.array(paths), start_time, 300)

  # Create simulations directory in project root's public folder
  sim_dir = os.path.join("../../public/custom", str(int(datetime.fromisoformat(start_time).timestamp())))
  os.makedirs(sim_dir, exist_ok=True)
  
  # Save the array to a JSON file in the timestamped directory
  filepath = os.path.join(sim_dir, "simulation.json")
  with open(filepath, 'w') as f:
      json.dump({
          "variable": {
              "current_price": float(initial_price),
              "time_increment": time_increment,
              "time_length": time_length,
              "num_simulations": num_simulations,
              "start_time": start_time,
              "volatility_type": "unknown",
              "model": "custom"
          },
          "prediction": converted_paths
      }, f, indent=2)

  print(f"Results saved to: {filepath}")

  real_path_file = os.path.join("../../public/real", str(from_iso_to_unix_time(start_time)), "real.json")
  if not os.path.exists(real_path_file):
      transformed_data = get_real_price_path(start_time=start_time)

      # Create simulations directory in project root's public folder
      sim_dir = os.path.join("../../public/real", str(from_iso_to_unix_time(start_time)))
      os.makedirs(sim_dir, exist_ok=True)

      # Save the transformed data directly to real.json
      filepath = os.path.join(sim_dir, "real.json")
      with open(filepath, 'w') as f:
          json.dump(transformed_data, f, indent=2)
      
      print(f"Real price path saved to: {filepath}")
  
  real_price_path = []
  with open(real_path_file, 'r') as f:
      real_price_path = json.load(f)

  predictions_path, real_price_path = align_prediction_and_real_prices(converted_paths, real_price_path)

  crps_score, detailed_crps_data = calculate_crps_for_miner(np.array(predictions_path), np.array(real_price_path), 300)

  # Save scores to score.json
  score_data = {
      "total_score": float(crps_score),  # Convert numpy float to Python float
      "detailed_scores": detailed_crps_data
  }
  
  # Create path and save file
  score_path = os.path.join("../../public/custom", str(from_iso_to_unix_time(start_time)), "score.json")
  os.makedirs(os.path.dirname(score_path), exist_ok=True)
  with open(score_path, 'w') as f:
      json.dump(score_data, f, indent=2)

  print(f"😊😊😊 Total score: {crps_score}")

if __name__ == "__main__":
    main()