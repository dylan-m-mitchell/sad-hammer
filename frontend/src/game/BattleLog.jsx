import React, { useEffect, useRef } from "react";

const SIDE_STYLES = {
  player: "bg-sky-400",
  ai: "bg-rose-400",
};

function eventTone(kind) {
  if (kind === "game_complete") return "text-amber-200";
  if (kind === "unit_destroyed") return "text-rose-300";
  if (kind === "objective_scored" || kind === "objective_controlled")
    return "text-amber-300";
  if (kind === "command_used" || kind === "rally_resolved")
    return "text-violet-300";
  if (kind === "charge_succeeded" || kind === "attack_resolved")
    return "text-stone-200";
  return "text-stone-400";
}

export default function BattleLog({ entries }) {
  const scrollRef = useRef(null);
  const visible = entries
    .filter((entry) => entry.kind !== "objective_checked")
    .slice(-100);

  useEffect(() => {
    const node = scrollRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [entries.length]);

  return (
    <section className="rounded-2xl border border-stone-800 bg-stone-900/80 shadow-xl shadow-black/20">
      <div className="flex items-center justify-between border-b border-stone-800 px-3 py-2.5">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-stone-300">
            Battle log
          </h2>
          <p className="text-[11px] text-stone-500">
            Dice, damage, objectives and phase changes.
          </p>
        </div>
        <span className="rounded-full bg-stone-950 px-2 py-1 text-[10px] text-stone-500">
          {visible.length} entries
        </span>
      </div>
      <div
        ref={scrollRef}
        className="max-h-72 space-y-1 overflow-y-auto px-3 py-2.5"
      >
        {visible.length === 0 && (
          <p className="py-4 text-center text-xs text-stone-500">
            The battle log will fill as orders are resolved.
          </p>
        )}
        {visible.map((entry) => (
          <div
            key={entry.id}
            className="flex items-start gap-2 rounded px-1 py-1 hover:bg-stone-950/50"
          >
            <span
              className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                SIDE_STYLES[entry.side] || "bg-stone-600"
              }`}
            />
            <div className="min-w-0">
              <div className="flex flex-wrap items-baseline gap-x-1.5">
                {entry.round > 0 && (
                  <span className="text-[9px] font-medium uppercase tracking-wide text-stone-600">
                    R{entry.round}
                  </span>
                )}
                <p
                  className={`text-[11px] leading-4 ${eventTone(entry.kind)}`}
                >
                  {entry.text}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
