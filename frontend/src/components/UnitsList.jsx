import React, { useEffect, useState } from "react";

export default function UnitsList({ units, onRemove, collapsible = false }) {
  const storageKey = "units.collapsed";
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (!collapsible) return;
    try {
      const raw = localStorage.getItem(storageKey);
      setCollapsed(raw === "1");
    } catch (e) {
      // ignore localStorage errors
    }
  }, [collapsible]);

  useEffect(() => {
    if (!collapsible) return;
    try {
      localStorage.setItem(storageKey, collapsed ? "1" : "0");
    } catch (e) {
      // ignore
    }
  }, [collapsed, collapsible]);

  return (
    <div className="card md:col-span-1">
      <div className="card-header flex items-center justify-between">
        <h2 className="card-title">Units</h2>
        {collapsible && (
          <button
            id="toggle-units"
            onClick={() => setCollapsed((c) => !c)}
            aria-expanded={!collapsed}
            aria-controls="units-content"
            className="text-slate-400 hover:text-slate-300 p-1 rounded"
            title={collapsed ? "Expand units" : "Collapse units"}
          >
            <svg
              className={`w-3 h-3 transform ${
                collapsed ? "rotate-0" : "rotate-180"
              }`}
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M5 12.5L10 7.5L15 12.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        )}
      </div>

      {!collapsed && (
        <div
          id="units-content"
          className="max-h-[30vh] sm:max-h-[480px] overflow-auto px-4 py-3"
        >
          {units.length === 0 ? (
            <p className="text-sm text-slate-300">No units loaded yet.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {units.map((u, i) => (
                <li key={i} className="flex items-center justify-between">
                  <div>
                    {u.name} — {u.models} models
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
      )}
    </div>
  );
}
