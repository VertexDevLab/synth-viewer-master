interface PricePath {
  time: string;
  price: number;
}

interface CRPSDetail {
  Interval: string;
  Increment: number | "Total";
  CRPS: number;
}

interface ScoringIntervals {
  [key: string]: number;
}

export function checkIfOneDayAgo(date: string) {
  return new Date(date).getTime() / 1000 + 86400 < Date.now() / 1000;
}

export function calculateCRPSForMiner(
  simulationRuns: PricePath[][],
  realPricePath: PricePath[],
  timeIncrement: number
): [number, CRPSDetail[]] {
  const scoringIntervals: ScoringIntervals = {
    "5min": 300,    // 5 minutes
    "30min": 1800,  // 30 minutes
    "3hour": 10800, // 3 hours
    "24hour": 86400 // 24 hours
  };

  const detailedCrpsData: CRPSDetail[] = [];
  let sumAllScores = 0;

  // Convert price paths to arrays of prices
  const simulatedPrices = simulationRuns.map(run => 
    run.map(point => point.price)
  );
  const realPrices = realPricePath.map(point => point.price);

  for (const [intervalName, intervalSeconds] of Object.entries(scoringIntervals)) {
    const intervalSteps = Math.floor(intervalSeconds / timeIncrement);

    // Calculate price changes
    const simulatedChanges = calculatePriceChangesOverIntervals(
      simulatedPrices,
      intervalSteps
    );
    const realChanges = calculatePriceChangesOverIntervals(
      [realPrices],
      intervalSteps
    )[0];

    // Calculate CRPS over intervals
    const numIntervals = Math.min(simulatedChanges[0].length, realChanges.length);
    const crpsValues: number[] = new Array(numIntervals).fill(0);

    for (let t = 0; t < numIntervals; t++) {
      const forecasts = simulatedChanges.map(path => path[t]);
      const observation = realChanges[t];
      crpsValues[t] = calculateCRPSEnsemble(observation, forecasts);

      detailedCrpsData.push({
        Interval: intervalName,
        Increment: t + 1,
        CRPS: crpsValues[t]
      });
    }

    // Total CRPS for this interval
    const totalCrpsInterval = crpsValues.reduce((a, b) => a + b, 0);
    sumAllScores += totalCrpsInterval;

    detailedCrpsData.push({
      Interval: intervalName,
      Increment: "Total",
      CRPS: totalCrpsInterval
    });
  }

  return [sumAllScores, detailedCrpsData];
}

function calculatePriceChangesOverIntervals(
  pricePaths: number[][],
  intervalSteps: number
): number[][] {
  return pricePaths.map(path => {
    const changes: number[] = [];
    for (let i = intervalSteps; i < path.length; i += intervalSteps) {
      changes.push(path[i] - path[i - intervalSteps]);
    }
    return changes;
  });
}

function calculateCRPSEnsemble(observation: number, forecasts: number[]): number {
  // Implementation of Continuous Ranked Probability Score
  // This is a simplified version of the properscoring.crps_ensemble
  let crps = 0;
  const n = forecasts.length;

  // Sort forecasts for empirical CDF
  const sortedForecasts = [...forecasts].sort((a, b) => a - b);

  for (let i = 0; i < n; i++) {
    // Calculate empirical CDF at each forecast point
    const p = (i + 1) / n;
    const forecast = sortedForecasts[i];
    
    // Heaviside step function at observation
    const H = observation <= forecast ? 1 : 0;
    
    // Integrate squared difference between CDF and Heaviside function
    crps += (p - H) ** 2;
  }

  return crps / n;
}