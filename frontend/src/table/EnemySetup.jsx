import React, { useRef, useState } from "react";
import { validateRoster } from "./api";
import { DOCTRINE_LABELS, DOCTRINE_STYLES, unitsByDoctrine } from "./doctrine";

const DOCTRINE_ORDER = ["press", "support", "hold"];

function RosterSummary({ roster }) {
  const groups = unitsByDoctrine(roster);
  return (
    <ul className="space-y-2">
      {DOCTRINE_ORDER.filter((doctrine) => groups[doctrine].length > 0).map(
        (doctrine) => (
          <li key={doctrine} className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${DOCTRINE_STYLES[doctrine]}`}
            >
              {DOCTRINE_LABELS[doctrine]}
            </span>
            <span className="text-xs leading-5 text-stone-300">
              {groups[doctrine].map((unit) => unit.name).join(", ")}
            </span>
          </li>
        )
      )}
    </ul>
  );
}

export default function EnemySetup({
  defaultRoster,
  loading,
  onUseDefault,
  onImport,
  onOpenBuilder,
}) {
  const [importOpen, setImportOpen] = useState(false);
  const [jsonText, setJsonText] = useState("");
  const [issues, setIssues] = useState([]);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef(null);

  function readFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setJsonText(String(reader.result || ""));
    reader.onerror = () =>
      setIssues([{ field: "File", message: "That file could not be read." }]);
    reader.readAsText(file);
  }

  async function applyImport() {
    setBusy(true);
    setIssues([]);
    try {
      let parsed;
      try {
        parsed = JSON.parse(jsonText);
      } catch (parseError) {
        setIssues([{ field: "JSON", message: "That is not valid JSON." }]);
        return;
      }
      try {
        const result = await validateRoster(parsed);
        onImport(result.roster);
      } catch (error) {
        const raw =
          error.payload?.issues?.length > 0
            ? error.payload.issues
            : [{ field: "Roster", message: error.message }];
        setIssues(raw);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-4">
      <div className="px-1">
        <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-amber-400/90">
          Set the table
        </p>
        <h2 className="mt-1 text-2xl font-semibold tracking-tight text-stone-50">
          Set the enemy army
        </h2>
        <p className="mt-1 text-sm leading-6 text-stone-400">
          Choose the army the AI will play. Start with the Skaven test army or
          import a roster of your own.
        </p>
      </div>

      {!defaultRoster ? (
        <section className="rounded-2xl border border-stone-800 bg-stone-900/70 px-4 py-8 text-center">
          <p className="text-sm text-stone-400">
            {loading ? "Loading the starter army…" : "The starter army is unavailable."}
          </p>
        </section>
      ) : (
        <article className="rounded-2xl border border-stone-800 bg-stone-900/70 p-4 shadow-xl shadow-black/20">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.25em] text-amber-400/90">
                Starter army
              </p>
              <h3 className="truncate text-lg font-semibold text-stone-50">
                {defaultRoster.name}
              </h3>
              <p className="text-xs text-stone-500">
                {defaultRoster.faction} · {defaultRoster.units.length} units · ready
                to test against
              </p>
            </div>
          </div>
          <div className="mt-3">
            <RosterSummary roster={defaultRoster} />
          </div>
          <button
            type="button"
            onClick={() => onUseDefault(defaultRoster)}
            className="mt-4 w-full rounded-xl bg-amber-500 px-4 py-3 text-sm font-semibold text-stone-950 transition hover:bg-amber-400"
          >
            Use the {defaultRoster.name} army
          </button>
        </article>
      )}

      <article className="rounded-2xl border border-stone-800 bg-stone-900/70 p-4 shadow-xl shadow-black/20">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-stone-100">
              Import your own army
            </h3>
            <p className="mt-0.5 text-xs leading-5 text-stone-500">
              Paste a roster JSON or pick a .json file. Unit IDs and duplicates
              are normalised on import.
            </p>
          </div>
          {!importOpen && (
            <button
              type="button"
              onClick={() => setImportOpen(true)}
              className="shrink-0 rounded-lg border border-stone-700 bg-stone-950/50 px-3 py-1.5 text-xs font-medium text-stone-300 transition hover:border-stone-500 hover:text-stone-100"
            >
              Import
            </button>
          )}
        </div>

        {importOpen && (
          <div className="mt-3 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => fileInput.current?.click()}
                className="rounded-lg border border-stone-700 bg-stone-950/50 px-3 py-1.5 text-[11px] text-stone-300 transition hover:border-stone-500 hover:text-stone-100"
              >
                Choose a file
              </button>
              <input
                ref={fileInput}
                type="file"
                accept="application/json,.json"
                onChange={readFile}
                className="hidden"
              />
              <span className="text-[11px] text-stone-500">or paste below</span>
            </div>
            <textarea
              className="input h-48 font-mono text-[11px] leading-5"
              value={jsonText}
              spellCheck={false}
              placeholder={'{ "name": "My army", "units": [ … ] }'}
              onChange={(event) => setJsonText(event.target.value)}
              aria-label="Enemy army JSON"
            />
            {issues.length > 0 && (
              <ul
                role="alert"
                className="space-y-1 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-100"
              >
                {issues.map((issue, index) => (
                  <li key={`${issue.field}-${index}`}>
                    <span className="font-semibold">{issue.field}:</span>{" "}
                    {issue.message}
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setImportOpen(false);
                  setJsonText("");
                  setIssues([]);
                }}
                className="rounded-lg border border-stone-700 px-3 py-2 text-xs text-stone-300 transition hover:border-stone-500"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={applyImport}
                disabled={busy || jsonText.trim() === ""}
                className="rounded-lg bg-amber-500 px-4 py-2 text-xs font-semibold text-stone-950 transition hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy ? "Checking…" : "Use this army"}
              </button>
            </div>
          </div>
        )}
      </article>

      <div className="text-center">
        <button
          type="button"
          onClick={onOpenBuilder}
          className="text-[11px] text-stone-500 underline-offset-4 transition hover:text-stone-300 hover:underline"
        >
          Open the roster editor
        </button>
      </div>
    </section>
  );
}
