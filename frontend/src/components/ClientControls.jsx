import React from "react";

export default function ClientControls({
  file,
  onFileChange,
  onUpload,
  onChoose,
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
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 mb-4">
      <input
        id="upload-file"
        type="file"
        onChange={onFileChange}
        style={{ display: "none" }}
      />
      <button
        id="choose-file"
        onClick={onChoose}
        className="btn-secondary w-full sm:w-auto"
      >
        {file ? file.name : "Choose file"}
      </button>
      <button
        id="create-run"
        onClick={onUpload}
        disabled={busy || !file}
        className="btn-primary w-full sm:w-auto"
      >
        Upload & Parse
      </button>

      <select
        id="battleplan-select"
        value={selectedBattleplan}
        onChange={(e) => setSelectedBattleplan(e.target.value)}
        className="w-full sm:w-auto"
      >
        <option value="">(random)</option>
        {battleplans &&
          battleplans.map((b) => (
            <option key={b.id} value={b.id}>
              {b.title}
            </option>
          ))}
      </select>

      <label htmlFor="roll-mode" className="text-sm">
        Roll mode:
      </label>
      <select
        id="roll-mode"
        value={rollMode}
        onChange={(e) => setRollMode(e.target.value)}
        className="w-full sm:w-auto"
      >
        <option value="ai">AI handles rolls</option>
        <option value="player">Player rolls (enter dice)</option>
      </select>

      <button
        id="run-ai-turn"
        onClick={onRunAiTurn}
        disabled={busy || (units && units.length === 0)}
        className="hidden sm:inline-flex btn-success w-full sm:w-auto"
      >
        Run AI Turn
      </button>
      {/* Mobile-only fixed bottom action for easy thumb reach */}
      <div
        className="sm:hidden fixed inset-x-0 bottom-0 p-3 z-20"
        style={{ pointerEvents: busy ? "none" : "auto" }}
      >
        <div className="mx-2">
          <button
            id="run-ai-turn-mobile"
            onClick={onRunAiTurn}
            disabled={busy || (units && units.length === 0)}
            className="btn-success w-full"
            style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
          >
            Run AI Turn (mobile)
          </button>
        </div>
      </div>
    </div>
  );
}
