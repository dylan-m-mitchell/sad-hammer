const JSON_HEADERS = { "Content-Type": "application/json" };

async function request(path, options = {}) {
  const response = await fetch(path, options);
  let payload = null;
  try {
    payload = await response.json();
  } catch (error) {
    if (response.ok) {
      const formatError = new Error("Response returned invalid JSON");
      formatError.status = response.status;
      formatError.payload = null;
      throw formatError;
    }
    payload = null;
  }
  if (!response.ok) {
    const message =
      (payload && payload.error) ||
      `Request failed with status ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

export function fetchTableRosters() {
  return request("/api/table/rosters");
}

export function validateRoster(roster) {
  return request("/api/table/rosters/validate", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(roster),
  });
}

export function fetchTablePlan(
  { playerRoster, aiRoster, round, seed, destroyed },
  signal
) {
  return request("/api/table/plan", {
    method: "POST",
    headers: JSON_HEADERS,
    signal,
    body: JSON.stringify({
      player_roster: playerRoster,
      ai_roster: aiRoster,
      round,
      seed,
      destroyed,
    }),
  });
}
