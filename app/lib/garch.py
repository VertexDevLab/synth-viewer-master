import pandas as pd
import numpy as np
import yfinance as yf
import warnings
from arch import arch_model

import os
import json
from helpers import get_published_asset_price
from helpers import convert_prices_to_time_format
from helpers import get_real_price_path
from helpers import calculate_crps_for_miner
from helpers import align_prediction_and_real_prices

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import warnings
from arch import arch_model

def analyze_trend(df, lookback_window=24):
    """Analyze recent price trend and momentum"""
    # Calculate various trend indicators
    df['returns'] = df['Close'].pct_change()
    df['sma'] = df['Close'].rolling(window=lookback_window).mean()
    df['momentum'] = df['Close'] / df['Close'].shift(lookback_window) - 1
    
    # Get latest values - use .iloc[-1] to get scalar values
    current_price = float(df['Close'].iloc[-1])  # Convert to float
    sma = float(df['sma'].iloc[-1]) if pd.notna(df['sma'].iloc[-1]) else None  # Convert to float or None
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

def simulate_garch_price_paths(initial_price: float, start_time: str, time_increment: int, 
                             time_length: int, num_simulations: int):
    warnings.filterwarnings('ignore')

    # Download historical data with a longer lookback period and shorter interval
    end_date = datetime.fromisoformat(start_time)
    start_date = end_date - timedelta(days=90)
    
    # Try different intervals if hourly data is insufficient
    intervals = ['1h', '15m', '5m']
    df = None
    
    for interval in intervals:
        try:
            df = yf.download('BTC-USD', start=start_date, end=end_date, interval=interval)[['Close']]
            if len(df) >= 24:  # Check if we have enough data
                break
        except Exception as e:
            print(f"Failed to download data with interval {interval}: {e}")
            continue
    
    if df is None or len(df) < 24:
        raise ValueError(f"Unable to obtain sufficient historical data for any interval")

    # Analyze trend
    trend_strength, momentum = analyze_trend(df)
    print(f"\nTrend Analysis:")
    print(f"Trend Strength: {trend_strength} (-3 to +3 scale)")
    print(f"Momentum: {momentum:.2%}")

    # Calculate returns and handle missing data
    df['returns'] = df['Close'].pct_change() * 100
    df = df.dropna()  # Remove any NaN values
    
    # Handle extreme values in returns
    df['returns'] = df['returns'].clip(-50, 50)  # Clip extreme returns
    
    # Additional check after data cleaning
    if len(df) < 24:
        print("Warning: Using simplified model due to insufficient clean data")
        return simulate_simplified_paths(initial_price, num_simulations, time_length)

    # Fit ARCH model with error handling
    try:
        model = arch_model(df['returns'], 
                          vol='GARCH', 
                          p=1, 
                          q=1, 
                          dist='t')
        results = model.fit(disp='off', update_freq=0)
    except Exception as e:
        print(f"Error fitting GARCH model: {e}")
        return simulate_simplified_paths(initial_price, num_simulations, time_length)

    # Get the last variance forecast
    last_variance = results.forecast().variance.iloc[-1] ** 0.5

    # Parameters for simulation
    S0 = initial_price
    M = 24 * 12  # Number of 5-min intervals in a day
    I = num_simulations

    # Get GARCH parameters
    garch_parameters = results.params
    omega = garch_parameters['omega']
    alpha = garch_parameters['alpha[1]']
    beta = garch_parameters['beta[1]']
    nu = garch_parameters['nu']

    # Scale down the variance to match 5-minute intervals
    scaling_factor = 1/288
    omega = omega * scaling_factor
    last_variance = last_variance * scaling_factor

    # Adjust drift based on trend
    base_drift = 0.0
    if trend_strength > 0:
        drift_adjustment = min(0.015 * abs(trend_strength), 0.03)  # Cap at 3%
        base_drift = drift_adjustment / (24 * 12)  # Per 5-min interval
    elif trend_strength < 0:
        drift_adjustment = min(0.015 * abs(trend_strength), 0.03)  # Cap at 3%
        base_drift = -drift_adjustment / (24 * 12)  # Per 5-min interval

    def simulate_trend_based_path(n_steps, omega, alpha, beta, last_variance, S0, nu, base_drift):
        variance = np.zeros(n_steps + 1)
        prices = np.zeros(n_steps + 1)
        variance[0] = last_variance
        prices[0] = S0
        
        try:
            for t in range(1, n_steps + 1):
                variance[t-1] = max(variance[t-1], 1e-8)
                
                # Generate asymmetric innovations based on trend
                if trend_strength > 0:
                    # Bias towards positive returns
                    eps = np.random.standard_t(nu) * 0.5
                    eps = abs(eps) if np.random.random() < 0.6 else -abs(eps)
                elif trend_strength < 0:
                    # Bias towards negative returns
                    eps = np.random.standard_t(nu) * 0.5
                    eps = -abs(eps) if np.random.random() < 0.6 else abs(eps)
                else:
                    eps = np.random.standard_t(nu) * 0.5
                
                # Update variance with error checking
                try:
                    variance[t] = max(omega + alpha * variance[t-1] * eps**2 + beta * variance[t-1], 1e-8)
                except Exception:
                    variance[t] = variance[t-1]  # Keep previous variance if calculation fails
                
                # Calculate return with trend-based drift
                vol = np.sqrt(variance[t])
                rt = np.clip(vol * eps / 100 + base_drift, -0.02, 0.02)
                
                # Update price with bounds checking
                prices[t] = prices[t-1] * (1 + rt)
                
                # Dynamic bounds based on trend
                lower_bound = S0 * (0.85 if trend_strength < 0 else 0.9)
                upper_bound = S0 * (1.15 if trend_strength > 0 else 1.1)
                prices[t] = np.clip(prices[t], lower_bound, upper_bound)
                
        except Exception as e:
            print(f"Error in simulation: {e}")
            return np.full(n_steps + 1, S0)
            
        return prices

    # Simulate multiple paths with improved error handling
    S = np.zeros((M + 1, I))
    valid_paths = 0
    max_attempts = I * 2  # Allow some retry attempts
    attempt = 0
    i = 0
    
    while i < I and attempt < max_attempts:
        try:
            path = simulate_trend_based_path(M, omega, alpha, beta, last_variance, S0, nu, base_drift)
            if not np.any(np.isnan(path)) and not np.any(np.isinf(path)):
                S[:, i] = path
                valid_paths += 1
                i += 1
        except Exception as e:
            print(f"Error in path {i}: {e}")
        attempt += 1

    if valid_paths == 0:
        print("Warning: No valid paths generated. Falling back to simplified model.")
        return simulate_simplified_paths(initial_price, num_simulations, time_length)

    # Analysis of results
    closing_prices = S[-1]
    
    print("\nSimulation Results:")
    print(f"Current Price: ${S0:,.2f}")
    print(f"Mean Predicted Price: ${np.mean(closing_prices):,.2f}")
    print(f"Median Predicted Price: ${np.median(closing_prices):,.2f}")
    print(f"5th Percentile: ${np.percentile(closing_prices, 5):,.2f}")
    print(f"95th Percentile: ${np.percentile(closing_prices, 95):,.2f}")
    
    # Calculate probability of price increase
    prob_increase = np.mean(closing_prices > S0) * 100
    print(f"\nProbability of Price Increase: {prob_increase:.1f}%")
    
    return S.T

