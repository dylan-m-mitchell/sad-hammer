import React from "react";
import UiSelect from "./UiSelect";
import UiButton from "./UiButton";

export default function SessionControls({
  file,
  onFileChange,
  onUpload,
  battleplans,
  selectedBattleplan,
  setSelectedBattleplan,
  rollMode,
  setRollMode,
  onRunAiTurn,
  units,
  busy,
}) {
  return (
    <section className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
      <label className="inline-flex items-center gap-3">
        <input
          id="roster-file"
          aria-label="Roster HTML"
          type="file"
          accept=".html,.htm,text/html"
          className="input"
          onChange={onFileChange}
        />
      </label>
      <div className="flex items-center gap-2">
        <label htmlFor="battleplan-select" className="text-sm text-slate-300">
          Battleplan:
        </label>
        <UiSelect
          id="battleplan-select"
          value={selectedBattleplan}
          onChange={(e) => setSelectedBattleplan(e.target.value)}
        >
          <option value="">Random</option>
          {battleplans.map((bp) => (
            <option key={bp.id} value={bp.id}>
              {bp.title}
            </option>
          ))}
        </UiSelect>
      </div>
      <div className="flex items-center gap-2">
        <label htmlFor="roll-mode" className="text-sm text-slate-300">
          Roll mode:
        </label>
        <UiSelect
          id="roll-mode"
          value={rollMode}
          onChange={(e) => setRollMode(e.target.value)}
        >
          <option value="ai">AI handles rolls</option>
          <option value="player">Player rolls (enter dice)</option>
        </UiSelect>
      </div>
      <div className="flex gap-2">
        <UiButton
          id="create-session"
          onClick={onUpload}
          disabled={busy || !file}
          className="btn-primary"
        >
          Upload & Parse
        </UiButton>
        <UiButton
          id="run-ai-turn"
          onClick={onRunAiTurn}
          disabled={busy || units.length === 0}
          className="btn-success"
        >
          Run AI Turn
        </UiButton>
      </div>
    </section>
  );
}
