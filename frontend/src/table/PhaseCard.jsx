import React from "react";
import { DOCTRINE_LABELS, DOCTRINE_TEXT } from "./doctrine";

function WeaponProfiles({ weapons }) {
  return (
    <div className="mt-3 overflow-x-auto rounded-lg border border-stone-800 bg-stone-950/60">
      <table className="w-full text-left text-[11px]">
        <thead className="border-b border-stone-800 text-stone-500">
          <tr>
            <th className="px-2.5 py-1.5 font-medium">Weapon</th>
            <th className="px-2 py-1.5 text-right font-medium">Range</th>
            <th className="px-2 py-1.5 text-right font-medium">A</th>
            <th className="px-2 py-1.5 text-right font-medium">Hit</th>
            <th className="px-2 py-1.5 text-right font-medium">Wound</th>
            <th className="px-2 py-1.5 text-right font-medium">Rend</th>
            <th className="px-2 py-1.5 text-right font-medium">Dmg</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-800/70 text-stone-200">
          {weapons.map((weapon, index) => (
            <tr key={`${weapon.name}-${index}`}>
              <td className="whitespace-nowrap px-2.5 py-1.5">{weapon.name}</td>
              <td className="whitespace-nowrap px-2 py-1.5 text-right text-stone-400">
                {Number(weapon.range) > 0 ? `${weapon.range}"` : "Melee"}
              </td>
              <td className="px-2 py-1.5 text-right">{weapon.attacks}</td>
              <td className="px-2 py-1.5 text-right">{weapon.hit}+</td>
              <td className="px-2 py-1.5 text-right">{weapon.wound}+</td>
              <td className="px-2 py-1.5 text-right">
                {Number(weapon.rend) > 0 ? `-${weapon.rend}` : "—"}
              </td>
              <td className="px-2 py-1.5 text-right">{weapon.damage}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InstructionRow({ entry }) {
  const isUnit = Boolean(entry.unit_name);
  return (
    <article className="px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          {isUnit ? (
            <>
              <p
                className={`text-[10px] font-semibold uppercase tracking-[0.2em] ${
                  entry.doctrine ? DOCTRINE_TEXT[entry.doctrine] : "text-stone-500"
                }`}
              >
                {DOCTRINE_LABELS[entry.doctrine] || "Unit"}
              </p>
              <h3 className="mt-0.5 text-sm font-semibold text-stone-100">
                {entry.unit_name}
              </h3>
            </>
          ) : (
            <h3 className="text-sm font-semibold text-stone-100">
              {entry.maneuver_name}
            </h3>
          )}
        </div>
        {isUnit && (
          <span className="rounded-full border border-stone-700 bg-stone-950/60 px-2.5 py-0.5 text-[11px] text-stone-300">
            {entry.maneuver_name}
          </span>
        )}
      </div>
      <p className="mt-2 text-sm leading-6 text-stone-200">{entry.instruction}</p>
      <p className="mt-1 text-xs leading-5 text-stone-400">{entry.reason}</p>
      {entry.weapons?.length > 0 && <WeaponProfiles weapons={entry.weapons} />}
    </article>
  );
}

export default function PhaseCard({ phase }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-stone-800 bg-stone-900/70 shadow-xl shadow-black/20">
      <header className="flex items-center justify-between gap-3 border-b border-stone-800 bg-stone-950/30 px-4 py-2.5">
        <h2 className="text-sm font-semibold tracking-wide text-stone-100">
          {phase.name}
        </h2>
        <span className="text-[11px] text-stone-500">
          {phase.instructions.length}{" "}
          {phase.instructions.length === 1 ? "action" : "actions"}
        </span>
      </header>
      {phase.instructions.length === 0 ? (
        <p className="px-4 py-4 text-xs text-stone-500">
          No AI unit has an action in this phase.
        </p>
      ) : (
        <div className="divide-y divide-stone-800/80">
          {phase.instructions.map((entry, index) => (
            <InstructionRow
              key={`${phase.id}-${entry.unit_id || entry.maneuver}-${index}`}
              entry={entry}
            />
          ))}
        </div>
      )}
    </section>
  );
}
