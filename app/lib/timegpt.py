from helpers import get_real_price_path, from_iso_to_unix_time, align_prediction_and_real_prices, calculate_crps_for_miner, get_published_asset_price
import json
import pandas as pd
from nixtla import NixtlaClient
import os
from datetime import datetime
import numpy as np

def get_timegpt_predictions(df: pd.DataFrame, initial_price: float, start_time: str, time_increment: int, time_length: int, num_simulations: int):
    client = NixtlaClient(api_key="nixak-ju4lqmknbQhqoexxsRjvCDQstGFFvpuOVMv3OU308b85DyAgqwSmU4QucwAb72ORBrAkl3qIecT73lV4")
    simulations = []
    level = [50]
    for i in range(num_simulations):
        fcst = client.forecast(
            df,
            h=288,
            # level = [i],
            model='timegpt-1-long-horizon',
            finetune_steps=10,
            finetune_loss='mae',
        )

        fcst.head()
        print(f"df last price: {float(df.iloc[-1]['y'])}")
        print(f"fcst last date: {fcst.iloc[-1]['ds']}")
        with open("fcst.json", "w") as f:
            json.dump(fcst.to_json(orient="records"), f, indent=2)
        # Convert forecast to desired format
        result = []
        # Add the last point from input data

        result.append({
            'time': start_time,  
            'price': initial_price 
        })
        # Add forecast points
        for _, row in fcst.iterrows():

            result.append({
                'time': row['ds'].isoformat(),  
                'price': float(row['TimeGPT'])  # Convert prediction to float
            })
        simulations.append(result)
    
    return simulations

def main():
    start_time = "2025-02-01T23:30:00+00:00"
    time_increment = 300
    time_length = 86400
    num_simulations = 100
    df_start_times = ["2025-01-04T23:30:00+00:00", "2025-01-11T23:30:00+00:00", "2025-01-18T23:30:00+00:00", "2025-01-25T23:30:00+00:00"]
    df_price_paths = []
    for df_start_time in df_start_times:
        df_price_path = get_real_price_path(duration=time_length * 7 - 300, resolution=5, time_increment=1, start_time=df_start_time)
        print(f"length of df_price_path: {len(df_price_path)}")
        df_price_paths.extend(df_price_path)
    with open("df_price_paths.json", "w") as f:
        json.dump(df_price_paths, f, indent=2)
    df = pd.DataFrame(df_price_paths)
    df = df.rename(columns={'time': 'ds', 'price': 'y'})

    initial_price = get_published_asset_price(asset="BTC", publish_time=from_iso_to_unix_time(start_time))
    predictions = get_timegpt_predictions(df=df, initial_price=initial_price, start_time=start_time, time_increment=time_increment, time_length=time_length, num_simulations=num_simulations)

    sim_dir = os.path.join("../../public/timegpt", str(int(datetime.fromisoformat(start_time).timestamp())))
    os.makedirs(sim_dir, exist_ok=True)
    filepath = os.path.join(sim_dir, "simulation.json")
    with open(filepath, "w") as f:
        json.dump({"start_time": start_time, "prediction": predictions}, f, indent=2)


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
    
    print(f"😊😊😊 Total score: {crps_score}")
    
    # Create path and save file
    score_path = os.path.join("../../public/timegpt", str(from_iso_to_unix_time(start_time)), "score.json")
    with open(score_path, 'w') as f:
        json.dump(score_data, f, indent=2)

    print(f"Score data saved to: {score_path}")
if __name__ == "__main__":
    main()

