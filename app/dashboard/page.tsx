"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import axios from "axios";

export default function SimulationsPage() {
  const [simulations, setSimulations] = useState<string[]>([]);
  const [baseSimulations, setBaseSimulations] = useState<string[]>([]);
  const [monteSimulations, setMonteSimulations] = useState<string[]>([]);
  const [customSimulations, setCustomSimulations] = useState<string[]>([]);
  const [loopholeSimulations, setLoopholeSimulations] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCustomSimulations = async () => {
      try {
        const response = await axios.get("/api/custom");
        setCustomSimulations(response.data);
      } catch (error) {
        console.error("Error fetching custom simulations:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchCustomSimulations();
  }, []);

  useEffect(() => {
    const fetchGBMSimulations = async () => {
      try {
        const response = await axios.get("/api/gbm");
        setSimulations(response.data);
      } catch (error) {
        console.error("Error fetching GBM simulations:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchGBMSimulations();
  }, []);

  useEffect(() => {
    const fetchBaseSimulations = async () => {
      try {
        const response = await axios.get("/api/base");
        setBaseSimulations(response.data);
      } catch (error) {
        console.error("Error fetching base simulations:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchBaseSimulations();
  }, []);

  useEffect(() => {
    const fetchMonteSimuations = async () => {
      try {
        const response = await axios.get("/api/monte-claude");
        setMonteSimulations(response.data);
      } catch (error) {
        console.error("Error fetching monte simulations:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchMonteSimuations();
  }, []);

  useEffect(() => {
    const fetchLoopholeSimulations = async () => {
      const response = await axios.get("/api/loophole");
      setLoopholeSimulations(response.data);
    };

    fetchLoopholeSimulations();
  }, []);
  if (loading) {
    return <div className="p-4">Loading simulations...</div>;
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Available Simulations</h1>
      <div className="grid grid-cols-2 grid-rows-2 gap-10">
        <div className="border-r border-gray-500 pr-10">
          <h2 className="text-xl font-bold mb-4">Base Simulations</h2>
          {baseSimulations.map((sim) => (
            <div className="flex justify-between items-center">
              <Link
                key={sim}
                href={`/base/${sim}`}
                className="p-4 bg-white rounded-lg shadow hover:shadow-md transition-shadow"
              >
                <div className="flex justify-between items-center">
                  <span className="text-gray-700">Simulation</span>
                </div>
              </Link>
              <span className="text-gray-700">
                {sim} {new Date(Number(sim) * 1000).toISOString()}
              </span>
            </div>
          ))}
        </div>
        <div className="border-r border-gray-500 pr-10">
          <h2 className="text-xl font-bold mb-4">GBM Simulations</h2>

          {simulations.map((sim) => (
            <div className="flex justify-between items-center">
              <Link
                key={sim}
                href={`/gbm/${sim}`}
                className="p-4 bg-white rounded-lg shadow hover:shadow-md transition-shadow"
              >
                <div className="flex justify-between items-center">
                  <span className="text-gray-700">Simulation</span>
                </div>
              </Link>
              <span className="text-gray-700">
                {sim} {new Date(Number(sim) * 1000).toISOString()}
              </span>
            </div>
          ))}
        </div>
        <div>
          <h2 className="text-xl font-bold mb-4">Monte Simulations</h2>
          {monteSimulations.map((sim) => (
            <div className="flex justify-between items-center">
              <Link
                key={sim}
                href={`/monte-claude/${sim}`}
                className="p-4 bg-white rounded-lg shadow hover:shadow-md transition-shadow"
              >
                <span className="text-gray-700">Simulation</span>
              </Link>
              <span className="text-gray-700">
                {sim} {new Date(Number(sim) * 1000).toISOString()}
              </span>
            </div>
          ))}
        </div>
        <div>
          <h2 className="text-xl font-bold mb-4">Loophole Simulations</h2>
          {loopholeSimulations.map((sim) => (
            <div className="flex justify-between items-center">
              <Link href={`/loophole/${sim}`}>
                <span className="text-gray-700">Simulation</span>
              </Link>
              <span className="text-gray-700">
                {sim} {new Date(Number(sim) * 1000).toISOString()}
              </span>
            </div>
          ))}
        </div>
        {/* <div>
          <h2 className="text-xl font-bold mb-4">Custom Simulations</h2>
          {customSimulations.map((sim) => (
            <div className="flex justify-between items-center">
              <Link href={`/custom/${sim}`}>
                <span className="text-gray-700">Simulation</span>
              </Link>
              <span className="text-gray-700">
                {sim} {new Date(Number(sim) * 1000).toISOString()}
              </span>
            </div>
          ))}
        </div> */}
      </div>
    </div>
  );
}
