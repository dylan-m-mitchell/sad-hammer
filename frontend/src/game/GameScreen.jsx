import React, { useEffect, useMemo, useState } from "react";
import Board from "./Board";
import OrdersPanel from "./OrdersPanel";
import AiIntentPanel from "./AiIntentPanel";
import BattleLog from "./BattleLog";

const SIDE_LABEL = { player: "You", ai: "AI" };

function scoreTone(view) {
  if (view.status === "complete") {
    if (view.result === "Victory") return "text-emerald-300";
    if (view.result === "Defeat") return "text-rose-300";
    return "text-amber-200";
  }
  return "text-stone-100";
}

function ResultOverlay({ view, onClose, onRematch, onNewGame, onExport }) {
  const tone =
    view.result === "Victory"
      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-100"
      : view.result === "Defeat"
      ? "border-rose-500/40 bg-rose-500/10 text-rose-100"
      : "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-3 backdrop-blur-sm sm:items-center">
      <div className="w-full max-w-md rounded-2xl border border-stone-700 bg-stone-900 p-5 shadow-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-stone-500">
          Battle complete
        </p>
        <div className={`mt-3 rounded-xl border px-4 py-5 text-center ${tone}`}>
          <div className="text-3xl font-semibold tracking-tight">
            {view.result}
          </div>
          <div className="mt-1 text-sm opacity-80">
            {view.factions.player} {view.scores.player} — {view.scores.ai}{" "}
            {view.factions.ai}
          </div>
        </div>
        <p className="mt-3 text-center text-xs leading-5 text-stone-400">
          {view.result === "Victory"
            ? "The objective markers are yours. The AI's intent log shows where it went wrong."
            : view.result === "Defeat"
            ? "The AI out-scored you this time. Try a different style or review the intent log."
            : "The battle ended level. Change your opening or pick a more aggressive AI."}
        </p>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={onRematch}
            className="btn bg-amber-500 px-4 py-2.5 text-sm font-semibold text-stone-950 hover:bg-amber-400"
          >
            Rematch
          </button>
          <button
            type="button"
            onClick={onNewGame}
            className="btn border border-stone-700 bg-stone-900 px-4 py-2.5 text-sm text-stone-200 hover:border-stone-500"
          >
            New battle
          </button>
          <button
            type="button"
            onClick={onExport}
            className="btn border border-stone-700 bg-stone-900 px-4 py-2.5 text-sm text-stone-200 hover:border-stone-500"
          >
            Export save
          </button>
          <button
            type="button"
            onClick={onClose}
            className="btn border border-stone-800 bg-stone-950 px-4 py-2.5 text-sm text-stone-400 hover:text-stone-200"
          >
            Review board
          </button>
        </div>
      </div>
    </div>
  );
}

