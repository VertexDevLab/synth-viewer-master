import axios from "axios";
import { NextResponse } from "next/server";

export const GET = async (
  req: Request,
  { params }: { params: { miner_uid: string } }
) => {
  const { miner_uid } = params;
  const { searchParams } = new URL(req.url);
  const start_time = searchParams.get("start_time");
  const API_KEY = process.env.SYNTH_API_KEY;
  try {
    const response = await axios.get(
      `https://synth.mode.network/prediction/historical?miner=${miner_uid}&asset=BTC&start_time=${start_time}&time_increment=300&time_length=86400`,
      {
        headers: {
          Authorization: `Apikey ${API_KEY}`,
        },
      }
    );

    return NextResponse.json(response.data[0]);
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to fetch data" },
      { status: 500 }
    );
  }
};
