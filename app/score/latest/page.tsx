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
import { MY_UIDS } from "@/app/config";

export default function SimulationsPage() {
  const [scores, setScores] = useState<Score[]>([]);
  const [loading, setLoading] = useState(true);
  const [globalFilter, setGlobalFilter] = useState("");

  useEffect(() => {
    const fetchLatestScores = async () => {
      try {
        const response = await axios.get(
          `https://synth.mode.network/validation/scores/latest`
        );
        setScores(response.data);
      } catch (error) {
        console.error("Error fetching simulations:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchLatestScores();
  }, []);

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
    columnHelper.accessor("crps", {
      header: "CRPS score",
      cell: (info) => info.getValue(),
    }),
  ];

  const table = useReactTable({
    data: scores,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    state: {
      globalFilter,
    },
    onGlobalFilterChange: setGlobalFilter,
  });

  if (loading) {
    return <div className="p-4">Loading simulations...</div>;
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Available Simulations</h1>

      {/* Existing search input */}
      <div className="mb-4">
        <input
          type="text"
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Search all columns..."
          className="p-2 border rounded"
        />
      </div>
      <h1 className="text-2xl font-bold mb-4">
        Latest Scores at {scores[0].scored_time}
      </h1>
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse border">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                <th className="border p-2 bg-gray-100 cursor-pointer">#</th>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="border p-2 bg-gray-100 cursor-pointer"
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext()
                    )}
                    {{
                      asc: " 🔼",
                      desc: " 🔽",
                    }[header.column.getIsSorted() as string] ?? null}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row, index) => (
              <tr
                key={row.id}
                className={`${MY_UIDS.some((uid) => uid.uid === row.original.miner_uid) ? "bg-gray-100" : ""}`}
              >
                <td className="border p-2">
                  <Link
                    href={`/score/latest/${row.original.miner_uid}?start_time=${row.original.scored_time}`}
                    className="w-full block"
                  >
                    {index + 1}
                  </Link>
                </td>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="border p-2">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
