import React, { useState } from "react";
import { validateRoster } from "./api";
import { classifyUnit, DOCTRINE_LABELS, DOCTRINE_STYLES } from "./doctrine";

const UNIT_STATS = [
  { key: "move", label: "Move", min: 0 },
  { key: "save", label: "Save", min: 2, max: 6 },
  { key: "health", label: "Health", min: 1 },
  { key: "models", label: "Models", min: 1 },
  { key: "control", label: "Control", min: 0 },
];

const WEAPON_STATS = [
  { key: "range", label: "Range", min: 0 },
  { key: "attacks", label: "Attacks", min: 1 },
  { key: "hit", label: "Hit", min: 2, max: 6 },
  { key: "wound", label: "Wound", min: 2, max: 6 },
  { key: "rend", label: "Rend", min: 0 },
  { key: "damage", label: "Damage", min: 1 },
];

function copy(value) {
  return JSON.parse(JSON.stringify(value));
}

function newWeapon() {
  return {
    name: "Weapon",
    range: 0,
    attacks: 1,
    hit: 4,
    wound: 4,
    rend: 0,
    damage: 1,
  };
}

function newUnit() {
  return {
    name: "New unit",
    move: 5,
    save: 4,
    health: 1,
    models: 1,
    control: 1,
    keywords: ["Infantry"],
    keywordsText: "Infantry",
    weapons: [newWeapon()],
  };
}

function submitShape(roster) {
  return {
    name: roster.name,
    faction: roster.faction,
    units: (roster.units || []).map((unit) => ({
      ...(unit.id ? { id: unit.id } : {}),
      name: unit.name,
      move: unit.move,
      save: unit.save,
      health: unit.health,
      models: unit.models,
      control: unit.control,
      keywords: Array.isArray(unit.keywords) ? unit.keywords : [],
      weapons: (unit.weapons || []).map((weapon) => ({
        name: weapon.name,
        range: weapon.range,
        attacks: weapon.attacks,
        hit: weapon.hit,
        wound: weapon.wound,
        rend: weapon.rend,
        damage: weapon.damage,
      })),
    })),
  };
}

function issuesFrom(error, label) {
  const raw =
    error.payload?.issues?.length > 0
      ? error.payload.issues
      : [{ field: "roster", message: error.message }];
  return raw.map((issue) => ({
    field: `${label} · ${issue.field}`,
    message: issue.message,
  }));
}

