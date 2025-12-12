import { NextResponse } from "next/server";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    const simulation = await prisma.my_predictions.findUnique({
      where: {
        id: Number(id),
      },
    });

    // Convert BigInt values to Numbers before serializing
    const serializedSimulation = simulation
      ? {
          ...simulation,
          id: Number(simulation.id),
        }
      : null;

    return NextResponse.json(serializedSimulation);
  } catch (error) {
    console.error("Error fetching simulation:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
