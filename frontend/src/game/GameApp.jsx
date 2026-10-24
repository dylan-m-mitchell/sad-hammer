import React, { useEffect, useRef, useState } from "react";
import SetupScreen from "./SetupScreen";
import GameScreen from "./GameScreen";
import {
  createGame,
  deleteGame,
  fetchOptions,
  importGame,
  resumeGame,
  submitAction,
} from "./api";

const STORAGE_KEY = "sadhammer.aos4.gameId";
let logCounter = 0;

function nextLogId(prefix) {
  logCounter += 1;
  return `${prefix}-${Date.now()}-${logCounter}`;
}

function eventToLog(event) {
  return {
    id: event.seq ? `event-${event.seq}` : nextLogId("event"),
    kind: event.kind,
    text: event.message,
    round: event.round,
    phase: event.phase,
    side: event.side,
  };
}

function initialBattleLog(snapshot, reason) {
  const entries = [
    {
      id: nextLogId("intro"),
      kind: "setup",
      text: reason,
      round: snapshot.view.round,
      phase: snapshot.view.phase,
      side: null,
    },
  ];
  (snapshot.state?.events || []).forEach((event) => {
    entries.push(eventToLog(event));
  });
  return entries;
}

function settingsFromSnapshot(snapshot) {
  const setup = snapshot?.view?.setup || {};
  return {
    mission: setup.mission,
    player_pack: setup.player_pack,
    ai_pack: setup.ai_pack,
    skip_deployment: setup.skip_deployment,
  };
}

