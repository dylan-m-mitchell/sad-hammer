import React from "react";
import AiLossList from "./AiLossList";

export default function BattlePanel({
  round,
  totalRounds,
  aiRoster,
  destroyed,
  firstTurn,
  aiTurnDone,
  onStartAiTurn,
  onStartNextRound,
  onNewBattle,
  onToggleDestroyed,
}) {
  const destroyedSet = new Set(destroyed);
  const activeCount = aiRoster.units.filter(
    (unit) => !destroyedSet.has(unit.id)
  ).length;
  const complete = aiTurnDone && round >= totalRounds;
  const status = complete
    ? "Battle complete"
    : aiTurnDone
    ? "AI turn complete"
    : firstTurn === "ai" && round === 1
    ? "The AI has the first turn"
    : "Your turn";

  const hint = complete
    ? "Pack up, or start again with the same armies."
    : aiTurnDone
    ? "Finish the battle round on the table, then start the next round."
    : firstTurn === "ai" && round === 1
    ? "When the table is ready, start the AI turn. It walks through one phase at a time."
    : "Play your turn on the table, then start the AI turn. It walks through one phase at a time.";

  return (
    <section className="space-y-3">
      <article className="rounded-2xl border border-stone-800 bg-stone-900/70 p-4 shadow-xl shadow-black/20">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.25em] text-amber-400/90">
              Battle round
            </p>
            <h2 className="mt-0.5 text-2xl font-semibold tracking-tight text-stone-50">
              Round {round}
              <span className="text-sm font-normal text-stone-500">
                {" "}
                of {totalRounds}
              </span>
            </h2>
          </div>
          <span className="shrink-0 rounded-full border border-stone-700 bg-stone-950/60 px-3 py-1 text-[11px] text-stone-300">
            {status}
          </span>
        </div>

        <p className="mt-3 text-xs leading-5 text-stone-400">{hint}</p>

        <button
          type="button"
          onClick={complete ? onNewBattle : aiTurnDone ? onStartNextRound : onStartAiTurn}
          className="mt-4 w-full rounded-xl bg-amber-500 px-4 py-4 text-sm font-semibold text-stone-950 transition hover:bg-amber-400"
        >
          {complete
            ? "Start a new battle"
            : aiTurnDone
            ? `Start round ${round + 1}`
            : "Start the AI turn"}
        </button>

        <div className="mt-4 flex items-center justify-between gap-3 border-t border-stone-800 pt-3 text-xs">
          <span className="truncate text-stone-400">
            AI army · <span className="text-stone-200">{aiRoster.name}</span>
          </span>
          <span className="shrink-0 text-stone-500">
            {activeCount} of {aiRoster.units.length} active
          </span>
        </div>
      </article>

      <AiLossList
        roster={aiRoster}
        destroyed={destroyed}
        onToggle={onToggleDestroyed}
      />
    </section>
  );
}
