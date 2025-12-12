"use client";

import { useEffect, useState } from "react";
import SimulationChart from "@/app/ui/dashboard/simulation";
import axios, { AxiosResponse } from "axios";
import { Price, ScoreData, SimulationData } from "@/app/types";
import ScoreChart from "@/app/ui/dashboard/score";

export default function Page({ params }: { params: { cid: string } }) {
  const [data, setData] = useState<SimulationData | null>(null);
  const [score, setScore] = useState<ScoreData | null>(null);

  const fetchSimulationData = async () => {
    try {
      const simulation: AxiosResponse<SimulationData> = await axios.get(
        `/custom/${params.cid}/simulation.json`
      );
      const real: AxiosResponse<Price[]> = await axios.get(
        `/real/${params.cid}/real.json`
      );

      const combinedData = {
        variable: simulation.data.variable,
        prediction: [real.data, ...simulation.data.prediction],
      };
      setData(combinedData);
    } catch (error) {
      console.error("Error fetching base simulation data:", error);
    }
  };

  const fetchScore = async () => {
    try {
      const res = await axios.get(`/custom/${params.cid}/score.json`);
      setScore(res.data);
    } catch (error) {
      console.error("Error fetching score:", error);
    }
  };
  useEffect(() => {
    fetchSimulationData();
    fetchScore();
  }, [params.cid]);

  return (
    <div className="p-4">
      {data && <SimulationChart data={data} />}
      {score && <ScoreChart data={score} />}
    </div>
  );
}
