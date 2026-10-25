import React, { useEffect, useState } from "react";
import SetupChecklist from "./SetupChecklist";
import AiRosterPanel from "./AiRosterPanel";
import TurnView from "./TurnView";
import RosterBuilder from "./RosterBuilder";
import { fetchTablePlan, fetchTableRosters } from "./api";
import {
  TOTAL_ROUNDS,
  createSeed,
  loadRosters,
  loadSession,
  saveRosters,
  saveSession,
} from "./storage";

const EMPTY_CHECKLIST = {
  objectives: false,
  terrain: false,
  playerDeploy: false,
  aiDeploy: false,
};

function Header() {
  return (
    <header className="border-b border-stone-800/80 bg-stone-950/90">
      <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-3 px-4 py-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.35em] text-amber-400/90">
            Sad Hammer
          </p>
          <h1 className="truncate text-lg font-semibold tracking-tight text-stone-50">
            Table companion
          </h1>
          <p className="truncate text-[11px] text-stone-500">
            Age of Sigmar 4th · you measure, move and roll for real
          </p>
        </div>
        <a
          href="/digital"
          className="shrink-0 rounded-lg border border-stone-700 bg-stone-900 px-3 py-2 text-[11px] font-medium text-stone-300 transition hover:border-stone-500 hover:text-stone-100"
        >
          Digital board
        </a>
      </div>
    </header>
  );
}

function ErrorBanner({ children, action, onAction }) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-xs text-rose-100"
    >
      <span>{children}</span>
      {action && (
        <button
          type="button"
          onClick={onAction}
          className="rounded-lg border border-rose-400/40 px-2.5 py-1 text-[11px] text-rose-100 transition hover:bg-rose-500/20"
        >
          {action}
        </button>
      )}
    </div>
  );
}

export default function TableApp() {
  const [rosters, setRosters] = useState(() => loadRosters());
  const [session, setSession] = useState(
    () =>
      loadSession() || {
        seed: createSeed(),
        round: 1,
        destroyed: [],
        checklist: EMPTY_CHECKLIST,
      }
  );
  const [plan, setPlan] = useState(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [planError, setPlanError] = useState(null);
  const [starterError, setStarterError] = useState(null);
  const [starterLoading, setStarterLoading] = useState(!rosters);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [startersRetry, setStartersRetry] = useState(0);
  const [planRetry, setPlanRetry] = useState(0);

  useEffect(() => {
    saveSession(session);
  }, [session]);

  useEffect(() => {
    if (rosters) return undefined;
    let cancelled = false;
    setStarterLoading(true);
    setStarterError(null);
    fetchTableRosters()
      .then((data) => {
        if (cancelled) return;
        const defaults = data.defaults || {};
        const player =
          data.rosters?.[defaults.player || "stormcast-starter"];
        const ai = data.rosters?.[defaults.ai || "skaven-starter"];
        if (!player || !ai) {
          throw new Error("the starter rosters were missing from the response.");
        }
        const next = { player, ai };
        setRosters(next);
        saveRosters(next);
        const aiIds = new Set(ai.units.map((unit) => unit.id));
        setSession((previous) => ({
          ...previous,
          destroyed: previous.destroyed.filter((id) => aiIds.has(id)),
        }));
      })
      .catch((error) => {
        if (!cancelled) setStarterError(error.message);
      })
      .finally(() => {
        if (!cancelled) setStarterLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [startersRetry]);

  useEffect(() => {
    if (!rosters) return undefined;
    const controller = new AbortController();
    setPlanLoading(true);
    setPlanError(null);
    fetchTablePlan(
      {
        playerRoster: rosters.player,
        aiRoster: rosters.ai,
        round: session.round,
        seed: session.seed,
        destroyed: session.destroyed,
      },
      controller.signal
    )
      .then((data) => {
        if (!controller.signal.aborted) setPlan(data);
      })
      .catch((error) => {
        if (error.name === "AbortError" || controller.signal.aborted) return;
        setPlan(null);
        setPlanError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setPlanLoading(false);
      });
    return () => controller.abort();
  }, [
    rosters,
    session.round,
    session.seed,
    session.destroyed,
    planRetry,
  ]);

  function changeRound(delta) {
    setSession((previous) => ({
      ...previous,
      round: Math.min(
        TOTAL_ROUNDS,
        Math.max(1, previous.round + delta)
      ),
    }));
  }

  function toggleDestroyed(unitId) {
    setSession((previous) => ({
      ...previous,
      destroyed: previous.destroyed.includes(unitId)
        ? previous.destroyed.filter((id) => id !== unitId)
        : [...previous.destroyed, unitId],
    }));
  }

  function toggleChecklist(key) {
    setSession((previous) => ({
      ...previous,
      checklist: {
        ...previous.checklist,
        [key]: !previous.checklist[key],
      },
    }));
  }

  function handleSaveRosters(next) {
    setRosters(next);
    saveRosters(next);
    const aiIds = new Set(next.ai.units.map((unit) => unit.id));
    setSession((previous) => ({
      ...previous,
      destroyed: previous.destroyed.filter((id) => aiIds.has(id)),
    }));
    setBuilderOpen(false);
  }

  return (
    <div className="min-h-screen bg-stone-950 pb-10 text-stone-100 antialiased">
      <Header />

      <main className="mx-auto w-full max-w-3xl space-y-4 px-4 py-5">
        {starterError && (
          <ErrorBanner
            action="Try again"
            onAction={() => setStartersRetry((value) => value + 1)}
          >
            Could not load the starter rosters: {starterError}
          </ErrorBanner>
        )}

        {planError && (
          <ErrorBanner
            action="Retry"
            onAction={() => setPlanRetry((value) => value + 1)}
          >
            Could not generate the AI plan: {planError}
          </ErrorBanner>
        )}

        {!rosters ? (
          <section className="rounded-2xl border border-stone-800 bg-stone-900/70 px-4 py-8 text-center">
            <p className="text-sm text-stone-400">
              {starterLoading
                ? "Loading the starter rosters…"
                : "The table companion needs its starter rosters to begin."}
            </p>
          </section>
        ) : builderOpen ? (
          <RosterBuilder
            rosters={rosters}
            onSave={handleSaveRosters}
            onClose={() => setBuilderOpen(false)}
          />
        ) : (
          <>
            <SetupChecklist
              checklist={session.checklist}
              aiRoster={rosters.ai}
              onToggle={toggleChecklist}
            />
            <AiRosterPanel
              roster={rosters.ai}
              round={session.round}
              destroyed={session.destroyed}
              onRoundChange={changeRound}
              onToggleDestroyed={toggleDestroyed}
              onOpenBuilder={() => setBuilderOpen(true)}
            />
            <TurnView
              plan={plan}
              loading={planLoading}
              error={planError}
              round={session.round}
            />
            <footer className="space-y-1 px-1 pt-1 text-center text-[11px] leading-5 text-stone-600">
              <p>
                No board, no coordinates, no dice roller — you measure, move and
                roll on your own table.
              </p>
              <p>
                Same round and seed always produce the same plan; the maneuver
                rotates each round.
              </p>
            </footer>
          </>
        )}
      </main>
    </div>
  );
}
