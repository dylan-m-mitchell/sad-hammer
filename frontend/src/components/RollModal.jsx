import React, { useEffect, useRef } from "react";
import Modal from "./Modal";

export default function RollModal({
  open,
  pausedActions,
  rollInputs,
  rollValidationErrors,
  onChangeInput,
  onCancel,
  onSubmit,
  disableSubmit,
}) {
  const firstRef = useRef(null);
  useEffect(() => {
    if (open && firstRef.current) firstRef.current.focus();
  }, [open]);

  return (
    <Modal open={open} onClose={onCancel} title="Enter Dice Results">
      <p className="text-sm text-slate-300">
        Enter physical dice rolls for the AI pending actions.
      </p>
      <div className="mt-3 space-y-3 max-h-[60vh] overflow-auto">
        {(pausedActions || []).map((a, idx) => {
          const err = rollValidationErrors[a.request_id];
          return (
            <div
              key={a.request_id}
              className="rounded border border-slate-700 p-3"
            >
              <div className="font-semibold">
                {a.unit} —{" "}
                {a.card_title || (a.card && a.card.title) || "Action"}
              </div>
              <div className="mt-2 flex items-center gap-2">
                <label className="text-xs text-slate-300">Roll (d6):</label>
                <input
                  ref={idx === 0 ? firstRef : null}
                  type="number"
                  min={1}
                  max={6}
                  className="input w-24"
                  value={rollInputs[a.request_id] ?? ""}
                  onChange={(e) => onChangeInput(a.request_id, e.target.value)}
                />
                {err ? (
                  <div className="text-xs text-rose-400 ml-2">
                    Enter a whole number between 1 and 6
                  </div>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button
          className="btn-primary"
          onClick={onSubmit}
          disabled={disableSubmit}
        >
          Submit Rolls
        </button>
      </div>
    </Modal>
  );
}
