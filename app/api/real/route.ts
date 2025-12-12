import { NextResponse } from "next/server";
import axios from "axios";

export async function GET(request: Request) {
  try {

    const { searchParams } = new URL(request.url);
    const cid = searchParams.get("cid");
    const url = "https://benchmarks.pyth.network/v1/shims/tradingview/history";
    const params = {
      symbol: "Crypto.BTC/USD",
      resolution: 1,
      from: cid,
      to: Number(cid) + 86400,
    };

    const response = await axios.get(url, {
      params,
    });

    return NextResponse.json(response.data);
  } catch (error) {
    console.error("Error fetching real data:", error);
    return NextResponse.json(

      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
