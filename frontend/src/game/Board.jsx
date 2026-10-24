import React from "react";

const SIDE_COLORS = {
  player: {
    fill: "#0ea5e9",
    stroke: "#bae6fd",
    soft: "rgba(14,165,233,0.22)",
    text: "#082f49",
  },
  ai: {
    fill: "#f43f5e",
    stroke: "#fecdd3",
    soft: "rgba(244,63,94,0.22)",
    text: "#4c0519",
  },
};

const ACTION_COLORS = {
  move: "#fbbf24",
  run: "#fb923c",
  retreat: "#a78bfa",
  deploy: "#34d399",
  shoot: "#38bdf8",
  charge: "#f43f5e",
  fight: "#ef4444",
};

function tokenRadius(unit) {
  return Math.max(1.15, unit.base_radius * 1.2 + 0.6);
}

function healthColor(ratio) {
  if (ratio > 0.66) return "#34d399";
  if (ratio > 0.33) return "#fbbf24";
  return "#fb7185";
}

function objectiveColor(controller) {
  if (controller === "player") return "#0ea5e9";
  if (controller === "ai") return "#f43f5e";
  return "#a8a29e";
}

function pointKey(point) {
  return `${Number(point.x).toFixed(2)},${Number(point.y).toFixed(2)}`;
}

