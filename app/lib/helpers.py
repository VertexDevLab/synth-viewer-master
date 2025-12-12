from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
import requests
import json
import os
from properscoring import crps_ensemble
import typing

def from_iso_to_unix_time(iso_time: str) -> int:
    # Convert to a datetime object

    dt = datetime.fromisoformat(iso_time).replace(tzinfo=timezone.utc)

    # Convert to Unix time
    unix_time = int(dt.timestamp())

    return unix_time

def get_intersecting_arrays(array1: list[dict], array2: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Filters two arrays of dictionaries, keeping only entries that intersect by 'time'.

    :param array1: First array of dictionaries with 'time' and 'price'.
    :param array2: Second array of dictionaries with 'time' and 'price'.
    :return: Two new arrays with only intersecting 'time' values.
    """
    # Extract times from the second array as a set for fast lookup
    times_in_array2 = {entry["time"] for entry in array2}
    # Filter array1 to include only matching times
    filtered_array1 = [
        entry for entry in array1 if entry["time"] in times_in_array2
    ]

    # Extract times from the first array as a set
    times_in_array1 = {entry["time"] for entry in array1}

    # Filter array2 to include only matching times
    filtered_array2 = [
        entry for entry in array2 if entry["time"] in times_in_array1
    ]

    return filtered_array1, filtered_array2

def compute_softmax(score_values: np.ndarray) -> np.ndarray:
    # Mask out invalid scores (e.g., -1)
    mask = score_values != -1  # True for values to include in computation

    # --- Softmax Normalization ---
    beta = -1 / 1000.0  # Negative beta to give higher weight to lower scores

    # Compute softmax scores only for valid values
    exp_scores = np.exp(beta * score_values[mask])
    softmax_scores_valid = exp_scores / np.sum(exp_scores)

    # Create final softmax_scores with 0 where scores were -1
    softmax_scores = np.zeros_like(score_values, dtype=float)
    softmax_scores[mask] = softmax_scores_valid

    return softmax_scores

def get_latest_asset_price(asset="BTC") -> float | None:
    """
    Retrieves the current price of the specified asset.
    Currently, supports BTC via Pyth Network.

    Returns:
        float: Current asset price.
    """
    if asset == "BTC":
        btc_price_id = (
            "e62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43"
        )
        
        endpoint = f"https://hermes.pyth.network/v2/updates/price/latest?ids[]={btc_price_id}"
        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            data = response.json()
            print(data)
            if not data :
                raise ValueError("No price data received")
            price_feed = data["parsed"][0]
            price = float(price_feed["price"]["price"]) / (10**8)
            return price
        except Exception as e:
            
            print(f"Error fetching {asset} price: {e}")
            return None
        
def get_published_asset_price(asset="BTC", publish_time: int | None = None) -> float | None:
    """
    Retrieves the published price of the specified asset.
    """
    if publish_time is None:
        publish_time = int(datetime.now().timestamp())
    
    if asset == "BTC":
        btc_price_id = (
            "e62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43"
        )
        
        endpoint = f"https://hermes.pyth.network/v2/updates/price/{publish_time}?ids[]={btc_price_id}"
        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            data = response.json()
            if not data:
                raise ValueError("No price data received")
            price_feed = data["parsed"][0]
            price = float(price_feed["price"]["price"]) / (10**8)
            return price
        except Exception as e:
            print(f"Error fetching {asset} price: {e}")
            return None
        
def transform_data(data, time_increment=5):
    if data is None or len(data) == 0:
        return []

    timestamps = data["t"]
    close_prices = data["c"]
    print(datetime.fromtimestamp(
                timestamps[0], timezone.utc
            ).isoformat())
    transformed_data = [
        {
            "time": datetime.fromtimestamp(
                timestamps[i], timezone.utc
            ).isoformat(),
            "price": float(close_prices[i]),
        }
        for i in range(len(timestamps) - 1, -1, -time_increment)
    ][::-1]

    return transformed_data

def get_real_price_path(asset="BTC", duration=86400, resolution=1, time_increment=5, start_time=None):
    """
    Retrieves the past price path of the specified asset.
    """
    try:
        if start_time is None:
            end_time = int(datetime.now().timestamp())
            start_time = end_time - duration

        else:
            start_time = from_iso_to_unix_time(str(start_time))
            end_time = start_time + duration
        params = {
            "symbol": "Crypto.BTC/USD",
            "resolution": resolution,
            "from": start_time,
            "to": end_time,
        }
        BASE_URL = "https://benchmarks.pyth.network/v1/shims/tradingview/history"
        
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        
        data = response.json()
        transformed_data = transform_data(data, time_increment=time_increment)
        return transformed_data
            
    except Exception as e:
        print(f"Error fetching {asset} price: {e}")
        raise e


def convert_prices_to_time_format(prices: list[float], start_time: str, time_increment: int) -> list[list[dict]]:
    """
    Convert an array of float numbers (prices) into an array of dictionaries with 'time' and 'price'.

    :param prices: List of float numbers representing prices.
    :param start_time: ISO 8601 string representing the start time.
    :param time_increment: Time increment in seconds between consecutive prices.
    :return: List of dictionaries with 'time' and 'price' keys.
    """
    start_time = datetime.fromisoformat(
        start_time
    )  # Convert start_time to a datetime object
    result = []

    for price_item in prices:
        single_prediction = []
        for i, price in enumerate(price_item):
            time_point = start_time + timedelta(seconds=i * time_increment)
            single_prediction.append(
                {"time": time_point.isoformat(), "price": price}
            )
        result.append(single_prediction)

    return result

def calculate_crps_for_miner(simulation_runs: list[list[dict]], real_price_path: list[dict], time_increment) -> tuple[float, list[dict]]:
    """
    Calculate the total CRPS score for a miner's simulations over specified intervals.
    
    Args:
        simulation_runs (numpy.ndarray): Simulated price paths.
        real_price_path (numpy.ndarray): The real price path.
        time_increment (int): Time increment in seconds.
        timestamp (str): Simulation timestamp for file path.
        
    Returns:
        tuple: (sum_all_scores, detailed_crps_data)
    """
    # Define scoring intervals in seconds
    scoring_intervals = {
        "5min": 300,    # 5 minutes
        "30min": 1800,  # 30 minutes
        "3hour": 10800, # 3 hours
        "24hour": 86400 # 24 hours
    }

    detailed_crps_data = []
    sum_all_scores = 0.0

    for interval_name, interval_seconds in scoring_intervals.items():
        interval_steps = int(interval_seconds / time_increment)

        # Calculate price changes over intervals
        simulated_changes = calculate_price_changes_over_intervals(
            simulation_runs, interval_steps
        )
        real_changes = calculate_price_changes_over_intervals(
            real_price_path.reshape(1, -1), interval_steps
        )[0]

        # Calculate CRPS over intervals, but only up to the valid length
        num_intervals = min(simulated_changes.shape[1], len(real_changes))
        crps_values = np.zeros(num_intervals)
        
        for t in range(num_intervals):
            forecasts = simulated_changes[:, t]
            observation = real_changes[t]
            crps_values[t] = crps_ensemble(observation, forecasts)

            detailed_crps_data.append({
                "Interval": interval_name,
                "Increment": t + 1,
                "CRPS": float(crps_values[t])  # Convert numpy float to Python float
            })

        # Total CRPS for this interval
        total_crps_interval = float(np.sum(crps_values))  # Convert numpy float to Python float
        sum_all_scores += total_crps_interval

        detailed_crps_data.append({
            "Interval": interval_name,
            "Increment": "Total",
            "CRPS": total_crps_interval
        })

    return sum_all_scores, detailed_crps_data

def calculate_price_changes_over_intervals(price_paths, interval_steps):
    """
    Calculate price changes over specified intervals.

    Parameters:
        price_paths (numpy.ndarray): Array of simulated price paths.
        interval_steps (int): Number of steps that make up the interval.

    Returns:
        numpy.ndarray: Array of price changes over intervals.
    """
    # Get the prices at the interval points
    interval_prices = price_paths[:, ::interval_steps]
    # Calculate price changes over intervals
    price_changes = np.diff(interval_prices, axis=1)
    return price_changes

def align_prediction_and_real_prices(predictions: list[list[dict]], real_prices: list[dict]):    
    # in case some of the time points is not overlapped
    intersecting_predictions = []
    intersecting_real_price = real_prices
    for prediction in predictions:

        intersecting_prediction, intersecting_real_price = (
            get_intersecting_arrays(prediction, intersecting_real_price)
        )
        intersecting_predictions.append(intersecting_prediction)

    predictions_path = [
        [entry["price"] for entry in sublist]
        for sublist in intersecting_predictions
    ]
    real_price_path = [entry["price"] for entry in intersecting_real_price]
    
    return predictions_path, real_price_path

def calculate_volatility(price_path: list[dict]) -> float:
    """
    Calculate the annualized volatility from a price path.
    
    Args:
        price_path (list[dict]): List of dictionaries containing 'time' and 'price' entries
                                Expected to be 24 hours of 5-minute interval data
                                
    Returns:
        float: Annualized volatility as a decimal (e.g., 0.65 for 65% volatility)
    """
    # Extract prices
    prices = [entry['price'] for entry in price_path]
    
    # Calculate log returns
    log_returns = np.log(np.array(prices[1:]) / np.array(prices[:-1]))
    
    # Calculate standard deviation of log returns
    std_dev = np.std(log_returns, ddof=1)
    
    # Annualize the volatility
    # For 5-min data over 24 hours: √(288) = √(12 * 24) for trading periods per year
    # 288 five-minute periods per day * 365 days = 105120 periods per year
    annualized_vol = std_dev * np.sqrt(105120)
    
    return float(annualized_vol)

def validate_responses(
    response,
    num_simulations,
    time_length,
    time_increment,
    start_time,
) -> str:
    """
    Validate responses from miners.

    Return a string with the error message
    if the response is not following the expected format or the response is empty,
    otherwise, return "CORRECT".
    """

    # check if the response is empty
    if response is None or len(response) == 0:
        return "Response is empty"

    # check the number of paths
    if len(response) != num_simulations:
        return f"Number of paths is incorrect: expected {num_simulations}, got {len(response)}"

    for path in response:
        # check the number of time points
        expected_time_points = (
            time_length // time_increment + 1
        )
        if len(path) != expected_time_points:
            return f"Number of time points is incorrect: expected {expected_time_points}, got {len(path)}"

        # check the start time
        if path[0]["time"] != start_time:
            return f"Start time is incorrect: expected {start_time}, got {path[0]['time']}"

        for i in range(1, len(path)):
            # check the time formats
            i_minus_one_str_time = path[i - 1]["time"]
            i_minus_one_datetime, error_message = validate_datetime(
                i_minus_one_str_time
            )
            if error_message:
                return error_message

            i_str_time = path[i]["time"]
            i_datetime, error_message = validate_datetime(i_str_time)
            if error_message:
                return error_message

            # check the time increment
            expected_delta = timedelta(seconds=time_increment)
            actual_delta = i_datetime - i_minus_one_datetime
            if actual_delta != expected_delta:
                return f"Time increment is incorrect: expected {expected_delta}, got {actual_delta}"

            # check the price format
            if not isinstance(path[i]["price"], (int, float)):
                return f"Price format is incorrect: expected int or float, got {type(path[i]['price'])}"

    return True

def validate_datetime(
    dt_str,
) -> typing.Tuple[typing.Optional[datetime], typing.Optional[str]]:
    if not isinstance(dt_str, str):
        return (
            None,
            f"Time format is incorrect: expected str, got {type(dt_str)}",
        )
    if not datetime_valid(dt_str):
        return (
            None,
            f"Time format is incorrect: expected isoformat, got {dt_str}",
        )

    return datetime.fromisoformat(dt_str), None

def datetime_valid(dt_str) -> bool:
    try:
        datetime.fromisoformat(dt_str)
    except:
        return False
    return True