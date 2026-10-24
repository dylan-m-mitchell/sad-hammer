import React from "react";

export default function AiIntentPanel({ decisions, busy }) {
  return (
    <section className="rounded-2xl border border-stone-800 bg-stone-900/80 shadow-xl shadow-black/20">
      <div className="flex items-center justify-between gap-2 border-b border-stone-800 px-3 py-2.5">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-stone-300">
            AI intent
          </h2>
          <p className="text-[11px] text-stone-500">
            Every AI choice comes with a reason.
          </p>
        </div>
        <span className="rounded-full border border-stone-700 bg-stone-950/60 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-stone-400">
          AI opponent
        </span>
      </div>

      <div className="max-h-56 space-y-2 overflow-y-auto p-3">
        {busy && (
          <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
            <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-amber-300" />
            The AI is choosing and resolving its actions…
          </div>
        )}
        {!busy && decisions.length === 0 && (
          <div className="rounded-lg border border-stone-800 bg-stone-950/40 px-3 py-3 text-xs leading-5 text-stone-500">
            The AI has not taken a visible action yet. Finish your turn to see
            its plan, target priorities and movement reasons.
          </div>
        )}
        {decisions.slice(0, 8).map((decision, index) => (
          <div
            key={`${decision.action.actor_id}-${decision.action.action_type}-${index}`}
            className="rounded-lg border border-stone-800 bg-stone-950/50 px-3 py-2"
          >
            <div className="min-w-0">
              <div className="truncate text-xs font-medium text-stone-200">
                {decision.label}
              </div>
              {decision.detail && (
                <div className="truncate text-[10px] text-stone-500">
                  {decision.detail}
                </div>
              )}
            </div>
            <p className="mt-1 text-[11px] leading-4 text-stone-400">
              {decision.reason}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
