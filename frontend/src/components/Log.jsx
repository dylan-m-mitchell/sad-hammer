import React from "react";
import LogEntry from "./LogEntry";

export default function Log({ entries }) {
  return (
    <div className="max-h-[480px] overflow-auto text-sm font-mono">
      {entries.map((e, i) => (
        <LogEntry key={`log-${i}`} entry={e} />
      ))}
    </div>
  );
}