export default function GameScreen({
  game,
  busy,
  error,
  battleLog,
  aiDecisions,
  onAction,
  onResume,
  onRefresh,
  onNewGame,
  onRematch,
  onExport,
  onDismissError,
}) {
  const view = game.view;
  const [selectedUnitId, setSelectedUnitId] = useState(null);
  const [resultDismissed, setResultDismissed] = useState(false);

  const playerUnits = useMemo(
    () => view.units.filter((unit) => unit.side === "player"),
    [view.units]
  );
  const actorIds = useMemo(
    () => new Set(view.legal_actions.map((entry) => entry.actor_id)),
    [view.legal_actions]
  );

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [game.game_id]);

  useEffect(() => {
    if (view.status !== "complete") setResultDismissed(false);
  }, [game.game_id, view.status]);

  useEffect(() => {
    const withOrders = playerUnits.filter((unit) => actorIds.has(unit.id));
    if (
      !selectedUnitId ||
      !actorIds.has(selectedUnitId) ||
      !playerUnits.some((unit) => unit.id === selectedUnitId)
    ) {
      const next =
        withOrders.find((unit) => unit.alive) ||
        playerUnits.find((unit) => unit.alive) ||
        null;
      setSelectedUnitId(next ? next.id : null);
    }
  }, [actorIds, playerUnits, selectedUnitId]);

  const turnTone =
    view.interaction === "player_combat_response"
      ? "border-amber-500/40 bg-amber-500/10 text-amber-100"
      : view.active_side === "player"
      ? "border-sky-500/40 bg-sky-500/10 text-sky-100"
      : "border-rose-500/40 bg-rose-500/10 text-rose-100";

  const phaseIndex = view.phases.findIndex((phase) => phase.current);

  return (
    <div className="min-h-screen bg-stone-950 pb-10 text-stone-100">
      <header className="sticky top-0 z-30 border-b border-stone-800 bg-stone-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-2 px-3 py-2.5 sm:px-5">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-[0.28em] text-amber-400">
                Sad Hammer
              </span>
              <span className="hidden rounded-full border border-stone-700 px-2 py-0.5 text-[10px] text-stone-400 sm:inline">
                {view.system} · {view.edition}
              </span>
            </div>
            <div className="truncate text-xs text-stone-400">
              {view.mission.name} · Round {Math.min(view.round, view.max_rounds)}{" "}
              of {view.max_rounds}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              onClick={onExport}
              disabled={busy}
              className="rounded-md border border-stone-700 px-2.5 py-2 text-[11px] text-stone-300 transition hover:border-stone-500 hover:text-white sm:px-3 sm:text-xs"
            >
              Export
            </button>
            <button
              type="button"
              onClick={onNewGame}
              disabled={busy}
              className="rounded-md border border-stone-700 px-2.5 py-2 text-[11px] text-stone-300 transition hover:border-stone-500 hover:text-white sm:px-3 sm:text-xs"
            >
              New battle
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-3 px-3 py-3 sm:space-y-4 sm:px-5">
        {error && (
          <div
            role="alert"
            className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-2.5 text-xs text-rose-100"
          >
            <span className="min-w-0 flex-1">{error}</span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onRefresh}
                className="rounded border border-rose-400/40 px-2 py-1 hover:bg-rose-500/10"
              >
                Sync game
              </button>
              <button
                type="button"
                onClick={onDismissError}
                className="rounded px-2 py-1 text-rose-200/70 hover:text-white"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        <section className="overflow-hidden rounded-2xl border border-stone-800 bg-stone-900/80 shadow-xl shadow-black/20">
          <div className="grid grid-cols-2 divide-x divide-stone-800 sm:grid-cols-4">
            <div className="px-3 py-2.5">
              <div className="text-[10px] font-semibold uppercase tracking-wide text-stone-500">
                Your VP
              </div>
              <div className={`text-2xl font-semibold ${scoreTone(view)}`}>
                {view.scores.player}
              </div>
              <div className="truncate text-[10px] text-stone-500">
                {view.factions.player}
              </div>
            </div>
            <div className="px-3 py-2.5">
              <div className="text-[10px] font-semibold uppercase tracking-wide text-stone-500">
                AI VP
              </div>
              <div className="text-2xl font-semibold text-stone-100">
                {view.scores.ai}
              </div>
              <div className="truncate text-[10px] text-stone-500">
                {view.factions.ai}
              </div>
            </div>
            <div className="px-3 py-2.5">
              <div className="text-[10px] font-semibold uppercase tracking-wide text-stone-500">
                Command points
              </div>
              <div className="mt-1 flex items-center gap-3 text-sm">
                <span className="text-sky-300">
                  <strong className="text-xl">{view.command_points.player}</strong>{" "}
                  you
                </span>
                <span className="text-rose-300">
                  <strong className="text-xl">{view.command_points.ai}</strong> AI
                </span>
              </div>
            </div>
            <div className="px-3 py-2.5">
              <div className="text-[10px] font-semibold uppercase tracking-wide text-stone-500">
                Objectives
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {view.objectives.map((objective) => (
                  <span
                    key={objective.id}
                    title={`${objective.name}: ${
                      objective.controller
                        ? `${objective.controller} controls`
                        : "uncontrolled"
                    }`}
                    className={`h-2.5 w-2.5 rounded-full ${
                      objective.controller === "player"
                        ? "bg-sky-400"
                        : objective.controller === "ai"
                        ? "bg-rose-400"
                        : "border border-stone-500 bg-transparent"
                    }`}
                  />
                ))}
                <span className="ml-1 text-[10px] text-stone-500">
                  {view.objectives.filter((item) => item.controller === "player").length}
                  –{view.objectives.filter((item) => item.controller === "ai").length}
                </span>
              </div>
            </div>
          </div>

          <div className="border-t border-stone-800 px-3 py-2.5">
            <div className={`rounded-xl border px-3 py-2 ${turnTone}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide">
                    {view.turn_label}
                  </div>
                  <div className="text-[11px] opacity-80">
                    {view.status === "complete"
                      ? `Final score ${view.scores.player}–${view.scores.ai}.`
                      : view.interaction === "player_combat_response"
                      ? "Alternating combat has reached your army."
                      : `${view.phase_name} phase · ${
                          SIDE_LABEL[view.active_side]
                        } active`}
                  </div>
                </div>
                {view.interaction === "ai" && !busy && (
                  <button
                    type="button"
                    onClick={onResume}
                    className="rounded border border-current/30 px-2.5 py-1 text-[11px] font-semibold hover:bg-white/10"
                  >
                    Resume AI turn
                  </button>
                )}
                {!busy &&
                  view.legal_actions.length === 0 &&
                  view.status !== "complete" && (
                    <button
                      type="button"
                      onClick={onResume}
                      className="rounded border border-current/30 px-2.5 py-1 text-[11px] font-semibold hover:bg-white/10"
                    >
                      Continue
                    </button>
                  )}
              </div>
            </div>

            <div className="mt-2 flex gap-1 overflow-x-auto pb-1">
              {view.phases.map((phase, index) => {
                const complete = phaseIndex >= 0 && index < phaseIndex;
                return (
                  <div
                    key={phase.id}
                    title={phase.description}
                    className={`flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-1 text-[10px] ${
                      phase.current
                        ? "border-amber-400/60 bg-amber-400/15 text-amber-100"
                        : complete
                        ? "border-stone-700 bg-stone-800/60 text-stone-400"
                        : "border-stone-800 text-stone-600"
                    }`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        phase.current
                          ? "bg-amber-300"
                          : complete
                          ? "bg-stone-500"
                          : "bg-stone-700"
                      }`}
                    />
                    {phase.name}
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1.6fr)_minmax(320px,1fr)] lg:items-start">
          <div className="min-w-0 space-y-3">
            <Board
              view={view}
              selectedUnitId={selectedUnitId}
              onSelectUnit={setSelectedUnitId}
              onAction={onAction}
              busy={busy}
            />
            <div className="rounded-xl border border-stone-800 bg-stone-900/60 px-3 py-2 text-[11px] leading-5 text-stone-500">
              Tip: tap a highlighted destination token to issue that move, or
              tap a pulsing enemy to attack it. Every order is also listed in
              the panel.
            </div>
          </div>

          <div className="min-w-0 space-y-3">
            <OrdersPanel
              view={view}
              selectedUnitId={selectedUnitId}
              onSelectUnit={setSelectedUnitId}
              onAction={onAction}
              busy={busy}
            />
            <AiIntentPanel
              view={view}
              decisions={aiDecisions}
              busy={busy}
            />
            <BattleLog entries={battleLog} />
          </div>
        </div>
      </main>

      {view.status === "complete" && !resultDismissed && (
        <ResultOverlay
          view={view}
          onClose={() => setResultDismissed(true)}
          onRematch={onRematch}
          onNewGame={onNewGame}
          onExport={onExport}
        />
      )}

      {busy && (
        <div className="fixed inset-0 z-40 flex items-end justify-center bg-black/55 p-4 backdrop-blur-[2px] sm:items-center">
          <div className="flex w-full max-w-sm items-center gap-3 rounded-2xl border border-stone-700 bg-stone-900 px-4 py-4 shadow-2xl">
            <span className="flex h-10 w-10 shrink-0 animate-spin items-center justify-center rounded-full border-2 border-amber-400 border-t-transparent text-lg">
              ⚔
            </span>
            <div>
              <div className="text-sm font-semibold text-stone-100">
                Resolving orders…
              </div>
              <div className="text-xs text-stone-400">
                The AI is choosing actions and rolling dice.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
