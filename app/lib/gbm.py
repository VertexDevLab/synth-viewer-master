import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
import os
import json
from helpers import from_iso_to_unix_time
from helpers import get_published_asset_price
from helpers import convert_prices_to_time_format
from helpers import get_real_price_path
from helpers import calculate_crps_for_miner
from helpers import align_prediction_and_real_prices

def simulate_crypto_price_paths(
    current_price, time_increment, time_length, num_simulations, sigma, start_time: str | None = None, volatility_type="hourly"
):
    """
    Simulate multiple crypto asset price paths.
    """
    
    if start_time is None:
        start_time = datetime.now().isoformat()
    
    simulations = simulate_gbm_price_paths(current_price=current_price, time_increment=time_increment, time_length=time_length, num_simulations=num_simulations, sigma=sigma, volatility_type=volatility_type)

    predictions = convert_prices_to_time_format(
        simulations.tolist(), str(start_time), time_increment
    )
    # Create simulations directory in project root's public folder
    sim_dir = os.path.join("../../public/gbm", str(int(datetime.fromisoformat(start_time).timestamp())))
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
                "volatility_type": volatility_type,
                "model": "gbm"
            },
            "prediction": predictions
        }, f, indent=2)

    print(f"Results saved to: {filepath}")
    
    return predictions

def simulate_gbm_price_paths(current_price, time_increment, time_length, num_simulations, sigma, volatility_type="hourly"):
    """
    Simulates num_simulations prices paths using a GBM model.
    Args:
    current_price: The latest available Bitcoin price.
    time_increment: The time increment in seconds.
    time_length: The time horizon in seconds.
    num_simulations: The number of paths to simulate.
    sigma: The hourly or daily volatility parameter of the GBM model.
    volatility_type: The type of volatility to use.
    Returns:
    np.array: A numpy array where each row corresponds to a simulated path.
    """
    num_steps = int(time_length / time_increment)
    one_hour = 3600
    one_day = 86400
    dt = time_increment / one_hour if volatility_type == "hourly" else time_increment / one_day
    simulated_prices = np.zeros((num_simulations, num_steps + 1))
    simulated_prices[:,0] = current_price

    dW = np.random.normal(0, 1, (num_simulations, num_steps))
    dS = np.exp(((-0.5 * sigma**2) * dt) + (sigma * np.sqrt(dt) * dW))
    for t in range(1, num_steps + 1):
        simulated_prices[:,t] = simulated_prices[:,t-1] * dS[:,t-1]
        
    return simulated_prices

def _calc_params(history_data: list[dict], volatility_type="hourly"):
    """
    Calculate the hourly volatility of the asset price path.

    Args:
        history_data: List of dictionaries containing price history for 24 hours with 5-minute intervals
        
    Returns:
        float: hourly or daily volatility (sigma) for use in GBM simulation
    """
    # Extract prices and convert to numpy array
    prices = np.array([price['price'] for price in history_data])
    
    # Calculate log returns
    log_returns = np.log(prices[1:] / prices[:-1])
    
    # Calculate volatility
    # For 5-minute data to hourly volatility:
    # 1. Calculate standard deviation of 5-min returns
    # 2. Multiply by square root of 12 (number of 5-min periods in an hour)
    std_5min = np.std(log_returns)
    if volatility_type == "hourly":
        sigma = std_5min * np.sqrt(12)  # Scale to hourly volatility
    elif volatility_type == "daily":
        sigma = std_5min * np.sqrt(288)  # Scale to daily volatility

    print(f"😊😊😊 {volatility_type} volatility (sigma) calculated: {sigma}")
    return sigma

def main():

    start_time = "2025-02-08T17:00:00+00:00"

    start_time_parsed = datetime.fromisoformat(start_time) - timedelta(days=1)
    current_price = get_real_price_path(asset="BTC", duration=86400, time_increment=5, resolution=1, start_time=start_time_parsed.isoformat())[-1]["price"]

    if current_price is None:
        raise ValueError("Current price is None")
    
    # Get the real price path for the past 7 days
    duration = 86400 * 7
    start_time_history = start_time_parsed - timedelta(days=7)
    history_data = get_real_price_path(duration=duration, time_increment=1, resolution=5, start_time=start_time_history.isoformat())

    with open("history_data.json", "w") as f:
        json.dump(history_data, f, indent=2)
    
    volatility_type = "hourly"
    sigma = _calc_params(history_data, volatility_type)

    predictions = simulate_crypto_price_paths(
        current_price=current_price,
        time_increment=300,
        time_length=86400,
        num_simulations=100,
        sigma=56.68 / 10000,
        start_time=start_time,
        volatility_type=volatility_type
    )
    
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
        
    predictions_path, real_price_path = align_prediction_and_real_prices(predictions, real_price_path)

    crps_score, detailed_crps_data = calculate_crps_for_miner(np.array(predictions_path), np.array(real_price_path), 300)
    
    # Save scores to score.json
    score_data = {
        "total_score": float(crps_score),  # Convert numpy float to Python float
        "detailed_scores": detailed_crps_data
    }
    print(f"Total CRPS score: {crps_score}")
    # Create path and save file
    score_path = os.path.join("../../public/gbm", str(from_iso_to_unix_time(start_time)), "score.json")
    with open(score_path, 'w') as f:
        json.dump(score_data, f, indent=2)

    print(f"Score data saved to: {score_path}")

if __name__ == "__main__":
    main()
