import React from "react";
import { TOTAL_ROUNDS } from "./storage";
import { classifyUnit, DOCTRINE_LABELS, DOCTRINE_STYLES } from "./doctrine";

function number(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return value;
  return Number.isInteger(parsed) ? parsed : parsed.toFixed(1);
}

function UnitRow({ unit, destroyed, onToggle }) {
  const doctrine = classifyUnit(unit);
  return (
    <li
      className={`px-4 py-3 transition ${
        destroyed ? "bg-stone-950/40 opacity-60" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3
              className={`text-sm font-semibold ${
                destroyed
                  ? "text-stone-500 line-through decoration-stone-600"
                  : "text-stone-100"
              }`}
            >
              {unit.name}
            </h3>
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${DOCTRINE_STYLES[doctrine]}`}
            >
              {DOCTRINE_LABELS[doctrine]}
            </span>
          </div>
          <p className="mt-1 text-[11px] leading-5 text-stone-400">
            Move {number(unit.move)}" · Save {unit.save}+ · Health{" "}
            {unit.health} · Models {unit.models} · Control {unit.control}
          </p>
          <p className="mt-0.5 text-[11px] leading-5 text-stone-500">
            {(unit.weapons || []).map((weapon) => weapon.name).join(" · ")}
          </p>
        </div>
        <label className="flex shrink-0 cursor-pointer items-center gap-2 rounded-lg border border-stone-800 bg-stone-950/50 px-2.5 py-1.5 text-[11px] text-stone-400">
          <input
            type="checkbox"
            checked={destroyed}
            onChange={() => onToggle(unit.id)}
            className="h-4 w-4 rounded border-stone-600 bg-stone-900 accent-rose-500"
            aria-label={`Mark ${unit.name} destroyed`}
          />
          Destroyed
        </label>
      </div>
    </li>
  );
}

export default function AiRosterPanel({
  roster,
  round,
  destroyed,
  onRoundChange,
  onToggleDestroyed,
  onOpenBuilder,
}) {
  const destroyedSet = new Set(destroyed);
  const units = roster?.units || [];
  const activeCount = units.filter((unit) => !destroyedSet.has(unit.id)).length;

  return (
    <section className="rounded-2xl border border-stone-800 bg-stone-900/70 shadow-xl shadow-black/20">
      <header className="border-b border-stone-800 px-4 py-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.25em] text-amber-400/90">
              AI army
            </p>
            <h2 className="truncate text-sm font-semibold text-stone-100">
              {roster?.name || "AI roster"}
            </h2>
            <p className="text-xs text-stone-500">
              {activeCount} of {units.length} units active
            </p>
          </div>
          <button
            type="button"
            onClick={onOpenBuilder}
            className="rounded-lg border border-stone-700 bg-stone-950/50 px-3 py-1.5 text-xs font-medium text-stone-300 transition hover:border-stone-500 hover:text-stone-100"
          >
            Edit rosters
          </button>
        </div>

        <div className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-stone-800 bg-stone-950/40 px-3 py-2">
          <div>
            <p className="text-[10px] uppercase tracking-[0.2em] text-stone-500">
              Battle round
            </p>
            <p className="text-sm font-semibold text-stone-100">
              Round {round}
              <span className="font-normal text-stone-500">
                {" "}
                of {TOTAL_ROUNDS}
              </span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onRoundChange(-1)}
              disabled={round <= 1}
              aria-label="Previous round"
              className="h-9 w-9 rounded-lg border border-stone-700 bg-stone-900 text-base text-stone-200 transition hover:border-stone-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              −
            </button>
            <button
              type="button"
              onClick={() => onRoundChange(1)}
              disabled={round >= TOTAL_ROUNDS}
              aria-label="Next round"
              className="h-9 w-9 rounded-lg border border-stone-700 bg-stone-900 text-base text-stone-200 transition hover:border-stone-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              +
            </button>
          </div>
        </div>
      </header>

      <ul className="divide-y divide-stone-800/80">
        {units.map((unit) => (
          <UnitRow
            key={unit.id}
            unit={unit}
            destroyed={destroyedSet.has(unit.id)}
            onToggle={onToggleDestroyed}
          />
        ))}
      </ul>
    </section>
  );
}