export default function GameApp() {
  const [options, setOptions] = useState(null);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [game, setGame] = useState(null);
  const [savedGameId, setSavedGameId] = useState(() =>
    typeof window === "undefined" ? null : localStorage.getItem(STORAGE_KEY)
  );
  const [lastSettings, setLastSettings] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [battleLog, setBattleLog] = useState([]);
  const [aiDecisions, setAiDecisions] = useState([]);
  const autoResumeAttempted = useRef(false);

  useEffect(() => {
    let cancelled = false;
    fetchOptions()
      .then((data) => {
        if (!cancelled) setOptions(data);
      })
      .catch((err) => {
        if (!cancelled) setError(`Could not load game options: ${err.message}`);
      })
      .finally(() => {
        if (!cancelled) setOptionsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (autoResumeAttempted.current) return;
    autoResumeAttempted.current = true;
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return;
    // Do not cancel this request on effect cleanup. React StrictMode runs an
    // extra setup/cleanup cycle in development, and cancelling here would drop
    // the only resume attempt because ``autoResumeAttempted`` is already set.
    setBusy(true);
    resumeGame(stored)
      .then((snapshot) => {
        setGame(snapshot);
        setSavedGameId(snapshot.game_id);
        localStorage.setItem(STORAGE_KEY, snapshot.game_id);
        setLastSettings(settingsFromSnapshot(snapshot));
        setBattleLog(
          initialBattleLog(
            snapshot,
            `Resumed battle — round ${snapshot.view.round}, ${snapshot.view.phase_name}.`
          )
        );
        setAiDecisions(snapshot.ai_decisions || []);
      })
      .catch((err) => {
        if (err.status === 404) {
          localStorage.removeItem(STORAGE_KEY);
          setSavedGameId(null);
        }
        setError(`Could not resume the saved game: ${err.message}`);
      })
      .finally(() => {
        setBusy(false);
      });
  }, []);

  async function startGame(settings) {
    setBusy(true);
    setError(null);
    const previousId = game?.game_id;
    try {
      const snapshot = await createGame(settings);
      setGame(snapshot);
      setSavedGameId(snapshot.game_id);
      localStorage.setItem(STORAGE_KEY, snapshot.game_id);
      setLastSettings(settings);
      setAiDecisions([]);
      setBattleLog(
        initialBattleLog(
          snapshot,
          `${snapshot.view.factions.player} vs ${snapshot.view.factions.ai} — you take the first turn.`
        )
      );
      if (previousId && previousId !== snapshot.game_id) {
        deleteGame(previousId).catch(() => {});
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleAction(entry) {
    if (!game || busy) return;
    setBusy(true);
    setError(null);
    try {
      const snapshot = await submitAction(game.game_id, entry.action);
      const orderEntry = {
        id: nextLogId("order"),
        kind: "order",
        text: `${entry.actor_name ? `${entry.actor_name}: ` : ""}${
          entry.label
        }${entry.detail ? ` (${entry.detail})` : ""}`,
        round: snapshot.view.round,
        phase: snapshot.view.phase,
        side: "player",
      };
      setGame(snapshot);
      setBattleLog((previous) =>
        [
          ...previous,
          orderEntry,
          ...(snapshot.events || []).map((event) => eventToLog(event)),
        ].slice(-320)
      );
      if (snapshot.ai_decisions?.length) {
        setAiDecisions((previous) =>
          [...snapshot.ai_decisions, ...previous].slice(0, 24)
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleResume() {
    if (!savedGameId || busy) return;
    setBusy(true);
    setError(null);
    try {
      const snapshot = await resumeGame(savedGameId);
      setGame(snapshot);
      setSavedGameId(snapshot.game_id);
      localStorage.setItem(STORAGE_KEY, snapshot.game_id);
      setLastSettings(settingsFromSnapshot(snapshot));
      if (game) {
        setBattleLog((previous) =>
          [
            ...previous,
            ...(snapshot.events || []).map((event) => eventToLog(event)),
          ].slice(-320)
        );
        if (snapshot.ai_decisions?.length) {
          setAiDecisions((previous) =>
            [...snapshot.ai_decisions, ...previous].slice(0, 24)
          );
        }
      } else {
        setBattleLog(
          initialBattleLog(
            snapshot,
            `Resumed battle — round ${snapshot.view.round}, ${snapshot.view.phase_name}.`
          )
        );
        setAiDecisions(snapshot.ai_decisions || []);
      }
    } catch (err) {
      setError(err.message);
      if (err.status === 404) {
        localStorage.removeItem(STORAGE_KEY);
        setSavedGameId(null);
        setGame(null);
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleImport(file) {
    setBusy(true);
    setError(null);
    try {
      const text = await file.text();
      const saved = JSON.parse(text);
      const snapshot = await importGame(saved);
      setGame(snapshot);
      setSavedGameId(snapshot.game_id);
      localStorage.setItem(STORAGE_KEY, snapshot.game_id);
      setLastSettings(settingsFromSnapshot(snapshot));
      setAiDecisions(snapshot.ai_decisions || []);
      setBattleLog(
        initialBattleLog(
          snapshot,
          `Imported battle — round ${snapshot.view.round}, ${snapshot.view.phase_name}.`
        )
      );
    } catch (err) {
      setError(
        err instanceof SyntaxError
          ? "That file is not valid JSON."
          : err.message
      );
    } finally {
      setBusy(false);
    }
  }

  function handleNewGame() {
    if (game && game.view.status !== "complete") {
      const proceed = window.confirm(
        "Leave this battle and return to setup? Export the save first if you want to keep it."
      );
      if (!proceed) return;
    }
    if (game?.game_id) deleteGame(game.game_id).catch(() => {});
    localStorage.removeItem(STORAGE_KEY);
    setSavedGameId(null);
    setGame(null);
    setBattleLog([]);
    setAiDecisions([]);
    setError(null);
  }

  function handleDiscardSaved() {
    if (savedGameId) deleteGame(savedGameId).catch(() => {});
    localStorage.removeItem(STORAGE_KEY);
    setSavedGameId(null);
    setBattleLog([]);
    setAiDecisions([]);
  }

  function handleRematch() {
    const settings = lastSettings || settingsFromSnapshot(game);
    if (!settings?.mission) {
      handleNewGame();
      return;
    }
    startGame({
      mission: settings.mission,
      player_pack: settings.player_pack,
      ai_pack: settings.ai_pack,
      skip_deployment: settings.skip_deployment,
    });
  }

  function handleExport() {
    if (!game?.game_id || !game.state) return;
    const blob = new Blob([JSON.stringify(game.state, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${game.game_id}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  if (!game) {
    return (
      <SetupScreen
        options={options}
        loading={optionsLoading}
        error={error}
        busy={busy}
        savedGameId={savedGameId}
        initialSettings={lastSettings}
        onStart={startGame}
        onResume={handleResume}
        onImport={handleImport}
        onDiscardSaved={handleDiscardSaved}
      />
    );
  }

  return (
    <GameScreen
      game={game}
      busy={busy}
      error={error}
      battleLog={battleLog}
      aiDecisions={aiDecisions}
      onAction={handleAction}
      onResume={handleResume}
      onRefresh={handleResume}
      onNewGame={handleNewGame}
      onRematch={handleRematch}
      onExport={handleExport}
      onDismissError={() => setError(null)}
    />
  );
}
