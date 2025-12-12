import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from scipy.ndimage import gaussian_filter1d
from helpers import get_real_price_path
from db import analytics as analytics_model
from db import create_database_engine

class DetailedTAPredictor:
    def __init__(self, ta_data):
        self.ta_data = ta_data
        
    def convert_direction_to_impact(self, direction):
        """Convert indicator direction to numerical impact"""
        direction_map = {
            'strong_buy': 2.0,
            'buy': 1.0, 
            'neutral': 0.0,
            'sell': -1.0,      
            'strong_sell': -2.0,
            'overbought': -3.0,
            'oversold': 3.0
        }
        return direction_map.get(direction, 0.0)
        
    def calculate_timeframe_impact(self, timeframe_data):
        """Calculate total impact from all indicators in a timeframe"""
        # Get overall forecast direction
        overall_impact = self.convert_direction_to_impact(timeframe_data['direction'])
        ma_impact = self.convert_direction_to_impact(timeframe_data['ma']['direction'])
        ta_impact = self.convert_direction_to_impact(timeframe_data['ta']['direction'])
        
        # Final weighted impact (overall forecast has highest weight)
        final_impact = overall_impact * 0.5 + ma_impact * 0.3 + ta_impact * 0.2
        
        return final_impact
    
    def calculate_market_volatility(self, timeframe_data):
        """Calculate market volatility based on forecast strength"""
        # Get the forecast direction
        forecast = timeframe_data['forecast']
        
        # Base volatility by signal strength
        if forecast in ['Overbought', 'Oversold']:
            base_vol = 0.0025  # Highest volatility for extreme conditions (0.25%)
        elif forecast in ['Strong sell', 'Strong buy']:
            base_vol = 0.0020  # High volatility for strong signals (0.20%)
        elif forecast in ['Sell', 'Buy']:
            base_vol = 0.0015  # Medium volatility for regular signals (0.15%)
        else:
            base_vol = 0.0010  # Low volatility for neutral signals (0.10%)
            
        # Use RSI to adjust volatility (more extreme RSI = higher volatility)
        rsi = float(timeframe_data['indicators'][1]['value'])
        rsi_factor = abs(50 - rsi) / 50  # 0 to 1 scale
        
        # Use ADX to adjust volatility (higher ADX = higher volatility)
        adx = float(timeframe_data['indicators'][5]['value']) / 100  # 0 to 1 scale
        
        # Combine factors
        volatility = base_vol * (1 + rsi_factor * 0.3 + adx * 0.3)
        
        return volatility

    def generate_smooth_path(self, initial_price, timeframe_impacts, intervals=288):
        """
        Generate a smooth price path based on technical analysis
        """
        # Create a coarse path first (fewer points)
        coarse_intervals = 25  # 24 hours with 1-hour intervals
        coarse_path = np.zeros(coarse_intervals)
        coarse_path[0] = initial_price
        
        # Calculate timeframe weights for coarse path
        timeframe_weights = {
            'm5': 0.05,
            'm15': 0.05,
            'm30': 0.10,
            'h1': 0.30,
            'h4': 0.35,
            'd1': 0.15
        }
        
        # Calculate total impact
        total_impact = 0
        for timeframe, weight in timeframe_weights.items():
            total_impact += timeframe_impacts[timeframe] * weight
        print(f"Total impact: {total_impact}")
        # Determine smoothing sigma based on signal strength
        timeframes = ['m5', 'm15', 'm30', 'h1', 'h4', 'd1']
        strong_signals = sum(abs(self.convert_direction_to_impact(self.ta_data[tf]['direction'])) >= 2 for tf in timeframes)
        # Adjust sigma: more strong signals = higher sigma (more smoothing)
        sigma = 1 + (strong_signals / len(timeframes)) * 7  # Scale from 1 (neutral) to 8 (all strong signals)
        print(f"Sigma: {sigma}")

        sell_count = sum(self.ta_data[tf]['direction'] in ['strong_sell', 'sell'] for tf in timeframes)
        oversold_count = sum(self.ta_data[tf]['direction'] == 'oversold' for tf in timeframes)
        
        # Adjust impact based on sell signals and oversold conditions
        if sell_count >= 4:  # At least 4 timeframes show sell signals
            if total_impact > -0.2:
                total_impact = -0.3  # Moderate negative trend for regular sells
            if all(self.ta_data[tf]['direction'] == 'strong_sell' for tf in timeframes):
                total_impact = -0.4  # Stronger negative trend for strong sells
        
        # Reduce negative impact if market is oversold
        if oversold_count >= 3:  # At least 3 timeframes show oversold
            total_impact = max(total_impact, -0.15)  # Limit downside during oversold conditions
        
        print(f"Total impact for path generation: {total_impact}")
        
        # Generate hourly price changes
        for i in range(1, coarse_intervals):
            # Smaller changes at the beginning, larger in the middle, smaller at the end
            position_factor = 1.0 - abs(i/coarse_intervals - 0.5) * 2
            hour_impact = total_impact * (1 + position_factor * 0.5)
            
            # Calculate price change
            price_change = hour_impact * 0.005  # 0.5% max change per hour
            coarse_path[i] = coarse_path[i-1] * (1 + price_change)
        # Interpolate to get 5-minute intervals
        interp_ratio = intervals // (coarse_intervals - 1)
        fine_path = np.zeros(intervals + 1)
        
        for i in range(coarse_intervals - 1):
            start_val = coarse_path[i]
            end_val = coarse_path[i + 1]
            
            # Linear interpolation
            for j in range(interp_ratio):
                idx = i * interp_ratio + j
                t = j / interp_ratio
                fine_path[idx] = start_val * (1 - t) + end_val * t

        # Fill in the last section
        fine_path[(coarse_intervals-1)*interp_ratio:] = coarse_path[-1]
        # Apply Gaussian smoothing with dynamic sigma
        smooth_path = gaussian_filter1d(fine_path, sigma=sigma)
        return smooth_path

    def predict_base_path(self, initial_price, intervals=288):
        """
        Predict smooth base price path
        """
        # Calculate impacts for each timeframe
        timeframe_impacts = {}
        for timeframe in ['m5', 'm15', 'm30', 'h1', 'h4', 'd1']:
            timeframe_impacts[timeframe] = self.calculate_timeframe_impact(self.ta_data[timeframe])
        print(f"Timeframe impacts: {timeframe_impacts}")
        # Generate smooth path
        path = self.generate_smooth_path(initial_price, timeframe_impacts, intervals)
        
        return path

    def generate_simulation_paths(self, base_path, num_paths=100):
        """
        Generate multiple price paths using Gaussian distribution around base path
        """
        # Initialize array for all paths
        all_paths = np.zeros((len(base_path), num_paths))
        all_paths[0] = base_path[0]  # All paths start from same point
        
        # Calculate average volatility for each timeframe
        timeframe_volatilities = {}
        for timeframe in ['m5', 'm15', 'm30', 'h1', 'h4', 'd1']:
            timeframe_volatilities[timeframe] = self.calculate_market_volatility(self.ta_data[timeframe])
        
        print(f"Timeframe volatilities: {timeframe_volatilities}")
        
        # Calculate average volatility
        avg_volatility = sum(timeframe_volatilities.values()) / len(timeframe_volatilities)
        print(f"Average volatility: {avg_volatility:.6f}")
        
        # Generate paths using proper Gaussian distribution
        for i in range(1, len(base_path)):
            # Calculate base percentage change
            base_change = (base_path[i] - base_path[i-1]) / base_path[i-1]
            
            # Determine which timeframe's volatility to use based on interval
            if i <= 12:  # First hour (5-min intervals)
                volatility = (timeframe_volatilities['m5'] + timeframe_volatilities['m15'] + timeframe_volatilities['m30']) / 3
            elif i <= 48:  # Next 3 hours
                volatility = timeframe_volatilities['h1']
            elif i <= 144:  # Next 8 hours
                volatility = timeframe_volatilities['h4']
            else:  # Remainder of day
                volatility = timeframe_volatilities['d1']
                
            # Generate random changes using Gaussian distribution
            # Pure Gaussian distribution with no skew
            random_changes = np.random.normal(base_change, volatility, num_paths)
            
            # Apply changes to all paths
            all_paths[i] = all_paths[i-1] * (1 + random_changes)
        
        return all_paths

    def predict_price_paths(self, initial_price, num_paths=100, intervals=289):
        """
        Predict multiple price paths using technical analysis and simulation
        """
        # Get base path from technical analysis
        base_path = self.predict_base_path(initial_price, intervals)
        
        # Calculate total change in base path
        final_price = base_path[-1]
        total_change = ((final_price - initial_price) / initial_price) * 100
        print(f"Base path: Initial ${initial_price:.2f}, Final ${final_price:.2f}, Change {total_change:.2f}%")
        
        # Generate simulation paths
        return self.generate_simulation_paths(base_path, num_paths)

