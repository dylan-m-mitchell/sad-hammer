// A display-only mirror of the backend doctrine rule. The backend remains the
// source of truth for plans; this lets the roster panel and deployment guide
// label units before a plan has loaded.
export const DOCTRINE_LABELS = {
  press: "Press",
  support: "Support",
  hold: "Hold",
};

export const DOCTRINE_STYLES = {
  press: "border-rose-500/30 bg-rose-500/10 text-rose-200",
  support: "border-sky-500/30 bg-sky-500/10 text-sky-200",
  hold: "border-amber-500/30 bg-amber-500/10 text-amber-200",
};

export const DOCTRINE_TEXT = {
  press: "text-rose-300",
  support: "text-sky-300",
  hold: "text-amber-300",
};

const HOLD_KEYWORDS = new Set(["hero", "hold", "defensive"]);

export function classifyUnit(unit) {
  const keywords = (unit.keywords || []).map((keyword) =>
    String(keyword).trim().toLowerCase()
  );
  if (keywords.some((keyword) => HOLD_KEYWORDS.has(keyword))) return "hold";
  if (
    (unit.weapons || []).some((weapon) => Number(weapon.range) > 0)
  ) {
    return "support";
  }
  return "press";
}

export function unitsByDoctrine(roster) {
  const groups = { press: [], support: [], hold: [] };
  (roster?.units || []).forEach((unit) => {
    groups[classifyUnit(unit)].push(unit);
  });
  return groups;
}
