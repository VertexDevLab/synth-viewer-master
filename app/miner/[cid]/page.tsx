"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import axios from "axios";
import { useParams } from "next/navigation";
import { SimulationData } from "@/app/types";
import { checkIfOneDayAgo } from "@/app/lib/helpers";
export default function SimulationsPage() {
  const [predictions, setPredictions] = useState<SimulationData[]>([]);
  const [loading, setLoading] = useState(true);
  const { cid } = useParams();
  useEffect(() => {
    const fetchPredictions = async () => {
      try {
        const response = await axios.get(`/api/miner/${cid}`);
        setPredictions(response.data);
      } catch (error) {
        console.error("Error fetching simulations:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchPredictions();
  }, []);

  if (loading) {
    return <div className="p-4">Loading simulations...</div>;
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">My Predictions</h1>
      <div className="">
        {predictions.map((prediction) => (
          <div className="flex justify-between items-center">
            <Link
              key={prediction.id}
              href={`/miner/prediction/${prediction.id}`}
              className={`p-4 bg-white rounded-lg shadow hover:shadow-md transition-shadow ${!checkIfOneDayAgo(prediction.request_time as string) ? "opacity-50" : ""}`}
            >
              <div className="flex justify-between items-center">
                <span className="text-gray-700">
                  Prediction {prediction.id}
                </span>
              </div>
            </Link>

            <span className="text-gray-700">{prediction.request_time}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
