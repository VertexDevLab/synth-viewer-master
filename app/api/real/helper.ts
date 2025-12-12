export interface PriceData {
  t: number[];  // timestamps
  c: number[];  // close prices
}

interface TransformedPrice {
  time: string;
  price: number;
}

export function transformData(data: PriceData | null): TransformedPrice[] {
  if (!data || !data.t || !data.c || data.t.length === 0) {
    return [];
  }

  const { t: timestamps, c: closePrices } = data;
  const transformedData: TransformedPrice[] = [];

  // Create array from end to start, stepping by 5
  for (let i = timestamps.length - 1; i >= 0; i -= 5) {
    transformedData.push({
      time: new Date(timestamps[i] * 1000).toISOString(), // Convert Unix timestamp to ISO string
      price: Number(closePrices[i]),
    });
  }

  // Reverse to get chronological order
  return transformedData.reverse();
}