import React from "react";

export default function UnitsList({ units, onRemove }) {
  return (
    <div className="card md:col-span-1 flex flex-col min-h-[160px]">
      <div className="card-header">
        <h2 className="card-title">Units</h2>
      </div>
      <div className="max-h-[480px] overflow-auto px-4 py-3 flex-1 min-h-0">
        {units.length === 0 ? (
          <p className="text-sm text-slate-300">No units loaded yet.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {units.map((u, i) => (
              <li key={i} className="flex items-center justify-between">
                <div>
                  {u.name} — {u.models} models
                  {u.wounds_per_model ? `, ${u.wounds_per_model} wpmodel` : ""}
                </div>
                {onRemove ? (
                  <button
                    id={`remove-unit-${u.name.replace(/\s+/g, "-")}`}
                    className="btn-secondary text-xs"
                    onClick={() => onRemove(u.name)}
                  >
                    Remove
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
