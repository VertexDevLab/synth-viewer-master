import { NextResponse } from "next/server";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

export async function GET(
  request: Request,
  { params }: { params: { cid: string } }
) {
  try {
    const minerData = await prisma.my_predictions.findMany({
      where: {
        miner_uid: Number(params.cid),
      },
      select: {
        id: true,
        request_time: true,
        prediction: false,
      },
      orderBy: {
        id: "asc",
      },
    });

    if (!minerData.length) {
      return NextResponse.json({ error: "Miner not found" }, { status: 404 });
    }

    // Convert BigInt to Number before serializing
    const serializedData = minerData.map((item: any) => ({
      ...item,
      id: Number(item.id),
    }));

    return NextResponse.json(serializedData);
  } catch (error) {
    console.error("Error fetching miner data:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  } finally {
    await prisma.$disconnect();
  }
}

export async function POST(
  request: Request,
  { params }: { params: { cid: string } }
) {
  try {
    const minerData = await prisma.my_predictions.findMany({
      where: {
        miner_uid: Number(params.cid),
      },
      orderBy: {
        id: "asc",
      },
    });

    // await prisma.my_predictions.update({
    //   where: {
    //     id: minerData[0].id,
    //   },
    //   data: {
    //     request_time: new Date(minerData[0].prediction[0][0].time),
    //   },
    // });
    minerData.forEach(async (miner: any) => {
      await prisma.my_predictions.update({
        where: {
          id: miner.id,
        },
        data: {
          request_time: new Date(miner.prediction[0][0].time),
        },
      });
    });

    return NextResponse.json(
      { message: "Predictions updated" },
      { status: 200 }
    );
  } catch (error) {
    console.error("Error updating miner data:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
