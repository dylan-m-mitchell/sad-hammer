import React, { useEffect, useState } from "react";
import EnemySetup from "./EnemySetup";
import PriorityRoll from "./PriorityRoll";
import BattlePanel from "./BattlePanel";
import AiTurn from "./AiTurn";
import RosterBuilder from "./RosterBuilder";
import { fetchTablePlan, fetchTableRosters } from "./api";
import {
  PHASE_COUNT,
  TOTAL_ROUNDS,
  createSeed,
  createSession,
  loadRosters,
  loadSession,
  saveRosters,
  saveSession,
} from "./storage";

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
  const [starters, setStarters] = useState(null);
  const [session, setSession] = useState(() => loadSession() || createSession());
  const [plan, setPlan] = useState(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [planError, setPlanError] = useState(null);
  const [starterError, setStarterError] = useState(null);
  const [starterLoading, setStarterLoading] = useState(!rosters);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [startersRetry, setStartersRetry] = useState(0);
  const [planRetry, setPlanRetry] = useState(0);

  const stage = !session.enemyReady
    ? "setup"
    : session.firstTurn
    ? "battle"
    : "priority";

  useEffect(() => {
    saveSession(session);
  }, [session]);

  useEffect(() => {
    let cancelled = false;
    setStarterLoading(true);
    setStarterError(null);
    fetchTableRosters()
      .then((data) => {
        if (cancelled) return;
        const defaults = data.defaults || {};
        const player = data.rosters?.[defaults.player || "stormcast-starter"];
        const ai = data.rosters?.[defaults.ai || "skaven-starter"];
        if (!player || !ai) {
          throw new Error("the starter rosters were missing from the response.");
        }
        const next = { player, ai };
        setStarters(next);
        setRosters((previous) => {
          if (previous) return previous;
          saveRosters(next);
          return next;
        });
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
    if (stage !== "battle" || !rosters) return undefined;
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
    stage,
    rosters,
    session.round,
    session.seed,
    session.destroyed,
    planRetry,
  ]);

  function chooseEnemyArmy(aiRoster) {
    const next = { player: rosters.player, ai: aiRoster };
    setRosters(next);
    saveRosters(next);
    setPlan(null);
    setPlanError(null);
    setSession((previous) => ({
      ...previous,
      enemyReady: true,
      firstTurn: null,
      aiTurnDone: false,
      phaseIndex: null,
      round: 1,
      destroyed: [],
    }));
  }

  function handleSaveRosters(next) {
    setRosters(next);
    saveRosters(next);
    const aiIds = new Set(next.ai.units.map((unit) => unit.id));
    setSession((previous) => ({
      ...previous,
      destroyed: previous.destroyed.filter((id) => aiIds.has(id)),
      enemyReady: true,
      phaseIndex: null,
    }));
    setBuilderOpen(false);
  }

  function chooseFirstTurn(firstTurn) {
    setSession((previous) => ({ ...previous, firstTurn }));
  }

  function startAiTurn() {
    setSession((previous) => ({ ...previous, phaseIndex: 0 }));
  }

  function changePhase(delta) {
    setSession((previous) => {
      if (previous.phaseIndex === null) return previous;
      return {
        ...previous,
        phaseIndex: Math.min(
          PHASE_COUNT - 1,
          Math.max(0, previous.phaseIndex + delta)
        ),
      };
    });
  }

  function backToBattle() {
    setSession((previous) => ({ ...previous, phaseIndex: null }));
  }

  function finishAiTurn() {
    setSession((previous) => ({
      ...previous,
      phaseIndex: null,
      aiTurnDone: true,
    }));
  }

  function startNextRound() {
    setSession((previous) => ({
      ...previous,
      round: Math.min(TOTAL_ROUNDS, previous.round + 1),
      aiTurnDone: false,
      phaseIndex: null,
    }));
  }

  function startNewBattle() {
    setPlan(null);
    setPlanError(null);
    setSession((previous) => ({
      ...previous,
      seed: createSeed(),
      round: 1,
      destroyed: [],
      firstTurn: null,
      aiTurnDone: false,
      phaseIndex: null,
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

        {planError && session.phaseIndex === null && (
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
                ? "Loading the table companion…"
                : "The table companion needs its starter rosters to begin."}
            </p>
          </section>
        ) : builderOpen ? (
          <RosterBuilder
            rosters={rosters}
            initialSlot="ai"
            onSave={handleSaveRosters}
            onClose={() => setBuilderOpen(false)}
          />
        ) : stage === "setup" ? (
          <EnemySetup
            defaultRoster={starters?.ai}
            loading={starterLoading}
            onUseDefault={chooseEnemyArmy}
            onImport={chooseEnemyArmy}
            onOpenBuilder={() => setBuilderOpen(true)}
          />
        ) : stage === "priority" ? (
          <PriorityRoll aiRoster={rosters.ai} onChoose={chooseFirstTurn} />
        ) : session.phaseIndex !== null ? (
          <AiTurn
            plan={plan}
            loading={planLoading}
            error={planError}
            phaseIndex={session.phaseIndex}
            round={session.round}
            aiRoster={rosters.ai}
            destroyed={session.destroyed}
            onPhaseChange={changePhase}
            onFinish={finishAiTurn}
            onToggleDestroyed={toggleDestroyed}
            onBackToBattle={backToBattle}
            onRetry={() => setPlanRetry((value) => value + 1)}
          />
        ) : (
          <>
            <BattlePanel
              round={session.round}
              totalRounds={TOTAL_ROUNDS}
              aiRoster={rosters.ai}
              destroyed={session.destroyed}
              firstTurn={session.firstTurn}
              aiTurnDone={session.aiTurnDone}
              onStartAiTurn={startAiTurn}
              onStartNextRound={startNextRound}
              onNewBattle={startNewBattle}
              onToggleDestroyed={toggleDestroyed}
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
