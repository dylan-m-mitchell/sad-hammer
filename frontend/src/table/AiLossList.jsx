import React from "react";
import { classifyUnit, DOCTRINE_LABELS, DOCTRINE_STYLES } from "./doctrine";

export default function AiLossList({
  roster,
  destroyed,
  onToggle,
  defaultOpen = false,
}) {
  const destroyedSet = new Set(destroyed);
  const units = roster?.units || [];
  const activeCount = units.filter((unit) => !destroyedSet.has(unit.id)).length;

  return (
    <details
      open={defaultOpen}
      className="overflow-hidden rounded-xl border border-stone-800 bg-stone-900/60"
    >
      <summary className="cursor-pointer px-4 py-2.5 text-xs text-stone-300">
        AI losses
        <span className="ml-2 text-stone-500">
          {activeCount} of {units.length} units active
        </span>
      </summary>
      <ul className="divide-y divide-stone-800/80 border-t border-stone-800">
        {units.map((unit) => {
          const destroyedUnit = destroyedSet.has(unit.id);
          return (
            <li key={unit.id}>
              <label className="flex cursor-pointer items-center gap-3 px-4 py-2.5">
                <input
                  type="checkbox"
                  checked={destroyedUnit}
                  onChange={() => onToggle(unit.id)}
                  className="h-4 w-4 shrink-0 rounded border-stone-600 bg-stone-900 accent-rose-500"
                  aria-label={`Mark ${unit.name} destroyed`}
                />
                <span
                  className={`min-w-0 flex-1 truncate text-xs ${
                    destroyedUnit
                      ? "text-stone-500 line-through decoration-stone-600"
                      : "text-stone-200"
                  }`}
                >
                  {unit.name}
                </span>
                <span
                  className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                    DOCTRINE_STYLES[classifyUnit(unit)]
                  }`}
                >
                  {DOCTRINE_LABELS[classifyUnit(unit)]}
                </span>
              </label>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
