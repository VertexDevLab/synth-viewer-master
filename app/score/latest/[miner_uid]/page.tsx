"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import axios, { AxiosResponse } from "axios";
import { useParams, useSearchParams } from "next/navigation";
import { Price, Score, SimulationData } from "@/app/types";
import SimulationChart from "@/app/ui/dashboard/simulation";
import { PriceData, transformData } from "@/app/api/real/helper";

export default function SimulationsPage() {
  const [scores, setScores] = useState<Score[]>([]);
  const [prediction, setPrediction] = useState<SimulationData | null>(null);
  const [loading, setLoading] = useState(true);
  const { miner_uid } = useParams();
  const searchParams = useSearchParams();
  const start_time = searchParams.get("start_time");
  useEffect(() => {
    const fetchLatestMinerPrediction = async () => {
      try {
        const response: AxiosResponse<SimulationData> = await axios.get(
          `/api/score/latest/${miner_uid}?start_time=${new Date(
            new Date(start_time as string).getTime() - 1000 * 60 * 60 * 24
          ).toISOString()}`
        );
        const real: AxiosResponse<PriceData> = await axios.get(
          `/api/real?cid=${new Date(response.data.prediction[0][0].time).getTime() / 1000}`
        );
        const transformedData = transformData(real.data);
        const combinedData = {
          variable: response.data.variable,
          prediction: [transformedData, ...response.data.prediction],
        };
        setPrediction(combinedData);
      } catch (error) {
        console.error("Error fetching simulations:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchLatestMinerPrediction();
  }, []);

  if (loading) {
    return <div className="p-4">Loading simulations...</div>;
  }

  return (
    <div className="p-4">
      {prediction && <SimulationChart data={prediction} />}
      {/* {score && <ScoreChart data={score} />} */}
    </div>
  );
}
