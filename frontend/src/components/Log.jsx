import React from "react";

export default function Log({ log, collapsedTurns, setCollapsedTurns }) {
  if (!Array.isArray(log)) return null;

  const renderEntry = (entry, key) => {
    if (!entry) return null;
    const { kind, text } = entry;
    if (kind === "check") {
      if (text && typeof text === "object") {
        const needed = text.needed ?? null;
        const actual = text.actual ?? null;
        const passed =
          typeof needed === "number" && typeof actual === "number"
            ? actual >= needed
            : null;
        const cls =
          passed === null
            ? "text-slate-300"
            : passed
            ? "text-emerald-400"
            : "text-rose-400";
        const unitLabel = text.unit ? `${text.unit} — ` : "";
        return (
          <div key={key} className="text-center my-1">
            <div className="text-xs text-slate-400">Aggression check</div>
            <div className={`${cls} text-sm font-semibold`}>
              {unitLabel}Need: {needed ?? "?"} &nbsp; Roll: {actual ?? "?"}
            </div>
          </div>
        );
      }
      return (
        <div key={key} className="text-slate-100 leading-tight text-sm mb-0.5">
          {text}
        </div>
      );
    }
    if (kind === "roll") {
      if (text && typeof text === "object") {
        const needed = text.needed ?? null;
        const actual = text.actual ?? null;
        const passed =
          typeof needed === "number" && typeof actual === "number"
            ? actual >= needed
            : null;
        const cls =
          passed === null
            ? "text-slate-300"
            : passed
            ? "text-emerald-400"
            : "text-rose-400";
        const unitLabel = text.unit ? `${text.unit} — ` : "";
        return (
          <div key={key} className="text-center my-1">
            <div className="text-xs text-slate-400">Roll result</div>
            <div className={`${cls} text-sm font-semibold`}>
              {unitLabel}Need: {needed ?? "?"} &nbsp; Roll: {actual ?? "?"}
            </div>
          </div>
        );
      }
      return (
        <div key={key} className="text-rose-400 text-xs my-1">
          {text}
        </div>
      );
    }
    if (kind === "tactic")
      return (
        <div
          key={key}
          className="text-amber-400 font-bold text-lg my-2 text-center bg-amber-900/20 py-2 px-4 rounded border border-amber-600/30"
        >
          {text}
        </div>
      );
    if (kind === "tactic-separator")
      return (
        <div key={key} className="text-amber-600/50 text-center my-1">
          {text}
        </div>
      );
    if (kind === "action")
      return (
        <div
          key={key}
          className="text-amber-200 font-semibold my-2 pl-2 border-l-2 border-amber-500/40"
        >
          {text}
        </div>
      );
    if (kind === "behavior")
      return (
        <div key={key} className="text-slate-300 text-sm my-1 pl-4 italic">
          {text}
        </div>
      );
    if (kind === "request")
      return (
        <div key={key} className="text-cyan-300 font-semibold my-3">
          {text}
        </div>
      );
    if (kind === "sep") return <div key={key} className="h-2" />;
    if (kind === "note")
      return (
        <div key={key} className="text-slate-300 italic my-1">
          {text}
        </div>
      );
    return (
      <div key={key} className="text-slate-200 my-1">
        {text}
      </div>
    );
  };

  // Build groups split by 'turn' entries
  const groups = [];
  let current = { startIdx: -1, title: null, entries: [] };
  log.forEach((entry, idx) => {
    if (!entry) return;
    if (entry.kind === "turn") {
      if (current.entries.length > 0 || current.title !== null)
        groups.push(current);
      current = { startIdx: idx, title: entry.text, entries: [] };
    } else {
      current.entries.push({ entry, idx });
    }
  });
  if (current.entries.length > 0 || current.title !== null)
    groups.push(current);

  return (
    <div className="max-h-[50vh] sm:max-h-[480px] overflow-auto text-sm font-mono">
      {groups.map((g) => {
        const gid = g.startIdx;
        const collapsed = (collapsedTurns && collapsedTurns[gid]) ?? false;
        return (
          <div key={`group-${gid}`} className="mb-2">
            {g.title ? (
              <div className="flex items-center justify-between">
                <div className="text-slate-200 text-sm font-semibold text-center w-full">
                  {g.title}
                </div>
                <button
                  className="ml-2 btn-ghost text-xs"
                  onClick={() =>
                    setCollapsedTurns((p) => ({
                      ...(p || {}),
                      [gid]: !p?.[gid],
                    }))
                  }
                  aria-expanded={!collapsed}
                >
                  {collapsed ? "Expand" : "Collapse"}
                </button>
              </div>
            ) : null}
            <div className={collapsed ? "hidden" : "mt-2"}>
              {g.entries.map(({ entry, idx }) =>
                renderEntry(entry, `log-${idx}`)
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
