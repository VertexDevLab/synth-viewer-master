from base import generate_simulations, _calc_params, get_real_price_path, align_prediction_and_real_prices, calculate_crps_for_miner
from datetime import datetime, timedelta, timezone
import os
import json
from helpers import from_iso_to_unix_time
import numpy as np

def main():
    now = datetime.now(timezone.utc)
    now = now.replace(second=0, microsecond=0)
    start_time = (now - timedelta(hours=24, minutes=1)).isoformat()
    # start_time = "2025-03-16T14:43:00+00:00"
    print(f"😊😊😊 Start time: {start_time}")

    days_history_data = 1
    start_time_parsed = datetime.fromisoformat(start_time) - timedelta(days=days_history_data)
    # Get real price path from 1 day before start time on 5 min interval
    history_data = get_real_price_path(duration=86400, time_increment=5, resolution=1, start_time=start_time_parsed.isoformat())
    initial_price = history_data[-1]["price"]
    print(f"😊😊😊 Initial price: {initial_price}")
    # Calculate hourly volatility based on 1 day of 5 min interval data
    volatility_type = "hourly"
    sigma= _calc_params(history_data=history_data, volatility_type=volatility_type)

    print(f"😊😊😊 {volatility_type} volatility (sigma) calculated: {sigma}")

    sigma_start = sigma / 2
    sigma_end = sigma * 1.5
    sigma_step = (sigma_end - sigma_start) / 20

    sigma_test_results = []

    for i in range(10):
        crps_scores = []
        for sigma in np.arange(sigma_start, sigma_end, sigma_step):
            predictions = generate_simulations(
                asset="BTC",
                start_time=start_time,
                time_increment=300,
                time_length=86400,
                sigma=sigma,
                volatility_type=volatility_type,
                num_simulations=100,
                current_price=initial_price
            )

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
            crps_scores.append({"sigma": sigma, "crps_score": crps_score})
        sigma_test_results.append(crps_scores)

    # Find the best sigma for each test run
    best_sigmas_per_run = [min(run, key=lambda x: x["crps_score"])["sigma"] for run in sigma_test_results]
    
    # Count occurrences of each sigma value
    sigma_counts = {}
    for sigma in best_sigmas_per_run:
        sigma_counts[sigma] = sigma_counts.get(sigma, 0) + 1
    print(f"😊😊😊 Sigma counts: {sigma_counts}")
    # Get the sigma with the most occurrences
    best_sigma = max(sigma_counts.items(), key=lambda x: x[1])[0]

    end_time = datetime.now(timezone.utc)
    time_taken = end_time - now
    print(f"😊😊😊 Best sigma: {best_sigma}")
    print(f"😊😊😊 Sigma counts: {sigma_counts}")
    print(f"😊😊😊 Time taken: {time_taken}")
    
    # Save the CRPS scores to a JSON file
    crps_scores_file = os.path.join("../../public/base", str(from_iso_to_unix_time(start_time)), "sigma_test.json")
    os.makedirs(os.path.dirname(crps_scores_file), exist_ok=True)
    with open(crps_scores_file, 'w') as f:
        json.dump(sigma_test_results, f, indent=2)
    print(f"CRPS scores saved to: {crps_scores_file}")

if __name__ == "__main__":
    main()

