const ROSTERS_KEY = "sadhammer.table.rosters";
const SESSION_KEY = "sadhammer.table.session";
export const TOTAL_ROUNDS = 5;

function isRoster(value) {
  return (
    value &&
    typeof value === "object" &&
    typeof value.name === "string" &&
    Array.isArray(value.units) &&
    value.units.length > 0
  );
}

export function loadRosters() {
  if (typeof window === "undefined") return null;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(ROSTERS_KEY));
    if (parsed && isRoster(parsed.player) && isRoster(parsed.ai)) {
      return parsed;
    }
  } catch (error) {
    // A malformed save falls back to the starter rosters.
  }
  return null;
}

export function saveRosters(rosters) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(ROSTERS_KEY, JSON.stringify(rosters));
  } catch (error) {
    // Storage can be full or disabled; the app still works for this session.
  }
}

export function createSeed() {
  return Math.floor(Math.random() * 2_147_483_647);
}

export function loadSession() {
  if (typeof window === "undefined") return null;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(SESSION_KEY));
    if (!parsed || typeof parsed !== "object") return null;
    const seed = Number.isInteger(parsed.seed) ? parsed.seed : createSeed();
    const round = Number.isInteger(parsed.round)
      ? Math.min(Math.max(parsed.round, 1), TOTAL_ROUNDS)
      : 1;
    const destroyed = Array.isArray(parsed.destroyed)
      ? parsed.destroyed.filter((item) => typeof item === "string")
      : [];
    return {
      seed,
      round,
      destroyed,
      checklist: {
        objectives: Boolean(parsed.checklist?.objectives),
        terrain: Boolean(parsed.checklist?.terrain),
        playerDeploy: Boolean(parsed.checklist?.playerDeploy),
        aiDeploy: Boolean(parsed.checklist?.aiDeploy),
      },
    };
  } catch (error) {
    return null;
  }
}

export function saveSession(session) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch (error) {
    // Non-fatal: the current round still works without persistence.
  }
}
