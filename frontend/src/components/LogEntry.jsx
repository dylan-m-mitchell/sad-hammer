import React from "react";

export default function LogEntry({ entry }) {
  const { kind, text } = entry || {};
  if (!entry) return null;
  if (kind === "turn") {
    return (
      <div className="text-slate-200 text-sm font-semibold text-center my-2">
        {text}
      </div>
    );
  }
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
        <div className="text-center my-1">
          <div className="text-xs text-slate-400">Aggression check</div>
          <div className={`${cls} text-sm font-semibold`}>
            {unitLabel}Need: {needed ?? "?"} &nbsp; Roll: {actual ?? "?"}
          </div>
        </div>
      );
    }
    return (
      <div className="text-slate-100 leading-tight text-sm mb-0.5">{text}</div>
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
        <div className="text-center my-1">
          <div className="text-xs text-slate-400">Roll result</div>
          <div className={`${cls} text-sm font-semibold`}>
            {unitLabel}Need: {needed ?? "?"} &nbsp; Roll: {actual ?? "?"}
          </div>
        </div>
      );
    }
    return <div className="text-rose-400 text-xs my-1">{text}</div>;
  }
  if (kind === "action")
    return <div className="text-amber-300 font-semibold my-2">{text}</div>;
  if (kind === "request")
    return <div className="text-cyan-300 font-semibold my-3">{text}</div>;
  if (kind === "sep") return <div className="h-2" />;
  if (kind === "note")
    return <div className="text-slate-300 italic my-1">{text}</div>;
  return <div className="text-slate-200 my-1">{text}</div>;
}
