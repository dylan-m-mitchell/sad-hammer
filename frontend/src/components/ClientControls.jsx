import React from "react";

export default function ClientControls({
  file,
  onFileChange,
  onUpload,
  openUploadModal,
  setOpenUploadModal,
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
      <button
        id="upload-roster"
        onClick={() => setOpenUploadModal(true)}
        className="btn-primary w-full sm:w-auto"
        disabled={busy}
      >
        Upload Roster
      </button>
      {/* Legacy upload controls removed — use Upload Roster modal instead. */}

      {/* Battleplan and roll-mode are selected in the Upload modal; remove legacy dropdowns */}

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
