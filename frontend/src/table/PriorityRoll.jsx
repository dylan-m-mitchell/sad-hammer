import React from "react";
import { DOCTRINE_LABELS, unitsByDoctrine } from "./doctrine";

const DEPLOY_HINTS = [
  { doctrine: "press", text: "deploy forward, toward the closest enemy" },
  { doctrine: "support", text: "deploy in cover with a line of sight" },
  { doctrine: "hold", text: "deploy near an objective, beside a friend" },
];

export default function PriorityRoll({ aiRoster, onChoose }) {
  const groups = unitsByDoctrine(aiRoster);

  return (
    <section className="space-y-4">
      <div className="px-1">
        <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-amber-400/90">
          Step 2
        </p>
        <h2 className="mt-1 text-2xl font-semibold tracking-tight text-stone-50">
          Roll for the first turn
        </h2>
        <p className="mt-1 text-sm leading-6 text-stone-400">
          Set up the table and roll off. Tell the app who won — it will call the
          AI's turn when the AI reaches it.
        </p>
      </div>

      <article className="rounded-2xl border border-stone-800 bg-stone-900/70 p-4 shadow-xl shadow-black/20">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.25em] text-amber-400/90">
              Enemy army
            </p>
            <h3 className="truncate text-sm font-semibold text-stone-100">
              {aiRoster.name}
            </h3>
            <p className="text-xs text-stone-500">
              {aiRoster.units.length} units · deploy by doctrine
            </p>
          </div>
        </div>
        <ul className="mt-3 space-y-1 text-xs leading-5 text-stone-400">
          {DEPLOY_HINTS.filter(({ doctrine }) => groups[doctrine].length > 0).map(
            ({ doctrine, text }) => (
              <li key={doctrine}>
                <span className="font-semibold text-stone-200">
                  {DOCTRINE_LABELS[doctrine]}
                </span>{" "}
                ({groups[doctrine].length}) — {text}.
              </li>
            )
          )}
        </ul>
      </article>

      <div className="grid gap-2 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => onChoose("player")}
          className="rounded-xl bg-amber-500 px-4 py-4 text-sm font-semibold text-stone-950 transition hover:bg-amber-400"
        >
          I have the first turn
        </button>
        <button
          type="button"
          onClick={() => onChoose("ai")}
          className="rounded-xl border border-stone-700 bg-stone-900 px-4 py-4 text-sm font-semibold text-stone-100 transition hover:border-stone-500"
        >
          The AI has the first turn
        </button>
      </div>

      <p className="px-1 text-center text-[11px] leading-5 text-stone-500">
        Later rounds follow the same button: play your turn, then start the AI
        turn.
      </p>
    </section>
  );
}
