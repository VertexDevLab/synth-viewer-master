import { readdir } from "fs/promises";
import { join } from "path";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const simulationsPath = join(process.cwd(), "public/monte-claude");
    const files = await readdir(simulationsPath);

    return NextResponse.json(files);
  } catch (error) {
    console.error("Error reading simulations directory:", error);
    return NextResponse.json(
      { error: "Failed to load simulations" },
      { status: 500 }
    );
  }
}
