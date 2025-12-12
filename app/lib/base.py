import numpy as np
from datetime import datetime, timedelta
from helpers import convert_prices_to_time_format
from helpers import from_iso_to_unix_time
from helpers import get_real_price_path
from helpers import align_prediction_and_real_prices
from helpers import calculate_crps_for_miner

import os
import json

def simulate_single_price_path_based_on_volatility(
    current_price, time_increment, time_length, sigma, volatility_type="hourly"
):
    """
    Simulate a single crypto asset price path.
    
    current_price: the current price of the asset
    time_increment: the time increment in seconds
    time_length: the time length in seconds
    sigma: the daily or hourly volatility of the asset
    volatility_type: the type of volatility to use
    """
    one_hour = 3600
    one_day = 86400

    dt = time_increment / one_hour if volatility_type == "hourly" else time_increment / one_day if volatility_type == "daily" else 1

    num_steps = int(time_length / time_increment)
    std_dev = sigma * np.sqrt(dt)
    price_change_pcts = np.random.normal(0, std_dev, size=num_steps)
    cumulative_returns = np.cumprod(1 + price_change_pcts)
    cumulative_returns = np.insert(cumulative_returns, 0, 1.0)
    price_path = current_price * cumulative_returns
    return price_path
  
def simulate_crypto_price_paths(
    current_price, time_increment, time_length, num_simulations, sigma, volatility_type="hourly"
):
    """
    Simulate multiple crypto asset price paths.
    """

    price_paths = []
    for _ in range(num_simulations):
        price_path = simulate_single_price_path_based_on_volatility(
            current_price, time_increment, time_length, sigma, volatility_type
        )
        price_paths.append(price_path)

    return np.array(price_paths)
  
def generate_simulations(
    asset="BTC",
    start_time=None,
    time_increment=300,
    time_length=86400,
    num_simulations=1,
    sigma=0.01,
    volatility_type="hourly",
    current_price=None
):


    """
    Generate simulated price paths.

    Parameters:
        asset (str): The asset to simulate. Default is 'BTC'.
        start_time (str): The start time of the simulation. Defaults to current time.
        time_increment (int): Time increment in seconds.
        time_length (int): Total time length in seconds.
        num_simulations (int): Number of simulation runs.

    Returns:
        numpy.ndarray: Simulated price paths.
    """
    if start_time is None:
        raise ValueError("Start time must be provided.")

    # Get real price path from 1 day before start time
    start_time_parsed = datetime.fromisoformat(start_time) - timedelta(days=1)
    if current_price is None:
        current_price = get_real_price_path(asset=asset, duration=86400, time_increment=5, resolution=1, start_time=start_time_parsed.isoformat())[-1]["price"]
    if current_price is None:
        raise ValueError(f"Failed to fetch current price for asset: {asset}")
    
    simulations = simulate_crypto_price_paths(
        current_price=current_price,
        time_increment=time_increment,
        time_length=time_length,
        num_simulations=num_simulations,
        sigma=sigma,
        volatility_type=volatility_type
    )

    predictions = convert_prices_to_time_format(
        simulations.tolist(), start_time, time_increment
    )

    return predictions

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
    else:
        sigma = std_5min

    print(f"😊😊😊 {volatility_type} volatility (sigma) calculated: {sigma}")
    return sigma
  

def main():
    start_time = "2025-02-26T07:38:00.000Z"
    # sigma = 0.005
    days_history_data = 1
    start_time_parsed = datetime.fromisoformat(start_time) - timedelta(days=days_history_data)
    # Get real price path from 1 day before start time on 5 min interval
    history_data = get_real_price_path(duration=86400, time_increment=5, resolution=1, start_time=start_time_parsed.isoformat())
    # Calculate hourly volatility based on 1 day of 5 min interval data
    volatility_type = "daily"
    sigma= _calc_params(history_data=history_data, volatility_type=volatility_type)
    # Generate predictions
    predictions = generate_simulations(
        asset="BTC",
        start_time=start_time,
        time_increment=300,
        time_length=86400,
        num_simulations=100,
        sigma=sigma,
        volatility_type=volatility_type
    )

    # Save the predictions to a JSON file
    predictions_file = os.path.join("../../public/base", str(from_iso_to_unix_time(start_time)), "simulation.json")
    os.makedirs(os.path.dirname(predictions_file), exist_ok=True)
    with open(predictions_file, 'w') as f:
        json.dump({
            "variable": {
                "start_time": start_time,
                "sigma": sigma,
                "volatility_type": volatility_type,
                "model": "base"
            },
            "prediction": predictions

        }, f, indent=2)
    print(f"Predictions saved to: {predictions_file}")
    
    # Generate real price if not exists
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
    
    real_prices = []
    with open(real_path_file, 'r') as f:
        real_prices = json.load(f)
    predictions_path, real_price_path = align_prediction_and_real_prices(predictions, real_prices)

    crps_score, detailed_crps_data = calculate_crps_for_miner(np.array(predictions_path), np.array(real_price_path), 300)
    
    # Save scores to score.json
    score_data = {
        "total_score": float(crps_score),  # Convert numpy float to Python float
        "detailed_scores": detailed_crps_data
    }
    print(f"Total CRPS score: {crps_score}")
    score_path = os.path.join("../../public/base", str(from_iso_to_unix_time(start_time)), "score.json")
    with open(score_path, 'w') as f:
        json.dump(score_data, f, indent=2)

    print(f"Score data saved to: {score_path}")

if __name__ == "__main__":
    main()