export default function Board({
  view,
  selectedUnitId,
  onSelectUnit,
  onAction,
  busy,
}) {
  const { board, units, objectives, terrain, deployment_zones: zones } = view;
  const selectedUnit = units.find((unit) => unit.id === selectedUnitId) || null;
  const selectedEntries = selectedUnit
    ? view.legal_actions.filter((entry) => entry.actor_id === selectedUnit.id)
    : [];

  const targetActions = new Map();
  selectedEntries.forEach((entry) => {
    if (entry.target_id && !targetActions.has(entry.target_id)) {
      targetActions.set(entry.target_id, entry);
    }
  });

  const destinationMarkers = new Map();
  selectedEntries.forEach((entry) => {
    if (!entry.action?.destination) return;
    const key = pointKey(entry.action.destination);
    if (!destinationMarkers.has(key)) {
      destinationMarkers.set(key, {
        position: entry.action.destination,
        entry,
      });
    }
  });

  const playerZones = zones?.player || [];
  const aiZones = zones?.ai || [];

  return (
    <div className="overflow-hidden rounded-2xl border border-stone-800 bg-stone-950 shadow-xl shadow-black/20">
      <div className="flex items-center justify-between gap-2 border-b border-stone-800 px-3 py-2">
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-stone-500">
          <span className="inline-flex h-2.5 w-2.5 rounded-full bg-sky-500" />
          {view.factions.player}
          <span className="text-stone-700">vs</span>
          <span className="inline-flex h-2.5 w-2.5 rounded-full bg-rose-500" />
          {view.factions.ai}
        </div>
        <span className="text-[11px] text-stone-500">
          {board.width}×{board.height} · inches
        </span>
      </div>

      <div className="bg-[#0c0a09] p-1.5 sm:p-2">
        <svg
          viewBox={`0 0 ${board.width} ${board.height}`}
          className="block h-auto w-full select-none rounded-lg"
          role="img"
          aria-label={`Battlefield with ${units.filter((unit) => unit.alive).length} units and ${objectives.length} objectives`}
        >
          <defs>
            <pattern
              id="aos4-grid"
              width="2"
              height="2"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 2 0 L 0 0 0 2"
                fill="none"
                stroke="#292524"
                strokeWidth="0.035"
              />
            </pattern>
            <radialGradient id="aos4-table" cx="50%" cy="45%" r="75%">
              <stop offset="0%" stopColor="#1c1917" />
              <stop offset="100%" stopColor="#0c0a09" />
            </radialGradient>
            <filter id="aos4-shadow" x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow
                dx="0"
                dy="0.16"
                stdDeviation="0.16"
                floodColor="#000000"
                floodOpacity="0.55"
              />
            </filter>
          </defs>

          <rect
            x="0"
            y="0"
            width={board.width}
            height={board.height}
            fill="url(#aos4-table)"
          />
          <rect
            x="0"
            y="0"
            width={board.width}
            height={board.height}
            fill="url(#aos4-grid)"
          />

          {playerZones.map((polygon, index) => (
            <polygon
              key={`player-zone-${index}`}
              points={polygon.map((point) => `${point.x},${point.y}`).join(" ")}
              fill="rgba(14,165,233,0.06)"
              stroke="rgba(56,189,248,0.22)"
              strokeWidth="0.12"
              strokeDasharray="0.7 0.45"
            />
          ))}
          {aiZones.map((polygon, index) => (
            <polygon
              key={`ai-zone-${index}`}
              points={polygon.map((point) => `${point.x},${point.y}`).join(" ")}
              fill="rgba(244,63,94,0.06)"
              stroke="rgba(251,113,133,0.22)"
              strokeWidth="0.12"
              strokeDasharray="0.7 0.45"
            />
          ))}

          {terrain.map((feature) => {
            const points = feature.points
              .map((point) => `${point.x},${point.y}`)
              .join(" ");
            const cx =
              feature.points.reduce((sum, point) => sum + point.x, 0) /
              feature.points.length;
            const cy =
              feature.points.reduce((sum, point) => sum + point.y, 0) /
              feature.points.length;
            return (
              <g key={feature.id}>
                <polygon
                  points={points}
                  fill={
                    feature.blocks_line_of_sight
                      ? "rgba(68,64,60,0.92)"
                      : "rgba(41,37,36,0.92)"
                  }
                  stroke={feature.cover ? "#78716c" : "#57534e"}
                  strokeWidth="0.12"
                  strokeDasharray={feature.cover ? "0" : "0.5 0.3"}
                />
                <polygon
                  points={points}
                  fill="none"
                  stroke="rgba(214,211,209,0.10)"
                  strokeWidth="0.3"
                />
                <text
                  x={cx}
                  y={cy}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="#a8a29e"
                  fontSize="0.62"
                  style={{ pointerEvents: "none" }}
                >
                  {feature.name}
                </text>
                <title>
                  {feature.name}
                  {feature.cover ? " · cover" : ""}
                  {feature.blocks_line_of_sight ? " · blocks line of sight" : ""}
                  {feature.difficult ? " · difficult ground" : ""}
                </title>
              </g>
            );
          })}

          {objectives.map((objective) => {
            const color = objectiveColor(objective.controller);
            return (
              <g key={objective.id}>
                <circle
                  cx={objective.position.x}
                  cy={objective.position.y}
                  r={objective.radius}
                  fill={color}
                  fillOpacity="0.09"
                  stroke={color}
                  strokeOpacity="0.85"
                  strokeWidth="0.12"
                  strokeDasharray="0.5 0.35"
                />
                <circle
                  cx={objective.position.x}
                  cy={objective.position.y}
                  r="0.55"
                  fill={color}
                  fillOpacity="0.9"
                  stroke="#e7e5e4"
                  strokeWidth="0.07"
                />
                <text
                  x={objective.position.x}
                  y={objective.position.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="#0c0a09"
                  fontSize="0.62"
                  fontWeight="700"
                  style={{ pointerEvents: "none" }}
                >
                  {objective.value}
                </text>
                <text
                  x={objective.position.x}
                  y={objective.position.y - 0.95}
                  textAnchor="middle"
                  fill="#d6d3d1"
                  fontSize="0.55"
                  style={{ pointerEvents: "none" }}
                >
                  {objective.name}
                </text>
                <title>
                  {objective.name}: {objective.value} VP ·{" "}
                  {objective.controller
                    ? `${objective.controller} controls`
                    : "uncontrolled"}
                </title>
              </g>
            );
          })}

          {Array.from(destinationMarkers.values()).map(({ position, entry }) => {
            const color = ACTION_COLORS[entry.group] || "#fbbf24";
            return (
              <g
                key={`dest-${pointKey(position)}`}
                onClick={() => !busy && onAction(entry)}
                style={{ cursor: busy ? "default" : "pointer" }}
              >
                <circle
                  cx={position.x}
                  cy={position.y}
                  r="0.5"
                  fill="#0c0a09"
                  stroke={color}
                  strokeWidth="0.14"
                />
                <circle
                  cx={position.x}
                  cy={position.y}
                  r="0.18"
                  fill={color}
                />
                <title>{`${entry.label}${entry.detail ? ` · ${entry.detail}` : ""}`}</title>
              </g>
            );
          })}

          {units
            .filter((unit) => unit.alive)
            .map((unit) => {
              const radius = tokenRadius(unit);
              const colors = SIDE_COLORS[unit.side] || SIDE_COLORS.ai;
              const selected = unit.id === selectedUnitId;
              const targetEntry = targetActions.get(unit.id);
              const targeted = Boolean(targetEntry);
              const tokenColor =
                unit.side === selectedUnit?.side
                  ? colors.fill
                  : SIDE_COLORS[unit.side]?.fill || colors.fill;
              const healthWidth = radius * 1.7;
              return (
                <g
                  key={unit.id}
                  onClick={() => {
                    if (busy) return;
                    if (unit.side === "player") {
                      onSelectUnit(unit.id);
                    } else if (targetEntry) {
                      onAction(targetEntry);
                    }
                  }}
                  style={{
                    cursor:
                      !busy && (unit.side === "player" || targeted)
                        ? "pointer"
                        : "default",
                  }}
                >
                  {selected && (
                    <circle
                      cx={unit.position.x}
                      cy={unit.position.y}
                      r={radius + 0.4}
                      fill="none"
                      stroke="#fef3c7"
                      strokeWidth="0.18"
                      strokeDasharray="0.42 0.26"
                    />
                  )}
                  {targeted && !selected && (
                    <circle
                      cx={unit.position.x}
                      cy={unit.position.y}
                      r={radius + 0.35}
                      fill="none"
                      stroke="#fbbf24"
                      strokeWidth="0.18"
                      strokeDasharray="0.35 0.22"
                    >
                      <animate
                        attributeName="stroke-opacity"
                        values="0.35;1;0.35"
                        dur="1.8s"
                        repeatCount="indefinite"
                      />
                    </circle>
                  )}
                  <circle
                    cx={unit.position.x}
                    cy={unit.position.y}
                    r={radius}
                    fill={tokenColor}
                    fillOpacity={unit.side === "player" ? 0.95 : 0.92}
                    stroke={selected ? "#fef3c7" : colors.stroke}
                    strokeWidth={selected ? 0.16 : 0.1}
                    filter="url(#aos4-shadow)"
                  />
                  <circle
                    cx={unit.position.x}
                    cy={unit.position.y}
                    r={radius * 0.58}
                    fill="rgba(12,10,9,0.35)"
                  />
                  <text
                    x={unit.position.x}
                    y={unit.position.y + 0.02}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="#fafaf9"
                    fontSize={Math.min(0.95, radius * 0.9)}
                    fontWeight="700"
                    style={{ pointerEvents: "none" }}
                  >
                    {unit.number}
                  </text>
                  <rect
                    x={unit.position.x - healthWidth / 2}
                    y={unit.position.y + radius + 0.18}
                    width={healthWidth}
                    height="0.24"
                    rx="0.1"
                    fill="rgba(12,10,9,0.8)"
                    stroke="rgba(250,250,249,0.2)"
                    strokeWidth="0.03"
                  />
                  <rect
                    x={unit.position.x - healthWidth / 2}
                    y={unit.position.y + radius + 0.18}
                    width={healthWidth * unit.health_ratio}
                    height="0.24"
                    rx="0.1"
                    fill={healthColor(unit.health_ratio)}
                  />
                  <title>
                    {unit.name} · {unit.wounds}/{unit.max_wounds} wounds ·{" "}
                    {unit.models} model{unit.models === 1 ? "" : "s"}
                    {targeted ? " · tap to attack" : ""}
                  </title>
                </g>
              );
            })}
        </svg>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-stone-800 px-3 py-2 text-[11px] text-stone-500">
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-sky-500" /> You
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-rose-500" /> AI
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full border border-amber-400" />
            Order target
          </span>
        </div>
        <span className="truncate">
          {selectedUnit
            ? `${selectedUnit.name} · ${selectedUnit.wounds}/${selectedUnit.max_wounds} wounds`
            : "Tap one of your units to issue an order"}
        </span>
      </div>
    </div>
  );
}
