import React from "react";
import PhaseCard from "./PhaseCard";

export default function TurnView({ plan, loading, error, round }) {
  if (!plan) {
    return (
      <section className="rounded-2xl border border-stone-800 bg-stone-900/70 px-4 py-6 text-center shadow-xl shadow-black/20">
        {loading ? (
          <p className="text-sm text-stone-400">Working out the AI's round…</p>
        ) : (
          <p className="text-sm text-stone-400">
            {error
              ? "The plan could not be loaded. Check the message above."
              : "No plan for this round yet."}
          </p>
        )}
      </section>
    );
  }

  const wiped = (plan.units || []).length === 0;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2 px-1">
        <div>
          <h2 className="text-base font-semibold text-stone-100">
            AI plan · Round {plan.round}
          </h2>
          <p className="text-xs text-stone-500">
            {plan.ai_roster.name} · {plan.ai_roster.active_count} of{" "}
            {plan.ai_roster.unit_count} units active
          </p>
        </div>
        <p className="text-[11px] text-stone-500">
          {loading ? "Updating…" : "Measure, move and roll on your table."}
        </p>
      </div>

      {wiped && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
          Every AI unit is destroyed. The table is yours this round — clear up
          and score.
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-2">
        {(plan.phases || []).map((phase) => (
          <PhaseCard key={phase.id} phase={phase} />
        ))}
      </div>

      {round !== plan.round && (
        <p className="px-1 text-[11px] text-stone-500">
          Showing the plan for round {plan.round}.
        </p>
      )}
    </section>
  );
}
