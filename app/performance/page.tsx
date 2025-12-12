"use client";

import { useEffect, useState } from "react";
import axios from "axios";
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
import { MY_UIDS } from "../config";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface PerformanceData {
  updated_at: string;
  neuron_uid: number;
  incentive: number;
}

export default function PerformanceChart() {
  const [data, setData] = useState<PerformanceData[]>([]);
  const [loading, setLoading] = useState(true);

  // Define neuron UIDs with their specific colors
  const neuronConfig = MY_UIDS.map(({ uid, color, label }) => ({
    uid,
    color,
    label,
  }));

  useEffect(() => {
    const fetchData = async () => {
      const end_date = new Date(new Date().getTime() + 24 * 60 * 60 * 1000)
        .toISOString()
        .split("T")[0];
      const start_date = new Date(
        new Date(end_date).getTime() - 7 * 24 * 60 * 60 * 1000
      )
        .toISOString()
        .split("T")[0];

      const response = await axios.get(
        `https://synth.mode.network/leaderboard/historical?start_time=${start_date}&end_time=${end_date}`
      );

      const filteredData = response.data.filter((item: PerformanceData) =>
        neuronConfig.map((n) => n.uid).includes(item.neuron_uid)
      );
      setData(filteredData);
      setLoading(false);
    };
    fetchData();
  }, []);

  const uniqueDates = [
    ...new Set(data.map((item: PerformanceData) => item.updated_at)),
  ];

  const chartData = {
    labels: uniqueDates,
    datasets: neuronConfig.map(({ uid, color, label }) => ({
      label,
      data: uniqueDates.map((date) => {
        const dataPoint = data.find(
          (item: PerformanceData) =>
            item.updated_at === date && item.neuron_uid === uid
        );
        return dataPoint ? dataPoint.incentive : null;
      }),
      borderColor: color,
      backgroundColor: color,
      fill: false,
      tension: 0.1, // Adds slight curve to lines
      pointRadius: 2,
      pointHoverRadius: 5,
    })),
  };

  const options = {
    plugins: {
      tooltip: {
        callbacks: {
          label: function (context: any) {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(5)}`;
          },
        },
      },
    },
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="w-full h-full">
      <Line data={chartData} options={options} />
    </div>
  );
}
