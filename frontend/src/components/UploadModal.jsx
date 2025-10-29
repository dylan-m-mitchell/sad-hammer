import React, { useCallback, useEffect, useRef, useState } from "react";
import Modal from "./Modal";

export default function UploadModal({
  open,
  onClose,
  onFileChange,
  onUpload,
  battleplans = [],
  selectedBattleplan,
  setSelectedBattleplan,
  busy,
}) {
  const [hover, setHover] = useState(false);
  const [localFile, setLocalFile] = useState(null);
  const [step, setStep] = useState(1); // 1=file, 2=options
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open) {
      setLocalFile(null);
      setStep(1);
    }
  }, [open]);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setHover(false);
      const f = e.dataTransfer?.files?.[0] ?? null;
      if (f) {
        setLocalFile(f);
        if (onFileChange) onFileChange({ target: { files: [f] } });
        setStep(2);
      }
    },
    [onFileChange]
  );

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setHover(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setHover(false);
  }, []);

  const handleFilePick = useCallback(
    (e) => {
      const f = e.target.files?.[0] ?? null;
      setLocalFile(f);
      if (onFileChange) onFileChange(e);
      if (f) setStep(2);
    },
    [onFileChange]
  );

  const confirmUpload = async () => {
    if (!localFile) return alert("Choose an HTML file first");
    try {
      await onUpload();
      // parent is expected to close the modal on success
    } catch (e) {
      // parent handles errors
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Upload roster"
      className="max-w-lg"
    >
      {step === 1 ? (
        <div
          id="upload-modal"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`rounded border border-slate-700 p-4 text-center ${
            hover ? "bg-slate-700/40" : ""
          }`}
          style={{ minHeight: 160 }}
        >
          <input
            ref={inputRef}
            id="upload-file-modal"
            type="file"
            accept=".html,.htm,text/html"
            onChange={handleFilePick}
            style={{ display: "none" }}
          />
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-sm text-slate-300 mb-2">
              Drag & drop an HTML roster here
            </div>
            <div className="text-sm text-slate-400 mb-4">or</div>
            <button
              className="btn-secondary"
              onClick={() => inputRef.current && inputRef.current.click()}
            >
              Choose file
            </button>
            <div className="mt-3 text-sm text-slate-200">
              {localFile ? (
                localFile.name
              ) : (
                <span className="text-slate-500">No file selected</span>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div id="upload-options" className="space-y-4">
          <div>
            <label className="text-sm text-slate-300">Battleplan:</label>
            <select
              id="upload-battleplan-select"
              value={selectedBattleplan || ""}
              onChange={(e) =>
                setSelectedBattleplan && setSelectedBattleplan(e.target.value)
              }
              className="w-full mt-1"
            >
              <option value="">(random)</option>
              {battleplans.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.title}
                </option>
              ))}
            </select>
          </div>
          <div className="text-sm text-slate-400">
            File: {localFile ? localFile.name : "None"}
          </div>
        </div>
      )}

      <div className="mt-4 flex justify-between">
        <div>
          {step === 2 && (
            <button
              className="btn-secondary"
              onClick={() => setStep(1)}
              disabled={busy}
            >
              Back
            </button>
          )}
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          {step === 1 ? (
            <button
              id="upload-next"
              className="btn-primary"
              onClick={() => setStep(2)}
              disabled={!localFile || busy}
            >
              Next
            </button>
          ) : (
            <button
              id="upload-confirm"
              className="btn-primary"
              onClick={confirmUpload}
              disabled={busy}
            >
              Upload
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}
