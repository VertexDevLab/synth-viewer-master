"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import axios from "axios";
import { useParams } from "next/navigation";
import { Score } from "@/app/types";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  FilterFn,
} from "@tanstack/react-table";
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
import { MY_UIDS } from "@/app/config";
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export default function SimulationsPage() {
  const [scores, setScores] = useState<Score[]>([]);
  const [loading, setLoading] = useState(true);
  const [globalFilter, setGlobalFilter] = useState("");
  // Define neuron UIDs with their specific colors
  const neuronConfig = MY_UIDS;

  const from = new Date(Date.now() - 6 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split("T")[0];
  const to = new Date().toISOString().split("T")[0];
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchHistoricalScores = async () => {
      try {
        setError("");
        const baseUrl =
          "https://synth.mode.network/validation/scores/historical";

        const params = new URLSearchParams({
          from: new Date(from).toISOString(),
          to: new Date(to).toISOString(),
        });

        const response = await axios.get(`${baseUrl}?${params}`);
        setScores(
          response.data.sort(
            (a: Score, b: Score) =>
              new Date(a.scored_time).getTime() -
              new Date(b.scored_time).getTime()
          )
        );
      } catch (error: any) {
        console.error("Error fetching simulations:", error);
        setError(error.response.data || "An error occurred");
        setScores([]);
      } finally {
        setLoading(false);
      }
    };

    fetchHistoricalScores();
  }, [from, to]);

  // Update columnHelper type
  const columnHelper = createColumnHelper<Score>();

  const columns = [
    columnHelper.accessor("miner_uid", {
      header: "Miner ID",
      cell: (info) => `Miner ${info.getValue()}`,
    }),

    columnHelper.accessor("prompt_score", {
      header: "Score",
      cell: (info) => info.getValue(),
    }),
    columnHelper.accessor("scored_time", {
      header: "Scored Time",
      cell: (info) => new Date(info.getValue()).toLocaleString(),
    }),
  ];

  const uniqueDates = [
    ...new Set(scores.map((item: Score) => item.scored_time)),
  ];

  const chartData = {
    labels: uniqueDates,
    datasets: neuronConfig.map(({ uid, color, label }) => ({
      label,
      data: uniqueDates.map((date) => {
        const dataPoint = scores.find(
          (item: Score) => item.scored_time === date && item.miner_uid === uid
        );
        return dataPoint ? dataPoint.prompt_score : null;
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
    return <div className="p-4">Loading simulations...</div>;
  }

  return (
    <div className="p-4">
      {scores?.length > 0 && (
        <h1 className="text-2xl font-bold mb-4">
          Historical Scores from {from} to {to}
        </h1>
      )}
      {scores?.length > 0 ? (
        <div className="w-full h-full">
          <Line data={chartData} options={options} />
        </div>
      ) : (
        <p className="text-gray-500 text-sm mt-1">No scores found</p>
      )}
    </div>
  );
}