export default function RosterBuilder({
  rosters,
  onSave,
  onClose,
  initialSlot = "player",
}) {
  const [drafts, setDrafts] = useState(() => ({
    player: copy(rosters.player),
    ai: copy(rosters.ai),
  }));
  const [active, setActive] = useState(
    initialSlot === "ai" ? "ai" : "player"
  );
  const [jsonOpen, setJsonOpen] = useState(false);
  const [jsonText, setJsonText] = useState("");
  const [issues, setIssues] = useState([]);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  const draft = drafts[active];
  const label = active === "player" ? "Your roster" : "AI roster";

  function updateActive(updater) {
    setDrafts((previous) => ({
      ...previous,
      [active]: updater(previous[active]),
    }));
  }

  function updateUnit(index, patch) {
    updateActive((current) => ({
      ...current,
      units: current.units.map((unit, unitIndex) =>
        unitIndex === index ? { ...unit, ...patch } : unit
      ),
    }));
  }

  function updateWeapon(unitIndex, weaponIndex, patch) {
    updateActive((current) => ({
      ...current,
      units: current.units.map((unit, index) =>
        index === unitIndex
          ? {
              ...unit,
              weapons: unit.weapons.map((weapon, weaponPosition) =>
                weaponPosition === weaponIndex
                  ? { ...weapon, ...patch }
                  : weapon
              ),
            }
          : unit
      ),
    }));
  }

  function addUnit() {
    updateActive((current) => ({
      ...current,
      units: [...current.units, newUnit()],
    }));
  }

  function removeUnit(index) {
    updateActive((current) => ({
      ...current,
      units: current.units.filter((unit, position) => position !== index),
    }));
  }

  function addWeapon(unitIndex) {
    updateActive((current) => ({
      ...current,
      units: current.units.map((unit, index) =>
        index === unitIndex && unit.weapons.length < 12
          ? { ...unit, weapons: [...unit.weapons, newWeapon()] }
          : unit
      ),
    }));
  }

  function removeWeapon(unitIndex, weaponIndex) {
    updateActive((current) => ({
      ...current,
      units: current.units.map((unit, index) =>
        index === unitIndex && unit.weapons.length > 1
          ? {
              ...unit,
              weapons: unit.weapons.filter(
                (weapon, position) => position !== weaponIndex
              ),
            }
          : unit
      ),
    }));
  }

  function selectTab(slot) {
    setActive(slot);
    setJsonOpen(false);
    setJsonText("");
    setIssues([]);
    setMessage(null);
  }

  function swapSides() {
    setDrafts((previous) => ({
      player: previous.ai,
      ai: previous.player,
    }));
    setJsonOpen(false);
    setJsonText("");
    setIssues([]);
    setMessage("Sides swapped in the draft. Save rosters to apply.");
  }

  async function save() {
    setBusy(true);
    setIssues([]);
    setMessage(null);
    try {
      let player;
      try {
        player = (await validateRoster(submitShape(drafts.player))).roster;
      } catch (error) {
        setIssues(issuesFrom(error, "Your roster"));
        return;
      }
      let ai;
      try {
        ai = (await validateRoster(submitShape(drafts.ai))).roster;
      } catch (error) {
        setIssues(issuesFrom(error, "AI roster"));
        return;
      }
      onSave({ player, ai });
    } finally {
      setBusy(false);
    }
  }

  function toggleJson() {
    if (!jsonOpen) {
      setJsonText(JSON.stringify(submitShape(draft), null, 2));
      setMessage(null);
    }
    setJsonOpen((value) => !value);
  }

  async function applyJson() {
    setBusy(true);
    setIssues([]);
    setMessage(null);
    try {
      let parsed;
      try {
        parsed = JSON.parse(jsonText);
      } catch (error) {
        setIssues([{ field: "JSON", message: "That is not valid JSON." }]);
        return;
      }
      try {
        const result = await validateRoster(parsed);
        setDrafts((previous) => ({ ...previous, [active]: result.roster }));
        setJsonText(JSON.stringify(result.roster, null, 2));
        setMessage("JSON loaded into the draft. Save rosters to apply.");
      } catch (error) {
        setIssues(issuesFrom(error, label));
      }
    } finally {
      setBusy(false);
    }
  }

  async function copyJson() {
    try {
      await navigator.clipboard.writeText(jsonText);
      setMessage("JSON copied to the clipboard.");
    } catch (error) {
      setMessage("Copy failed — select the JSON and copy it manually.");
    }
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-amber-500/25 bg-stone-900/85 shadow-2xl shadow-black/30">
      <header className="flex items-start justify-between gap-3 border-b border-stone-800 px-4 py-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.25em] text-amber-400/90">
            Rosters
          </p>
          <h2 className="text-sm font-semibold text-stone-100">
            Build, swap or import
          </h2>
          <p className="text-xs text-stone-500">
            Saved in this browser. No points, no matched-play rules.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-stone-700 bg-stone-950/50 px-3 py-1.5 text-xs text-stone-300 transition hover:border-stone-500 hover:text-stone-100"
        >
          Close
        </button>
      </header>

      <div className="border-b border-stone-800 px-4 py-3">
        <div role="tablist" aria-label="Roster to edit" className="flex gap-2">
          {[
            ["player", "Your roster"],
            ["ai", "AI roster"],
          ].map(([slot, tabLabel]) => (
            <button
              key={slot}
              type="button"
              role="tab"
              aria-selected={active === slot}
              onClick={() => selectTab(slot)}
              className={`rounded-lg px-3 py-2 text-xs font-medium transition ${
                active === slot
                  ? "bg-amber-500 text-stone-950"
                  : "border border-stone-700 bg-stone-950/40 text-stone-300 hover:border-stone-500"
              }`}
            >
              {tabLabel}
            </button>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={swapSides}
            className="rounded-lg border border-stone-700 bg-stone-950/40 px-3 py-1.5 text-xs text-stone-300 transition hover:border-stone-500 hover:text-stone-100"
          >
            Swap sides
          </button>
          <button
            type="button"
            onClick={toggleJson}
            className="rounded-lg border border-stone-700 bg-stone-950/40 px-3 py-1.5 text-xs text-stone-300 transition hover:border-stone-500 hover:text-stone-100"
          >
            {jsonOpen ? "Hide JSON" : "Import / export JSON"}
          </button>
        </div>
      </div>

      <div className="space-y-4 px-4 py-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-[11px] text-stone-400">
            Roster name
            <input
              className="input mt-1"
              value={draft.name}
              onChange={(event) =>
                updateActive((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
            />
          </label>
          <label className="text-[11px] text-stone-400">
            Faction
            <input
              className="input mt-1"
              value={draft.faction || ""}
              onChange={(event) =>
                updateActive((current) => ({
                  ...current,
                  faction: event.target.value,
                }))
              }
            />
          </label>
        </div>

        {(draft.units || []).map((unit, unitIndex) => {
          const doctrine = classifyUnit(unit);
          const keywordsText =
            unit.keywordsText ?? (unit.keywords || []).join(", ");
          return (
            <div
              key={unitIndex}
              className="rounded-xl border border-stone-800 bg-stone-950/40 p-3"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-stone-500">
                    Unit {unitIndex + 1}
                  </span>
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${DOCTRINE_STYLES[doctrine]}`}
                  >
                    {DOCTRINE_LABELS[doctrine]}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => removeUnit(unitIndex)}
                  disabled={draft.units.length <= 1}
                  className="text-[11px] text-rose-300 underline-offset-4 transition hover:text-rose-200 hover:underline disabled:cursor-not-allowed disabled:text-stone-600 disabled:no-underline"
                >
                  Remove
                </button>
              </div>

              <label className="mt-3 block text-[11px] text-stone-400">
                Name
                <input
                  className="input mt-1"
                  value={unit.name || ""}
                  onChange={(event) =>
                    updateUnit(unitIndex, { name: event.target.value })
                  }
                />
              </label>

              <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-5">
                {UNIT_STATS.map((field) => (
                  <label
                    key={field.key}
                    className="text-[11px] text-stone-400"
                  >
                    {field.label}
                    <input
                      className="input mt-1"
                      type="number"
                      min={field.min}
                      max={field.max}
                      value={unit[field.key] ?? ""}
                      onChange={(event) =>
                        updateUnit(unitIndex, {
                          [field.key]: event.target.value,
                        })
                      }
                    />
                  </label>
                ))}
              </div>

              <label className="mt-2 block text-[11px] text-stone-400">
                Keywords
                <input
                  className="input mt-1"
                  value={keywordsText}
                  placeholder="Hero, Infantry"
                  onChange={(event) =>
                    updateUnit(unitIndex, {
                      keywordsText: event.target.value,
                      keywords: event.target.value
                        .split(",")
                        .map((keyword) => keyword.trim())
                        .filter(Boolean),
                    })
                  }
                />
              </label>

              <div className="mt-3 space-y-2">
                {(unit.weapons || []).map((weapon, weaponIndex) => (
                  <div
                    key={weaponIndex}
                    className="rounded-lg border border-stone-800 bg-stone-900/60 p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-stone-500">
                        Weapon {weaponIndex + 1}
                      </span>
                      <button
                        type="button"
                        onClick={() => removeWeapon(unitIndex, weaponIndex)}
                        disabled={unit.weapons.length <= 1}
                        className="text-[11px] text-rose-300 underline-offset-4 transition hover:text-rose-200 hover:underline disabled:cursor-not-allowed disabled:text-stone-600 disabled:no-underline"
                      >
                        Remove
                      </button>
                    </div>
                    <label className="mt-2 block text-[11px] text-stone-400">
                      Name
                      <input
                        className="input mt-1"
                        value={weapon.name || ""}
                        onChange={(event) =>
                          updateWeapon(unitIndex, weaponIndex, {
                            name: event.target.value,
                          })
                        }
                      />
                    </label>
                    <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-6">
                      {WEAPON_STATS.map((field) => (
                        <label
                          key={field.key}
                          className="text-[11px] text-stone-400"
                        >
                          {field.label}
                          <input
                            className="input mt-1"
                            type="number"
                            min={field.min}
                            max={field.max}
                            value={weapon[field.key] ?? ""}
                            onChange={(event) =>
                              updateWeapon(unitIndex, weaponIndex, {
                                [field.key]: event.target.value,
                              })
                            }
                          />
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => addWeapon(unitIndex)}
                  disabled={unit.weapons.length >= 12}
                  className="w-full rounded-lg border border-dashed border-stone-700 px-3 py-2 text-[11px] text-stone-400 transition hover:border-stone-500 hover:text-stone-200 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  + Add weapon
                </button>
              </div>
            </div>
          );
        })}

        <button
          type="button"
          onClick={addUnit}
          className="w-full rounded-xl border border-dashed border-stone-700 px-3 py-2.5 text-xs text-stone-300 transition hover:border-stone-500 hover:text-stone-100"
        >
          + Add unit
        </button>

        {jsonOpen && (
          <div className="rounded-xl border border-stone-800 bg-stone-950/50 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-medium text-stone-200">
                {label} JSON
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={copyJson}
                  className="rounded-lg border border-stone-700 px-2.5 py-1 text-[11px] text-stone-300 transition hover:border-stone-500"
                >
                  Copy
                </button>
                <button
                  type="button"
                  onClick={applyJson}
                  disabled={busy}
                  className="rounded-lg bg-amber-500 px-2.5 py-1 text-[11px] font-semibold text-stone-950 transition hover:bg-amber-400 disabled:opacity-60"
                >
                  Apply JSON
                </button>
              </div>
            </div>
            <textarea
              className="input mt-2 h-56 font-mono text-[11px] leading-5"
              value={jsonText}
              spellCheck={false}
              onChange={(event) => setJsonText(event.target.value)}
              aria-label={`${label} JSON`}
            />
            <p className="mt-1 text-[11px] text-stone-500">
              Paste a roster here or copy this JSON out. Unit IDs and duplicates
              are normalised when you apply it.
            </p>
          </div>
        )}

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
        {message && (
          <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-[11px] text-emerald-100">
            {message}
          </p>
        )}
      </div>

      <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-stone-800 bg-stone-950/50 px-4 py-3">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-stone-700 px-3 py-2 text-xs text-stone-300 transition hover:border-stone-500"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={save}
          disabled={busy}
          className="rounded-lg bg-amber-500 px-4 py-2 text-xs font-semibold text-stone-950 transition hover:bg-amber-400 disabled:opacity-60"
        >
          {busy ? "Checking…" : "Save rosters"}
        </button>
      </footer>
    </section>
  );
}
