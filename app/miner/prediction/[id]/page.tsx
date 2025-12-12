"use client";

import { useEffect, useState } from "react";
import SimulationChart from "@/app/ui/dashboard/simulation";
import axios, { AxiosResponse } from "axios";
import { Price, ScoreData, SimulationData, AnalyticsData } from "@/app/types";
import ScoreChart from "@/app/ui/dashboard/score";
import { PriceData, transformData } from "@/app/api/real/helper";
import JsonView from "@uiw/react-json-view";
import { vscodeTheme } from "@uiw/react-json-view/vscode";

export default function Page({ params }: { params: { id: string } }) {
  const [data, setData] = useState<SimulationData | null>(null);
  const [score, setScore] = useState<ScoreData | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);

  const fetchSimulationData = async () => {
    try {
      const simulation: AxiosResponse<SimulationData> = await axios.get(
        `/api/miner/simulation/${params.id}`
      );
      const cid =
        new Date(
          simulation.data.prediction?.[0]?.[0]?.time as string
        ).getTime() / 1000;

      let combinedData: Price[][] = [];
      if (cid + 86400 < Date.now() / 1000) {
        const real: AxiosResponse<PriceData> = await axios.get(
          `/api/real?cid=${cid}`
        );
        const transformedData = transformData(real.data);
        combinedData = [
          transformedData,
          ...(simulation.data.prediction as Price[][]),
        ];

        setData({
          variable: simulation.data.variable,
          prediction: combinedData,
        });
      } else {
        setData(simulation.data);
      }
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  const fetchScore = async () => {
    try {
      const res: AxiosResponse<ScoreData> = await axios.get(
        `/prediction_score/score_${params.id}.json`
      );
      setScore(res.data);
    } catch (error) {
      console.error("Error fetching score:", error);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const analytics_id = data?.variable?.analytics_id;
      const res: AxiosResponse<AnalyticsData> = await axios.get(
        `/api/analytics/${analytics_id}`
      );
      setAnalytics(res.data);
    } catch (error) {
      console.error("Error fetching analytics:", error);
    }
  };
  useEffect(() => {
    fetchSimulationData();
  }, [params.id]);

  useEffect(() => {
    if (data?.prediction?.length && data.prediction.length > 1) {
      fetchScore();
    }
  }, [data]);

  useEffect(() => {
    if (data?.variable?.analytics_id) {
      fetchAnalytics();
    }
  }, [data]);

  return (
    <div className="p-4">
      {data && <SimulationChart data={data} />}
      {score && <ScoreChart data={score} />}
      {analytics && <JsonView value={analytics.data} />}
    </div>
  );
}
