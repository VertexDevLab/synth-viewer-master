import { ScoreData } from "@/app/types";
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
import { Line } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export default function ScoreChart({ data }: { data: ScoreData }) {
  // Group scores by interval
  const scoresByInterval: {
    [key: string]: { increment: number; crps: number }[];
  } = {};

  // Map to convert interval names to minutes for scaling
  const intervalToMinutes = {
    "5min": 5,
    "30min": 30,
    "3hour": 180,
    "24hour": 1440,
  };

  data.detailed_scores.forEach((score) => {
    if (score.Increment !== "Total") {
      if (!scoresByInterval[score.Interval]) {
        scoresByInterval[score.Interval] = [];
      }
      // Scale the increment to hours
      const scaledIncrement =
        ((score.Increment as number) *
          intervalToMinutes[score.Interval as keyof typeof intervalToMinutes]) /
        60;
      scoresByInterval[score.Interval].push({
        increment: scaledIncrement,
        crps: score.CRPS,
      });
    }
  });

  // Get all time points for x-axis (based on hours)
  const timePoints = scoresByInterval["5min"].map((score) => score.increment);

  const chartData = {
    labels: timePoints,
    datasets: Object.entries(scoresByInterval).map(([interval, scores]) => ({
      label: interval,
      data: scores.map((score) => ({
        x: score.increment,
        y: score.crps,
      })),
      borderColor:
        interval === "5min"
          ? "rgb(53, 162, 235)"
          : interval === "30min"
          ? "rgb(255, 99, 132)"
          : interval === "3hour"
          ? "rgb(75, 192, 192)"
          : "rgb(255, 159, 64)",
      backgroundColor: "transparent",
      tension: 0.1,
      pointRadius: interval === "5min" ? 2 : 4,
    })),
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: "top" as const,
      },
      title: {
        display: true,
        text: "CRPS Scores Over Time",
      },
      tooltip: {
        callbacks: {
          title: (context: any) => {
            const hours = context[0].parsed.x;
            return `Time: ${hours} hours`;
          },
        },
      },
    },
    scales: {
      y: {
        title: {
          display: true,
          text: "CRPS Score",
        },
        beginAtZero: true,
      },
      x: {
        title: {
          display: true,
          text: "Time (hours)",
        },
        ticks: {
          maxRotation: 0,
          autoSkip: true,
          autoSkipPadding: 6,
          callback: function (tickValue: number | string) {
            const value = Number(tickValue);
            if (Number.isInteger(value)) {
              return value;
            }
            return "";
          },
        },
        grid: {
          display: true,
        },
        beginAtZero: true,
      },
    },
  };

  return (
    <div className="w-full h-[600px]">
      <Line options={options} data={chartData} className="!w-full !h-full" />
      <p>Total CRPS: {data.total_score}</p>
    </div>
  );
}
