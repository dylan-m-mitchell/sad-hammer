import React from "react";
import PhaseCard from "./PhaseCard";
import AiLossList from "./AiLossList";
import { PHASE_COUNT } from "./storage";

function StateCard({ children }) {
  return (
    <section className="rounded-2xl border border-stone-800 bg-stone-900/70 px-4 py-8 text-center shadow-xl shadow-black/20">
      {children}
    </section>
  );
}

export default function AiTurn({
  plan,
  loading,
  error,
  phaseIndex,
  round,
  aiRoster,
  destroyed,
  onPhaseChange,
  onFinish,
  onToggleDestroyed,
  onBackToBattle,
  onRetry,
}) {
  const ready = plan && plan.round === round;
  const phases = ready ? plan.phases : [];
  const phase = phases[phaseIndex];
  const isLast = phaseIndex >= PHASE_COUNT - 1;
  const nextPhase = phases[phaseIndex + 1];
  const wiped = ready && (plan.units || []).length === 0;

  return (
    <section className="space-y-3">
      <div className="rounded-2xl border border-stone-800 bg-stone-900/70 px-4 py-3 shadow-xl shadow-black/20">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.25em] text-amber-400/90">
              AI turn · Round {round}
            </p>
            <h2 className="truncate text-base font-semibold text-stone-100">
              Phase {phaseIndex + 1} of {PHASE_COUNT}
              {phase ? ` · ${phase.name}` : ""}
            </h2>
          </div>
          <button
            type="button"
            onClick={onBackToBattle}
            className="shrink-0 rounded-lg border border-stone-700 px-2.5 py-1 text-[11px] text-stone-400 transition hover:border-stone-500 hover:text-stone-200"
          >
            Back to battle
          </button>
        </div>
        <div className="mt-3 flex gap-1" aria-hidden="true">
          {Array.from({ length: PHASE_COUNT }).map((_, index) => (
            <span
              key={index}
              className={`h-1.5 flex-1 rounded-full ${
                index <= phaseIndex ? "bg-amber-500" : "bg-stone-800"
              }`}
            />
          ))}
        </div>
        <p className="mt-2 text-[11px] text-stone-500">
          Resolve this phase on the table, then continue.
        </p>
      </div>

      {wiped && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
          Every AI unit is destroyed. The table is yours this round — clear up
          and score.
        </div>
      )}

      {!phase ? (
        <StateCard>
          {error ? (
            <>
              <p className="text-sm text-stone-300">
                The AI plan could not be loaded: {error}
              </p>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                <button
                  type="button"
                  onClick={onBackToBattle}
                  className="rounded-lg border border-stone-700 px-3 py-2 text-xs text-stone-300 transition hover:border-stone-500"
                >
                  Back to battle
                </button>
                <button
                  type="button"
                  onClick={onRetry}
                  className="rounded-lg bg-amber-500 px-4 py-2 text-xs font-semibold text-stone-950 transition hover:bg-amber-400"
                >
                  Try again
                </button>
              </div>
            </>
          ) : (
            <p className="text-sm text-stone-400">
              {loading || !ready
                ? "Working out the AI's turn…"
                : "No instructions for this phase."}
            </p>
          )}
        </StateCard>
      ) : (
        <>
          <PhaseCard phase={phase} />

          {phase.id === "end" && (
            <div className="space-y-2">
              <AiLossList
                roster={aiRoster}
                destroyed={destroyed}
                onToggle={onToggleDestroyed}
                defaultOpen
              />
              <p className="px-1 text-[11px] leading-5 text-stone-500">
                Mark the AI units you destroyed. Next round&apos;s plan leaves
                them out.
              </p>
            </div>
          )}

          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => onPhaseChange(-1)}
              disabled={phaseIndex <= 0}
              className="rounded-xl border border-stone-700 bg-stone-900 px-4 py-3 text-sm text-stone-200 transition hover:border-stone-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Back
            </button>
            {isLast ? (
              <button
                type="button"
                onClick={onFinish}
                className="rounded-xl bg-amber-500 px-5 py-3 text-sm font-semibold text-stone-950 transition hover:bg-amber-400"
              >
                Finish AI turn
              </button>
            ) : (
              <button
                type="button"
                onClick={() => onPhaseChange(1)}
                className="rounded-xl bg-amber-500 px-5 py-3 text-sm font-semibold text-stone-950 transition hover:bg-amber-400"
              >
                {nextPhase ? `Continue to ${nextPhase.name}` : "Continue"}
              </button>
            )}
          </div>
        </>
      )}
    </section>
  );
}
