import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { SimulationData } from "@/app/types";
import { useEffect } from "react";
import axios from "axios";

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export default function SimulationChart({ data }: { data: SimulationData }) {
  // Create time labels for each data point
  const timeLabels = Array.from(
    {
      length: data.prediction?.[0]?.length,
    },
    (_, i) => {
      // Each point represents time_increment seconds
      const totalSeconds = i * 300;
      const hours = totalSeconds / 3600;

      // Only show label for every hour (when hours is a whole number)
      if (Number.isInteger(hours)) {
        return hours;
      }
      return "";
    }
  );

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: "Price Simulation",
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: "Time (hours)",
        },
        ticks: {
          // stepSize: 1,
          maxRotation: 0,
          autoSkip: true,
          autoSkipPadding: 6,
        },
        grid: {
          display: true,
        },
      },
      y: {
        title: {
          display: true,
          text: "Price",
        },
        grid: {
          display: true,
        },
      },
    },
  };

  // Create datasets for each simulation
  const datasets = data.prediction.map((simulation, index) => ({
    label: `Simulation ${index + 1}`,
    data: simulation.map((price) => price.price),
    borderColor:
      data.prediction.length > 100 && index === 0
        ? "rgb(75, 192, 192)"
        : `rgba(75, 192, 192, 0.1)`,
    borderWidth: data.prediction.length > 100 && index === 0 ? 2 : 1,
    tension: 0.1,
    pointRadius: 0,
  }));

  const chartData = {
    labels: timeLabels,
    datasets,
  };

  return (
    <div className="w-full h-full">
      <Line
        options={chartOptions}
        data={chartData}
        className="!w-full !h-full"
      />
      <div className="flex justify-between">
        <p>
          Start Time: {data.variable?.start_time || data.prediction[0][0].time}
        </p>
        <p>Sigma: {data.variable?.sigma}</p>
        <p>Volatility Type: {data.variable?.volatility_type}</p>
        <p>Mean: {data.variable?.mean}</p>
        <p>Std: {data.variable?.std}</p>
        <p>Model: {data.variable?.model}</p>
        <p>Analytics: {data.variable?.analytics_id}</p>
      </div>
    </div>
  );
}
