import React from "react";

const GROUP_ORDER = [
  "deploy",
  "move",
  "run",
  "retreat",
  "shoot",
  "charge",
  "fight",
  "command",
];

const GROUP_HINTS = {
  deploy: "Choose a deployment position.",
  move: "A normal move cannot finish within 3\" of an enemy.",
  run: "Run for extra distance, but the unit cannot shoot or charge.",
  retreat: "Leave combat and suffer D3 mortal damage.",
  shoot: "Pick a visible target in range.",
  charge: "Roll 2D6. A successful charge strikes first in combat.",
  fight: "Alternating combat: pick a target in range.",
  command: "Spend 1 command point. One use per unit and per command each phase.",
};

function healthColor(ratio) {
  if (ratio > 0.66) return "bg-emerald-400";
  if (ratio > 0.33) return "bg-amber-400";
  return "bg-rose-400";
}

function phaseActionLabel(view, entry) {
  const phaseId = entry.action?.payload?.phase || view.phase;
  if (phaseId === "end_of_turn") return "End turn";
  if (phaseId === "start_of_turn") return "Continue to Hero phase";
  const phase = view.phases.find((item) => item.id === phaseId);
  return `End ${phase?.name || phaseId.replace(/_/g, " ")} phase`;
}

export default function OrdersPanel({
  view,
  selectedUnitId,
  onSelectUnit,
  onAction,
  busy,
}) {
  const playerUnits = view.units.filter((unit) => unit.side === "player");
  const actionsByActor = new Map();
  view.legal_actions.forEach((entry) => {
    if (!actionsByActor.has(entry.actor_id)) actionsByActor.set(entry.actor_id, []);
    actionsByActor.get(entry.actor_id).push(entry);
  });

  const selectedUnit =
    playerUnits.find((unit) => unit.id === selectedUnitId) || null;
  const selectedEntries = selectedUnit
    ? actionsByActor.get(selectedUnit.id) || []
    : [];
  const groups = new Map();
  selectedEntries.forEach((entry) => {
    if (!groups.has(entry.group)) groups.set(entry.group, []);
    groups.get(entry.group).push(entry);
  });
  const orderedGroups = GROUP_ORDER.filter((group) => groups.has(group));

  const endDeployment = view.legal_actions.find(
    (entry) => entry.action_type === "end_deployment"
  );
  const endPhase = view.legal_actions.find(
    (entry) => entry.action_type === "end_phase"
  );
  const otherActors = playerUnits.filter(
    (unit) => unit.id !== selectedUnitId && actionsByActor.has(unit.id)
  );

  return (
    <section className="rounded-2xl border border-stone-800 bg-stone-900/80 shadow-xl shadow-black/20">
      <div className="flex items-start justify-between gap-3 border-b border-stone-800 px-3 py-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-amber-400">
            Orders
          </h2>
          <p className="mt-1 text-xs leading-5 text-stone-400">
            {view.instruction}
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-stone-700 bg-stone-950 px-2.5 py-1 text-[11px] text-stone-300">
          {view.command_points.player} CP
        </span>
      </div>

      <div className="space-y-3 p-3">
        {(endDeployment || endPhase) && (
          <div className="grid gap-2">
            {endDeployment && (
              <button
                type="button"
                onClick={() => onAction(endDeployment)}
                disabled={busy}
                className="btn w-full bg-emerald-600 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-500"
              >
                Finish deployment
              </button>
            )}
            {endPhase && (
              <button
                type="button"
                onClick={() => onAction(endPhase)}
                disabled={busy}
                className="btn w-full border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm font-semibold text-amber-100 hover:bg-amber-500/20"
              >
                {phaseActionLabel(view, endPhase)}
                {view.phase === "end_of_turn" && (
                  <span className="ml-2 text-[11px] font-normal text-amber-200/70">
                    the AI will take its turn
                  </span>
                )}
              </button>
            )}
          </div>
        )}

        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-stone-500">
              Your units
            </h3>
            {otherActors.length > 0 && (
              <span className="text-[11px] text-stone-500">
                {otherActors.length} more with orders
              </span>
            )}
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {playerUnits.map((unit) => {
              const selected = unit.id === selectedUnitId;
              const hasOrders = actionsByActor.has(unit.id);
              return (
                <button
                  key={unit.id}
                  type="button"
                  onClick={() => onSelectUnit(unit.id)}
                  disabled={!unit.alive}
                  className={`min-w-[8.5rem] shrink-0 rounded-xl border px-2.5 py-2 text-left transition ${
                    selected
                      ? "border-sky-400/70 bg-sky-500/10"
                      : hasOrders
                      ? "border-stone-700 bg-stone-950/60 hover:border-stone-500"
                      : "border-stone-800 bg-stone-950/30 opacity-60"
                  } ${!unit.alive ? "line-through" : ""}`}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-sky-500 text-[10px] font-bold text-sky-950">
                      {unit.number}
                    </span>
                    <span className="truncate text-xs font-medium text-stone-200">
                      {unit.name}
                    </span>
                  </div>
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-stone-800">
                    <div
                      className={`h-full rounded-full ${healthColor(
                        unit.health_ratio
                      )}`}
                      style={{ width: `${Math.round(unit.health_ratio * 100)}%` }}
                    />
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[10px] text-stone-500">
                    <span>
                      {unit.wounds}/{unit.max_wounds} W
                    </span>
                    <span>{unit.models} models</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {selectedUnit && view.status !== "complete" && (
          <div className="rounded-xl border border-stone-800 bg-stone-950/40 p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-stone-100">
                  {selectedUnit.name}
                </h3>
                <div className="mt-1 flex flex-wrap gap-1">
                  {selectedUnit.status.length ? (
                    selectedUnit.status.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full bg-stone-800 px-2 py-0.5 text-[10px] text-stone-400"
                      >
                        {tag}
                      </span>
                    ))
                  ) : (
                    <span className="text-[11px] text-stone-500">
                      Ready for orders
                    </span>
                  )}
                </div>
              </div>
              <div className="flex gap-3 text-right text-[11px] text-stone-400">
                <span>
                  <strong className="block text-sm text-stone-100">
                    {selectedUnit.save}+
                  </strong>
                  Save
                </span>
                <span>
                  <strong className="block text-sm text-stone-100">
                    {selectedUnit.move}&quot;
                  </strong>
                  Move
                </span>
                <span>
                  <strong className="block text-sm text-stone-100">
                    {selectedUnit.control}
                  </strong>
                  Control
                </span>
              </div>
            </div>

            {selectedEntries.length === 0 ? (
              <p className="mt-3 rounded-lg border border-stone-800 bg-stone-900/60 px-3 py-2 text-xs text-stone-400">
                This unit has no orders left in the {view.phase_name} phase.
                {otherActors.length > 0
                  ? " Choose another unit or end the phase."
                  : " End the phase to continue."}
              </p>
            ) : (
              <div className="mt-3 space-y-3">
                {orderedGroups.map((group) => (
                  <div key={group}>
                    <div className="mb-1.5 flex items-center gap-2">
                      <h4 className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
                        {groups.get(group)[0].group_label}
                      </h4>
                      <span className="text-[10px] leading-4 text-stone-600">
                        {GROUP_HINTS[group]}
                      </span>
                    </div>
                    <div className="grid gap-1.5 sm:grid-cols-2">
                      {groups.get(group).map((entry) => (
                        <button
                          key={entry.id}
                          type="button"
                          onClick={() => onAction(entry)}
                          disabled={busy}
                          className={`group flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left transition disabled:opacity-50 ${
                            entry.action_type === "command"
                              ? "border-violet-500/30 bg-violet-500/5 hover:border-violet-400/60 hover:bg-violet-500/10"
                              : entry.action_type === "fight" ||
                                entry.action_type === "charge"
                              ? "border-rose-500/30 bg-rose-500/5 hover:border-rose-400/60 hover:bg-rose-500/10"
                              : "border-stone-700 bg-stone-900 hover:border-amber-500/50 hover:bg-stone-800"
                          }`}
                        >
                          <span className="min-w-0">
                            <span className="block truncate text-xs font-medium text-stone-100">
                              {entry.label}
                            </span>
                            {entry.detail && (
                              <span className="block truncate text-[10px] text-stone-500">
                                {entry.detail}
                              </span>
                            )}
                          </span>
                          {entry.cp_cost > 0 && (
                            <span className="shrink-0 rounded-full bg-violet-500/20 px-2 py-0.5 text-[10px] font-semibold text-violet-200">
                              {entry.cp_cost} CP
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {!selectedUnit && playerUnits.length > 0 && (
          <div className="rounded-xl border border-dashed border-stone-700 bg-stone-950/40 px-4 py-5 text-center">
            <p className="text-sm text-stone-300">
              Select a unit to see its orders.
            </p>
            <p className="mt-1 text-xs text-stone-500">
              You can tap a friendly token on the board or a unit chip above.
            </p>
          </div>
        )}

        {view.interaction === "player_combat_response" && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
            The AI is mid-turn. Alternating combat has reached your unit — pick
            a fight to keep the turn moving.
          </div>
        )}
      </div>
    </section>
  );
}
