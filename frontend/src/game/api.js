const JSON_HEADERS = { "Content-Type": "application/json" };

async function request(path, options = {}) {
  const response = await fetch(path, options);
  let payload = null;
  try {
    payload = await response.json();
  } catch (error) {
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

export function fetchOptions() {
  return request("/api/aos4/options");
}

export function createGame(settings) {
  return request("/api/aos4/games", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(settings),
  });
}

export function fetchGame(gameId) {
  return request(`/api/aos4/games/${encodeURIComponent(gameId)}`);
}

export function submitAction(gameId, action) {
  return request(`/api/aos4/games/${encodeURIComponent(gameId)}/actions`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ action }),
  });
}

export function resumeGame(gameId) {
  return request(`/api/aos4/games/${encodeURIComponent(gameId)}/resume`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({}),
  });
}

export function deleteGame(gameId) {
  return request(`/api/aos4/games/${encodeURIComponent(gameId)}`, {
    method: "DELETE",
  });
}

export function importGame(state) {
  return request("/api/aos4/games/import", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(state),
  });
}

export function exportUrl(gameId) {
  return `/api/aos4/games/${encodeURIComponent(gameId)}/export`;
}