def simulate_simplified_paths(initial_price, num_simulations, time_length):
    """Fallback method using a simple geometric Brownian motion model"""
    M = time_length // 300  # Number of 5-min intervals
    paths = np.zeros((num_simulations, M + 1))
    paths[:, 0] = initial_price
    
    # Use historical volatility estimate
    daily_vol = 0.03  # Conservative estimate
    dt = 1/288  # 5-min interval as fraction of day
    vol = daily_vol * np.sqrt(dt)
    
    for t in range(1, M + 1):
        # Generate random returns
        z = np.random.standard_normal(num_simulations)
        paths[:, t] = paths[:, t-1] * np.exp(-0.5 * vol**2 * dt + vol * np.sqrt(dt) * z)
    
    return paths

def simulate_crypto_price_paths(
    current_price, time_increment, time_length, num_simulations, start_time: str | None = None
):
    """
    Simulate multiple crypto asset price paths.
    """
    
    if start_time is None:
        start_time = datetime.now().isoformat()
    
    simulations = simulate_garch_price_paths(current_price, start_time,time_increment, time_length, num_simulations)

    print(simulations)

    predictions = convert_prices_to_time_format(
        simulations.tolist(), str(start_time), time_increment
    )
    # Create simulations directory in project root's public folder
    sim_dir = os.path.join("../../public/garch", str(int(datetime.fromisoformat(start_time).timestamp())))
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

def main():

    start_time = "2025-02-04T01:38:00+00:00"

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
    
    # Create path and save file
    score_path = os.path.join("../../public/garch", str(publish_time), "score.json")
    with open(score_path, 'w') as f:
        json.dump(score_data, f, indent=2)

    print(f"Score data saved to: {score_path}")

if __name__ == "__main__":
    main()
