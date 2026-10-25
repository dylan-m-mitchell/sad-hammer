import React from "react";
import {
  DOCTRINE_LABELS,
  DOCTRINE_STYLES,
  unitsByDoctrine,
} from "./doctrine";

const GUIDE = {
  press: "Deploy forward, toward the closest enemy.",
  support: "Deploy in cover with a line of sight.",
  hold: "Deploy near an objective, beside a friendly unit.",
};

const ITEMS = [
  {
    key: "objectives",
    title: "Place the objectives",
    detail: "Place the objectives across the battlefield, spread out.",
  },
  {
    key: "terrain",
    title: "Place the terrain",
    detail: "Place the terrain, leaving lanes to move and shoot through.",
  },
  {
    key: "playerDeploy",
    title: "Deploy your army",
    detail: "Deploy your units in your deployment zone.",
  },
  {
    key: "aiDeploy",
    title: "Deploy the AI army",
    detail: "Use the doctrine guide below — no coordinates required.",
  },
];

function GuideRow({ doctrine, units }) {
  if (!units.length) return null;
  return (
    <li className="flex gap-2 text-xs leading-5 text-stone-300">
      <span
        className={`mt-0.5 shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${DOCTRINE_STYLES[doctrine]}`}
      >
        {DOCTRINE_LABELS[doctrine]}
      </span>
      <span>
        {GUIDE[doctrine]}
        <span className="text-stone-500">
          {" "}
          ({units.length} {units.length === 1 ? "unit" : "units"})
        </span>
      </span>
    </li>
  );
}

export default function SetupChecklist({ checklist, aiRoster, onToggle }) {
  const groups = unitsByDoctrine(aiRoster);
  const done = ITEMS.filter((item) => checklist[item.key]).length;

  return (
    <section className="rounded-2xl border border-stone-800 bg-stone-900/70 shadow-xl shadow-black/20">
      <header className="flex items-center justify-between gap-3 border-b border-stone-800 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-stone-100">Before you start</h2>
          <p className="text-xs text-stone-500">
            Set the table, then let the planner call the AI's round.
          </p>
        </div>
        <span className="rounded-full border border-stone-700 bg-stone-950/60 px-2.5 py-1 text-[11px] text-stone-400">
          {done}/{ITEMS.length}
        </span>
      </header>

      <ul className="divide-y divide-stone-800/80">
        {ITEMS.map((item, index) => {
          const checked = Boolean(checklist[item.key]);
          return (
            <li key={item.key}>
              <label className="flex cursor-pointer items-start gap-3 px-4 py-3">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(item.key)}
                  className="mt-0.5 h-5 w-5 shrink-0 rounded border-stone-600 bg-stone-900 accent-amber-500"
                />
                <span className="min-w-0">
                  <span className="flex items-baseline gap-2">
                    <span className="text-[11px] font-semibold text-stone-500">
                      {index + 1}
                    </span>
                    <span
                      className={`text-sm font-medium ${
                        checked ? "text-stone-400 line-through" : "text-stone-100"
                      }`}
                    >
                      {item.title}
                    </span>
                  </span>
                  <span className="mt-0.5 block text-xs leading-5 text-stone-400">
                    {item.detail}
                  </span>
                  {item.key === "aiDeploy" && (
                    <ul className="mt-2 space-y-1.5">
                      <GuideRow doctrine="press" units={groups.press} />
                      <GuideRow doctrine="support" units={groups.support} />
                      <GuideRow doctrine="hold" units={groups.hold} />
                    </ul>
                  )}
                </span>
              </label>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
