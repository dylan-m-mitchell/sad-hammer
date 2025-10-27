import React from "react";

export default function Header() {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
      <div className="container-max py-4 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">Sadhammer</h1>
        <p className="text-slate-300 text-sm mt-1">
          Upload a BattleScribe HTML roster and run a simulated AI turn.
        </p>
      </div>
    </header>
  );
}
