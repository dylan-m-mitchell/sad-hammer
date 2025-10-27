import React from "react";

export default function Header({ sessionId }) {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
      <div className="container-max py-4">
        <h1 className="text-2xl font-semibold tracking-tight">
          Sad Hammer — Frontend
        </h1>
        <p className="text-slate-300 text-sm">
          Upload a BattleScribe HTML roster and run a simulated AI turn.
        </p>
        <div className="mt-2 text-xs text-slate-400">
          Session: <span id="session-id">{sessionId || "(none)"}</span>
        </div>
      </div>
    </header>
  );
}