def format_prediction_summary(price_array):
    """Format prediction results from multiple paths"""
    initial_price = price_array[0, 0]  # First price of base path
    final_price = price_array[-1, 0]   # Last price of base path
    
    timeframes = {
        '5min': 1,
        '15min': 3,
        '30min': 6,
        '1hour': 12,
        '4hour': 48,
        '12hour': 144,
        '24hour': 288
    }
    
    summary = {
        'initial_price': initial_price,
        'final_price': final_price,
        'total_change_percent': ((final_price - initial_price) / initial_price) * 100,
        'timeframe_prices': {}
    }
    
    for timeframe, intervals in timeframes.items():
        if intervals < len(price_array):
            price = price_array[intervals, 0]  # Get price from base path
            change = ((price - initial_price) / initial_price) * 100
            summary['timeframe_prices'][timeframe] = {
                'price': price,
                'change_percent': change
            }
    
    return summary


def analytics_simulation(initial_price: float, time_increment: int, time_length: int, num_simulations: int):
    # Your detailed technical analysis data
    engine = create_database_engine() 
    with engine.connect() as connection:
        query = analytics_model.select().order_by(analytics_model.c.created_at.desc()).limit(1)
        result = connection.execute(query).fetchone()
    
    ta_data = result.data
    id = result.id
    print(f"Analytics ID: {id}")
    predictor = DetailedTAPredictor(ta_data)
    
    intervals = int(time_length / time_increment)
    price_array = predictor.predict_price_paths(initial_price, num_simulations, intervals)
    summary = format_prediction_summary(price_array)
    
    # Print results
    print("\n😊😊 Bitcoin Price Prediction Summary:")
    print(f"Initial Price: ${summary['initial_price']:,.2f}")
    print(f"Final Price (24h): ${summary['final_price']:,.2f}")
    print(f"Total Change: {summary['total_change_percent']:.2f}%")
    
    print("\nPrice Predictions by Timeframe:")
    for timeframe, data in summary['timeframe_prices'].items():
        print(f"{timeframe}:")
        print(f"  Price: ${data['price']:,.2f}")
        print(f"  Change: {data['change_percent']:.2f}%")

    return np.array(price_array.T)

def main():
    start_time = "2025-02-26T07:38:00.000Z"
    start_time_parsed = datetime.fromisoformat(start_time) - timedelta(days=1)
    current_price = get_real_price_path(asset="BTC", duration=86400, time_increment=5, resolution=1, start_time=start_time_parsed.isoformat())[-1]["price"]
    simulations = analytics_simulation(initial_price=current_price, time_increment=300, time_length=24*60*60, num_simulations=100)
    print(simulations.shape)
    with open("simulations.json", "w") as f:
        json.dump(simulations.tolist(), f, indent=2)
if __name__ == "__main__":
    main()

