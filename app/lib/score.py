from helpers import calculate_crps_for_miner, get_real_price_path, align_prediction_and_real_prices, from_iso_to_unix_time, convert_prices_to_time_format
import json
from db import create_database_engine
from db import my_predictions
from sqlalchemy import select
import numpy as np
import os

def main():
    prediction_id = 25959
    engine = create_database_engine() 
    with engine.connect() as connection:
        # Fetch prediction by ID
        # query = select(my_predictions).where(my_predictions.c.id == prediction_id)
        # result = connection.execute(query).first()
        with open("predictions.json", "r") as f: 
            result = json.load(f)
        if not result:
            raise ValueError(f"No prediction found with ID {prediction_id}")
            
        simulation_data = result["predictions"]

        # miner_uid = result["miner_uid"]
    
    print(np.array(simulation_data).shape)
    # start_time = simulation_data[0][0]["time"]
    start_time = "2025-03-04T13:51:00+00:00"
    start_timestamp = from_iso_to_unix_time(start_time)
    real_path_file = os.path.join("../../public/real", str(start_timestamp), "real.json")
    if not os.path.exists(real_path_file):
        transformed_data = get_real_price_path(start_time=start_time)

        # Create simulations directory in project root's public folder
        sim_dir = os.path.join("../../public/real", str(start_timestamp))
        os.makedirs(sim_dir, exist_ok=True)

        # Save the transformed data directly to real.json
        filepath = os.path.join(sim_dir, "real.json")
        with open(filepath, 'w') as f:
            json.dump(transformed_data, f, indent=2)
        
        print(f"Real price path saved to: {filepath}")
    # real_prices = get_real_price_path(asset="BTC", duration=86400, resolution=1, time_increment=5, start_time=start_time)
    simulation_data = convert_prices_to_time_format(simulation_data, start_time, 300)
    with open("lstm_predictions.json", "w") as f:
        json.dump(simulation_data, f, indent=2)
    real_price_path = []
    with open(real_path_file, 'r') as f:
        real_price_path = json.load(f)
    predictions_path, real_price_path = align_prediction_and_real_prices(simulation_data, real_price_path)
    crps_score, detailed_crps_data = calculate_crps_for_miner(np.array(predictions_path), np.array(real_price_path), 300)

    # Save crps score to score file
    score_path = os.path.join("../../public/prediction_score")
    os.makedirs(score_path, exist_ok=True)
    with open(os.path.join(score_path, f"score_{prediction_id}.json"), 'w') as f:
        json.dump({"prediction_id": prediction_id, "start_time": start_time, "total_score": crps_score, "detailed_scores": detailed_crps_data}, f, indent=2)

    print(f"😊😊😊 Total score: {crps_score}")

if __name__ == "__main__":
    main()

