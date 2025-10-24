import React, { useEffect, useMemo, useState } from "react";

// Module-level cache to prevent duplicate /api/battleplans requests
// (React StrictMode in development may mount/unmount/mount components which
// would otherwise trigger the effect twice). Caching here avoids extra
// network traffic while preserving correctness.
let BATTLEPLANS_CACHE = null;

const api = {
  getBattleplans: async () => {
    const res = await fetch("/api/battleplans");
    if (!res.ok) throw new Error(`Failed to load battleplans: ${res.status}`);
    return res.json();
  },
  runAiTurn: async (sessionId) => {
    const res = await fetch(`/api/session/${sessionId}/ai_turn`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`Failed to run AI turn: ${res.status}`);
    // return text (server returns human-readable summary) but structured events are available via last_turn
    return res.text();
  },
  getLastTurn: async (sessionId) => {
    const res = await fetch(`/api/session/${sessionId}/last_turn`);
    if (!res.ok) throw new Error(`Failed to get last turn: ${res.status}`);
    return res.json();
  },
  resolveRolls: async (sessionId, actionResults) => {
    const res = await fetch(`/api/session/${sessionId}/resolve_rolls`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_results: actionResults }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  loadRoster: async (file) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/load_roster", { method: "POST", body: fd });
    if (!res.ok) throw new Error(`Failed to load roster: ${res.status}`);
    return res.json();
  },
  runSimulation: async (units, turns = 5, seed = 1) => {
    const res = await fetch("/api/run_simulation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ units, turns, seed }),
    });
    if (!res.ok) throw new Error(`Failed to run simulation: ${res.status}`);
    return res.json();
  },
  createSession: async (file, rollMode = "ai", battleplan = "") => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("roll_mode", rollMode);
    if (battleplan) fd.append("battleplan", String(battleplan));
    const res = await fetch("/api/session", { method: "POST", body: fd });
    if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
    return res.json();
  },
  getSession: async (sessionId) => {
    const res = await fetch(`/api/session/${sessionId}`);
    if (!res.ok) throw new Error(`Failed to fetch session: ${res.status}`);
    return res.json();
  },
  getPlacement: async (sessionId) => {
    const res = await fetch(`/api/session/${sessionId}/placement`);
    if (!res.ok) throw new Error(`Failed to fetch placement: ${res.status}`);
    return res.json();
  },
  confirmPlacement: async (sessionId, placements) => {
    const res = await fetch(`/api/session/${sessionId}/placement`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ placements }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};

export default function App() {
  const [units, setUnits] = useState([]);
  // log entries are objects: { kind: 'info'|'action'|'check'|'request'|'note'|'sep', text: string }
  const [log, setLog] = useState([]);
  const [file, setFile] = useState(null);
  const [isValidFile, setIsValidFile] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [battleplan, setBattleplan] = useState(null);
  const [battleplans, setBattleplans] = useState([]);
  const [selectedBattleplan, setSelectedBattleplan] = useState("");
  const [rollMode, setRollMode] = useState("ai");
  const [placement, setPlacement] = useState(null);
  const [placementOpen, setPlacementOpen] = useState(false);
  const [chosenZones, setChosenZones] = useState({});
  const [pausedActions, setPausedActions] = useState(null);
  const [rollInputs, setRollInputs] = useState({});
  const [rollModalOpen, setRollModalOpen] = useState(false);
  const [rollValidationErrors, setRollValidationErrors] = useState({});

  const classifyLine = (text) => {
    if (!text) return "info";
    const t = String(text).trim();
    if (/^PLAYER ROLL REQUEST/i.test(t) || /^ROLL REQUEST/i.test(t))
      return "request";
    if (
      /^AI action/i.test(t) ||
      /^AI action resolved/i.test(t) ||
      /^Resolved:/i.test(t)
    )
      return "action";
    if (
      /^Aggression/i.test(t) ||
      /^AI check/i.test(t) ||
      /^Aggression check/i.test(t)
    )
      return "check";
    if (/^Placement confirmed/i.test(t) || /^Note:/i.test(t)) return "note";
    if (t === "") return "sep";
    return "info";
  };

  const appendLog = (line) => {
    const text = line === undefined || line === null ? "" : String(line);
    const kind = classifyLine(text);
    setLog((l) => [...l, { kind, text }]);
  };

  // Append a typed log entry directly (bypass classification)
  const appendTyped = (kind, text) => {
    setLog((l) => [...l, { kind, text }]);
  };

  // Append a block of text to the log with spacing and line splitting for readability.
  const appendBlock = (text) => {
    if (text === undefined || text === null) return;
    const str = String(text);
    const lines = str.split(/\r?\n/).map((s) => s.replace(/\s+$/g, ""));
    setLog((l) => {
      const out = [...l];
      // add a separator before block for readability
      out.push({ kind: "sep", text: "" });
      lines.forEach((ln) => out.push({ kind: classifyLine(ln), text: ln }));
      // small spacer after block
      out.push({ kind: "sep", text: "" });
      return out;
    });
  };

  // Normalize events coming from the server: some responses include objects
  // where the event name isn't in `ev.event` but is indicated by the
  // presence of a key (for example: { aggression_check: true, ... }).
  const normalizeEvent = (ev) => {
    if (!ev || typeof ev !== "object") return ev;
    if (ev.event) return ev;
    if (ev.action_resolved) return { ...ev, event: "action_resolved" };
    if (ev.roll_request) return { ...ev, event: "roll_request" };
    if (
      ev.aggression_check !== undefined ||
      Object.prototype.hasOwnProperty.call(ev, "aggression_check")
    )
      return { ...ev, event: "aggression_check" };
    if (
      (ev.request_id || ev.requestId) &&
      (ev.roll !== undefined || ev.value !== undefined)
    )
      return { ...ev, event: "roll_result" };
    return ev;
  };

  // Format structured events into plain-English sentences for the log.
  const formatEvent = (evIn) => {
    const ev = normalizeEvent(evIn) || evIn;
    if (!ev) return "";
    // If the server already provided a textual summary, prefer it
    if (typeof ev === "string") return ev;
    if (ev.text) return String(ev.text);
    let t = ev.event;
    // Fallback detection when normalizeEvent didn't set event
    if (!t) {
      if (ev.action_resolved) t = "action_resolved";
      else if (ev.roll_request) t = "roll_request";
      else if (
        ev.aggression_check !== undefined ||
        Object.prototype.hasOwnProperty.call(ev, "aggression_check")
      )
        t = "aggression_check";
    }
    try {
      if (t === "action_resolved" && ev.action_resolved) {
        const ar = ev.action_resolved;
        const lines = [];
        lines.push(`AI action: ${ar.unit} -> ${ar.card_title || "(action)"}`);
        if (ar.initiative !== undefined)
          lines.push(`  initiative: ${ar.initiative}`);
        if (ar.behavior) lines.push(`  behavior: ${ar.behavior}`);
        const details = ar.details || {};
        const detailKeys = Object.keys(details || {});
        if (detailKeys.length) {
          lines.push(`  details:`);
          detailKeys.forEach((k) =>
            lines.push(`    ${k}: ${JSON.stringify(details[k])}`)
          );
        }
        return lines.join("\n");
      }

      if (t === "aggression_check") {
        // Render compact needed vs actual. Prefer total if present.
        const needed = ev.target ?? null;
        const actual = ev.total ?? ev.roll ?? null;
        if (needed !== null || actual !== null) {
          return `Need: ${needed ?? "?"}  Roll: ${actual ?? "?"}`;
        }
        return `Aggression check: ${ev.unit} -> ${
          ev.aggression_check ? "ACT" : "HOLD"
        }`;
      }

      if (t === "roll_request") {
        const lines = [];
        lines.push(`ROLL REQUEST (turn ${ev.turn ?? "?"}): ${ev.tactic || ""}`);
        (ev.pending_actions || []).forEach((p) => {
          const dice = p.dice ? `${p.dice.count}d${p.dice.sides}` : "1d6";
          const card = p.card_title || (p.card && p.card.title) || "(action)";
          lines.push(
            `  - [${p.request_id}] ${p.unit} -> ${card} | init=${p.initiative} | roll: ${dice}`
          );
        });
        return lines.join("\n");
      }

      if (t === "placement_confirmed") {
        return `Placement confirmed for turn ${ev.turn || "?"}`;
      }

      if (t === "unit_removed") {
        return `Unit removed: ${ev.unit_name} (${ev.reason || ""})`;
      }

      // Default: render key=value pairs in a readable way
      const kv = Object.keys(ev).map(
        (k) =>
          `${k}: ${typeof ev[k] === "object" ? JSON.stringify(ev[k]) : ev[k]}`
      );
      return kv.join(", ");
    } catch (err) {
      return JSON.stringify(ev);
    }
  };

  // Normalize battleplan title to our filename convention (Title-Case-Hyphens)
  const normalizeBpTitle = (title) => {
    if (!title) return "";
    const stripped = String(title)
      .replace(/\s*\([^)]*\)\s*$/i, "")
      .trim();
    const parts = stripped.split(/[^A-Za-z0-9]+/).filter(Boolean);
    if (parts.length === 0) return stripped;
    return parts
      .map((w) =>
        w.length > 1
          ? w[0].toUpperCase() + w.slice(1).toLowerCase()
          : w.toUpperCase()
      )
      .join("-");
  };

  // Load available battleplans for the dropdown
  useEffect(() => {
    // If we've already loaded battleplans in this module, reuse them.
    if (BATTLEPLANS_CACHE) {
      setBattleplans(BATTLEPLANS_CACHE);
      return;
    }

    (async () => {
      try {
        const data = await api.getBattleplans();
        const plans = data.battleplans || [];
        BATTLEPLANS_CACHE = plans;
        setBattleplans(plans);
      } catch (e) {
        appendLog(`Warn: could not load battleplans: ${e.message}`);
      }
    })();
  }, []);

  const battleplanImageCandidates = useMemo(() => {
    const title = battleplan?.title;
    if (!title) return [];
    const raw = String(title).trim();
    const stripped = raw.replace(/\s*\([^)]*\)\s*$/i, "").trim();
    const baseTitleCase = normalizeBpTitle(raw);
    const strippedTitleCase = normalizeBpTitle(stripped);
    const slug = stripped
      .toLowerCase()
      .replace(/['"]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");

    // Additional variants: underscores, small-words casing, optional 'The' prefix
    const words = stripped.split(/[^A-Za-z0-9]+/).filter(Boolean);
    const small = new Set(["and", "or", "the", "of", "in", "to", "a", "an"]);
    const cap = (w) =>
      w.length > 1
        ? w[0].toUpperCase() + w.slice(1).toLowerCase()
        : w.toUpperCase();
    const titleCase = words.map(cap);
    const titleSmall = words.map((w, i) =>
      i === 0 ? cap(w) : small.has(w.toLowerCase()) ? w.toLowerCase() : cap(w)
    );
    const underTitle = titleCase.join("_");
    const underSmall = titleSmall.join("_");
    const withThe = (s, sep) =>
      s && !/^The[-_]/.test(s) ? `The${sep}${s}` : s;

    // possible filename stems without extension (include 2048x variants)
    const baseStems = [
      baseTitleCase,
      strippedTitleCase,
      underTitle,
      underSmall,
      slug,
    ];
    const thePrefixed = [
      withThe(baseTitleCase, "-"),
      withThe(strippedTitleCase, "-"),
      withThe(underTitle, "_"),
      withThe(underSmall, "_"),
      withThe(slug, "-"),
    ];
    const stems = Array.from(
      new Set(
        [
          ...baseStems,
          ...thePrefixed,
          ...baseStems.map((s) => (s ? `${s}-2048x1524` : s)),
          ...thePrefixed.map((s) => (s ? `${s}-2048x1524` : s)),
        ].filter(Boolean)
      )
    );
    const exts = [".png", ".jpg", ".jpeg", ".webp"]; // prefer PNGs first
    const urls = [];
    for (const stem of stems) {
      for (const ext of exts) {
        urls.push(`/battleplans-media/${stem}${ext}`);
      }
    }
    return urls;
  }, [battleplan]);

  const [bpImgSrc, setBpImgSrc] = useState("");
  useEffect(() => {
    // try candidates in order until one loads
    let cancelled = false;
    (async () => {
      for (const url of battleplanImageCandidates) {
        if (!url) continue;
        try {
          // Attempt a HEAD to see if it exists; fallback to optimistic set and onerror in img
          const ok = await new Promise((resolve) => {
            const img = new Image();
            img.onload = () => resolve(true);
            img.onerror = () => resolve(false);
            img.src = url;
          });
          if (ok) {
            if (!cancelled) setBpImgSrc(url);
            return;
          }
        } catch (_) {}
      }
      if (!cancelled) setBpImgSrc("");
    })();
    return () => {
      cancelled = true;
    };
  }, [battleplanImageCandidates]);

  const onUpload = async () => {
    if (!file) return alert("Choose an HTML roster first");
    // Client-side validation: only allow HTML files
    try {
      const fname = (file.name || "").toLowerCase();
      const isHtmlExt = /\.html?$/.test(fname);
      const isHtmlType = Boolean(file.type && file.type.includes("html"));
      if (!isHtmlExt && !isHtmlType) {
        alert("Please select an HTML file (.html or .htm).");
        setFile(null);
        setIsValidFile(false);
        return;
      }
    } catch (e) {
      // conservative fallback
      alert("Please select a valid HTML file.");
      setFile(null);
      setIsValidFile(false);
      return;
    }
    setBusy(true);
    try {
      // Create a session so we can drive placement via backend
      const created = await api.createSession(
        file,
        rollMode,
        selectedBattleplan ? String(selectedBattleplan) : ""
      );
      const sid = created.session_id;
      setSessionId(sid);
      if (created.battleplan) setBattleplan(created.battleplan);
      appendLog(`Created session ${sid}`);

      // Fetch session to get profiles/units
      try {
        const state = await api.getSession(sid);
        const profiles = state.ai_profiles || [];
        setUnits(
          profiles.map((p) => ({
            name: p.name,
            models: p.models,
            wounds_per_model: p.wounds_per_model,
          }))
        );
        appendLog(`Loaded ${profiles.length} AI units`);
      } catch (e) {
        // Non-fatal if session fetch fails
        appendLog(`Warn: could not fetch session: ${e.message}`);
      }

      // Try to get placement and have AI auto-pick deployment
      try {
        const pl = await api.getPlacement(sid);
        const proposed = pl.placement;
        const confirmed = pl.confirmed;
        if (proposed) {
          setPlacement(proposed);
          // Build AI-chosen zones from suggestions (fallback to first allowed)
          const aiChosen = {};
          const placements = (proposed.suggestions || []).map((s) => {
            const zone =
              s.suggested_zone || (proposed.allowed_zones?.[0] ?? "");
            if (s.unit) aiChosen[s.unit] = zone;
            return { unit: s.unit, zone };
          });
          setChosenZones(aiChosen);
          // If server hasn't already confirmed, confirm automatically
          if (!confirmed) {
            try {
              await api.confirmPlacement(sid, placements);
              appendLog(
                `AI deployment auto-confirmed for session ${sid} based on battleplan.`
              );
            } catch (err) {
              const msg = String(err);
              if (msg.includes("placement_already_auto_confirmed")) {
                appendLog("Placement already confirmed by server.");
              } else {
                appendLog("Warn: failed to auto-confirm placement: " + msg);
              }
            }
          } else {
            appendLog("Placement was auto-confirmed by server.");
          }
          // Show a read-only summary modal of the AI's deployment
          setPlacementOpen(true);
          if (created.battleplan) setBattleplan(created.battleplan);
          if (confirmed && confirmed.by === "server") {
            appendLog(
              "Note: placement auto-confirmed by server; showing summary."
            );
          }
        } else {
          appendLog("No placement proposed by server.");
        }
      } catch (e) {
        appendLog(`Warn: could not fetch placement: ${e.message}`);
      }
    } catch (e) {
      alert(e.message);
    } finally {
      setBusy(false);
      // Keep file selection but reset validity after upload to require re-validation
      setIsValidFile(false);
    }
  };

  const handleFileChange = (e) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    if (!f) {
      setIsValidFile(false);
      return;
    }
    const name = (f.name || "").toLowerCase();
    const isHtmlExt = /\.html?$/.test(name);
    const isHtmlType = Boolean(f.type && f.type.includes("html"));
    setIsValidFile(isHtmlExt || isHtmlType);
  };

  const onRun = async () => {
    setBusy(true);
    try {
      const minimalUnits = units.map((u) => ({
        name: u.name,
        models: u.models ?? 1,
      }));
      const data = await api.runSimulation(minimalUnits, 3, 2);
      appendBlock("Simulation events:");
      (data.events || []).forEach((ev) => {
        const n = normalizeEvent(ev) || ev;
        if (n && n.event === "aggression_check") {
          appendTyped("check", {
            unit: n.unit || null,
            needed: n.target ?? null,
            actual: n.total ?? n.roll ?? null,
            raw: n,
          });
        } else if (n && (n.event === "roll_result" || n.event === "roll")) {
          appendTyped("roll", {
            unit: n.unit || null,
            card: n.card_title || (n.card && n.card.title) || null,
            needed: n.target ?? n.required ?? null,
            actual: n.roll ?? n.value ?? null,
            request_id: n.request_id ?? null,
            raw: n,
          });
        } else {
          appendBlock(formatEvent(n));
        }
      });
    } catch (e) {
      alert(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 antialiased">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
        <div className="container-max py-4">
          <h1 className="text-2xl font-semibold tracking-tight">
            Sad Hammer — Frontend
          </h1>
          <p className="text-slate-300 text-sm">
            Upload a BattleScribe HTML roster and run a simulated AI turn.
          </p>
          <div className="mt-2 text-xs text-slate-400">
            Session: <span id="session-id">{sessionId || "(none)"}</span>
          </div>
        </div>
      </header>

      <main className="container-max py-6">
        <section className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
          <label className="inline-flex items-center gap-3">
            <input
              id="roster-file"
              aria-label="Roster HTML"
              type="file"
              accept=".html,.htm,text/html"
              className="input"
              onChange={handleFileChange}
            />
          </label>
          <div className="flex items-center gap-2">
            <label
              htmlFor="battleplan-select"
              className="text-sm text-slate-300"
            >
              Battleplan:
            </label>
            <select
              id="battleplan-select"
              className="input"
              value={selectedBattleplan}
              onChange={(e) => setSelectedBattleplan(e.target.value)}
            >
              <option value="">Random</option>
              {battleplans.map((bp) => (
                <option key={bp.id} value={bp.id}>
                  {bp.title}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="roll-mode" className="text-sm text-slate-300">
              Roll mode:
            </label>
            <select
              id="roll-mode"
              className="input"
              value={rollMode}
              onChange={(e) => setRollMode(e.target.value)}
            >
              <option value="ai">AI handles rolls</option>
              <option value="player">Player rolls (enter dice)</option>
            </select>
          </div>
          <div className="flex gap-2">
            <button
              id="create-session"
              onClick={onUpload}
              disabled={busy || !isValidFile}
              className="btn-primary"
            >
              Upload & Parse
            </button>
            <button
              id="run-ai-turn"
              onClick={async () => {
                setBusy(true);
                // Ensure we have a session id to operate on; if not, create one inline
                let sidToUse = sessionId;
                if (!sidToUse) {
                  try {
                    const created = await api.createSession(
                      file,
                      rollMode,
                      selectedBattleplan ? String(selectedBattleplan) : ""
                    );
                    sidToUse = created.session_id;
                    setSessionId(sidToUse);
                    if (created.battleplan) setBattleplan(created.battleplan);
                    appendLog(`Created session ${sidToUse}`);
                  } catch (e) {
                    alert(e.message);
                    setBusy(false);
                    return;
                  }
                }

                if (!sidToUse) {
                  alert("No session available to run AI turn");
                  setBusy(false);
                  return;
                }

                // Run the AI turn via the API. Server may set paused turn state (roll_request)
                try {
                  await api.runAiTurn(sidToUse);
                  // fetch structured last_turn events to show the turn details
                  const last = await api.getLastTurn(sidToUse);
                  const events = last.events || [];

                  // Determine the turn number (if present) and append header so player knows which turn.
                  const inferredTurn =
                    events.find((e) => e && e.turn !== undefined)?.turn ??
                    events.find(
                      (e) => e && e.action_resolved && e.action_resolved.turn
                    )?.action_resolved.turn;
                  if (inferredTurn !== undefined) {
                    appendTyped("turn", `=== AI Turn ${inferredTurn} ===`);
                  }

                  // If there's a roll_request present (player-mode), show a request block.
                  const rr = events.find((ev) => ev.event === "roll_request");
                  if (
                    rr &&
                    rr.pending_actions &&
                    rr.pending_actions.length > 0
                  ) {
                    // Append any aggression checks first
                    events
                      .filter((ev) => ev.event === "aggression_check")
                      .forEach((ac) =>
                        appendTyped("check", {
                          unit: ac.unit,
                          needed: ac.target ?? null,
                          actual: ac.total ?? ac.roll ?? null,
                          raw: ac,
                        })
                      );

                    // Show the player roll request instructions (keeps previous behavior)
                    const pending = rr.pending_actions || [];
                    setPausedActions(pending);
                    setRollModalOpen(true);
                    appendLog("");
                    appendLog("=== PLAYER ROLL REQUEST ===");
                    appendLog(
                      "Please roll the required dice physically and enter each result in the dialog:"
                    );
                    pending.forEach((p) => {
                      const dice = p.dice
                        ? `${p.dice.count}d${p.dice.sides}`
                        : "1d6";
                      const card =
                        p.card_title || (p.card && p.card.title) || "(action)";
                      appendLog(
                        `  • [${p.request_id}] ${p.unit} -> ${card}  |  init=${p.initiative}  |  roll: ${dice}`
                      );
                    });
                    appendLog("");
                  } else {
                    // No pause: present the events in ordered groups: checks -> rolls -> actions
                    const checks = [];
                    const rolls = [];
                    const actions = [];
                    const others = [];
                    events.forEach((ev) => {
                      if (ev.event === "aggression_check") checks.push(ev);
                      else if (
                        ev.event === "roll_result" ||
                        ev.event === "roll"
                      )
                        rolls.push(ev);
                      else if (
                        ev.event === "action_resolved" &&
                        ev.action_resolved
                      )
                        actions.push(ev);
                      else others.push(ev);
                    });

                    checks.forEach((ac) =>
                      appendTyped("check", {
                        unit: ac.unit,
                        needed: ac.target ?? null,
                        actual: ac.total ?? ac.roll ?? null,
                        raw: ac,
                      })
                    );

                    rolls.forEach((r) => {
                      appendTyped("roll", {
                        unit: r.unit || null,
                        card: r.card_title || (r.card && r.card.title) || null,
                        needed: r.target ?? r.required ?? null,
                        actual: r.roll ?? r.value ?? null,
                        request_id: r.request_id ?? null,
                        raw: r,
                      });
                    });

                    actions.forEach((ev) => {
                      const ar = ev.action_resolved;
                      const details = ar.details || {};
                      const detailLines = Object.keys(details || {}).map(
                        (k) => `    ${k}: ${JSON.stringify(details[k])}`
                      );
                      const block = [
                        `AI action: ${ar.unit} -> ${
                          ar.card_title || "(action)"
                        }`,
                        `  initiative: ${ar.initiative || ""}`,
                        `  behavior: ${ar.behavior || ""}`,
                        ...(detailLines.length
                          ? ["  details:", ...detailLines]
                          : []),
                      ].join("\n");
                      appendBlock(block);
                    });

                    // Anything else: render via formatEvent, but normalize checks/rolls to structured entries first
                    others.forEach((ev) => {
                      const n = normalizeEvent(ev) || ev;
                      if (n && n.event === "aggression_check") {
                        appendTyped("check", {
                          unit: n.unit || null,
                          needed: n.target ?? null,
                          actual: n.total ?? n.roll ?? null,
                          raw: n,
                        });
                      } else if (
                        n &&
                        (n.event === "roll_result" || n.event === "roll")
                      ) {
                        appendTyped("roll", {
                          unit: n.unit || null,
                          card:
                            n.card_title || (n.card && n.card.title) || null,
                          needed: n.target ?? n.required ?? null,
                          actual: n.roll ?? n.value ?? null,
                          request_id: n.request_id ?? null,
                          raw: n,
                        });
                      } else {
                        appendBlock(formatEvent(n));
                      }
                    });
                  }
                } catch (e) {
                  appendLog(`Warn: failed to run AI turn: ${e.message}`);
                } finally {
                  setBusy(false);
                }
              }}
              disabled={busy || units.length === 0}
              className="btn-success"
            >
              Run AI Turn
            </button>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="card md:col-span-1">
            <div className="card-header">
              <h2 className="card-title">Units</h2>
            </div>
            <div className="max-h-[480px] overflow-auto px-4 py-3">
              {units.length === 0 ? (
                <p className="text-sm text-slate-300">No units loaded yet.</p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {units.map((u, i) => (
                    <li key={i}>
                      {u.name} — {u.models} models
                      {u.wounds_per_model
                        ? `, ${u.wounds_per_model} wpmodel`
                        : ""}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="card md:col-span-2">
            <div className="card-header">
              <h2 className="card-title">Log</h2>
            </div>
            <div className="px-4 py-3">
              <div className="max-h-[480px] overflow-auto text-sm font-mono">
                {log.map((entry, i) => {
                  const key = `log-${i}`;
                  if (!entry) return null;
                  const { kind, text } = entry;
                  // small condensed style for checks
                  if (kind === "check") {
                    // support structured check entries: { unit, needed, actual, raw_roll, modifier }
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
                          <div className="text-xs text-slate-400">
                            Aggression check
                          </div>
                          <div className={`${cls} text-sm font-semibold`}>
                            {unitLabel}Need: {needed ?? "?"} &nbsp; Roll:{" "}
                            {actual ?? "?"}
                          </div>
                        </div>
                      );
                    }
                    return (
                      <div
                        key={key}
                        className="text-slate-100 leading-tight text-sm mb-0.5"
                      >
                        {text}
                      </div>
                    );
                  }
                  if (kind === "roll") {
                    // structured roll object is handled similarly to checks
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
                          <div className="text-xs text-slate-400">
                            Roll result
                          </div>
                          <div className={`${cls} text-sm font-semibold`}>
                            {unitLabel}Need: {needed ?? "?"} &nbsp; Roll:{" "}
                            {actual ?? "?"}
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
                  if (kind === "turn") {
                    return (
                      <div
                        key={key}
                        className="text-slate-200 text-sm font-semibold text-center my-2"
                      >
                        {text}
                      </div>
                    );
                  }
                  // roll results (player-entered or resolved dice)
                  if (kind === "roll") {
                    // support structured roll entries: { unit, card, needed, actual }
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
                      const targetLabel = `Target: ${needed ?? "?"}`;
                      const rollLabel = `Roll: ${actual ?? "?"}`;
                      return (
                        <div key={key} className={`${cls} text-xs my-1`}>
                          {unitLabel}
                          {targetLabel} {rollLabel}
                        </div>
                      );
                    }
                    return (
                      <div key={key} className="text-rose-400 text-xs my-1">
                        {text}
                      </div>
                    );
                  }
                  if (kind === "action") {
                    return (
                      <div
                        key={key}
                        className="text-amber-300 font-semibold my-2"
                      >
                        {text}
                      </div>
                    );
                  }
                  if (kind === "request") {
                    return (
                      <div
                        key={key}
                        className="text-cyan-300 font-semibold my-3"
                      >
                        {text}
                      </div>
                    );
                  }
                  if (kind === "sep") {
                    return <div key={key} className="h-2" />;
                  }
                  if (kind === "note") {
                    return (
                      <div key={key} className="text-slate-300 italic my-1">
                        {text}
                      </div>
                    );
                  }
                  return (
                    <div key={key} className="text-slate-200 my-1">
                      {text}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </section>
      </main>

      {placementOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-slate-900/80 backdrop-blur-sm"
            onClick={() => setPlacementOpen(false)}
          />
          <div className="relative z-10 w-full max-w-4xl max-h-[85vh] rounded-lg border border-slate-800 bg-slate-800 shadow-lg flex flex-col">
            <div className="flex items-start justify-between px-4 py-3 border-b border-slate-700 shrink-0">
              <div>
                <h3 className="text-lg font-semibold">AI Deployment</h3>
                <p className="text-sm text-slate-300">
                  The uploaded roster is the enemy AI. Deployment has been
                  auto-picked based on the battleplan:{" "}
                  {battleplan?.title || "Unknown"}
                </p>
              </div>
            </div>
            <div
              id="placement-modal-body"
              className="flex-1 min-h-0 overflow-y-auto p-4"
            >
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-3" id="placement-summary">
                  <div className="rounded border border-slate-700 p-3">
                    <div className="text-sm text-slate-300">Allowed zones</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {(placement?.allowed_zones || []).map((z) => (
                        <span
                          key={z}
                          className="rounded bg-slate-700 px-2 py-1 text-xs uppercase tracking-wide"
                        >
                          {z}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="max-h-[420px] overflow-auto rounded border border-slate-700">
                    <table className="w-full text-sm" id="placement-panel">
                      <thead className="sticky top-0 bg-slate-700/60">
                        <tr>
                          <th className="px-3 py-2 text-left font-semibold">
                            Unit
                          </th>
                          <th className="px-3 py-2 text-left font-semibold">
                            Zone (AI-chosen)
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {(placement?.suggestions || []).map((s) => (
                          <tr
                            key={s.unit}
                            className="border-t border-slate-700"
                          >
                            <td className="px-3 py-2">{s.unit}</td>
                            <td className="px-3 py-2 text-slate-300">
                              {chosenZones[s.unit] || s.suggested_zone || "-"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div className="space-y-3">
                  <div
                    className="rounded border border-slate-700 p-3"
                    id="placement-map"
                  >
                    <div className="mb-2 text-sm font-semibold">
                      Deployment map
                    </div>
                    {bpImgSrc ? (
                      <img
                        src={bpImgSrc}
                        alt="Battleplan map"
                        className="max-h-[360px] w-full rounded object-contain"
                      />
                    ) : (
                      <div className="text-sm text-slate-300">
                        No map image found. Use the grid below as a guide.
                      </div>
                    )}
                  </div>
                  <div className="rounded border border-slate-700 p-3">
                    <div className="mb-2 text-sm font-semibold">
                      Placement instructions
                    </div>
                    <div className="space-y-3">
                      {(placement?.suggestions || []).map((s) => {
                        const zone = (
                          chosenZones[s.unit] ||
                          s.suggested_zone ||
                          ""
                        ).toLowerCase();
                        const zoneLabel =
                          zone || placement?.allowed_zones?.[0] || "—";
                        const zoneHint =
                          s.zone_hint || (zone ? `Place in ${zone}` : "");
                        const coord = s.coordinate_hint || "";
                        const dist = s.distance_range || "";
                        const prio = s.priority || "";
                        const reason = s.reason || "";
                        return (
                          <div
                            key={`inst-${s.unit}`}
                            className="rounded border border-slate-700 bg-slate-900/40 p-3"
                          >
                            <div className="flex items-baseline justify-between gap-2">
                              <div className="text-base font-semibold">
                                {s.unit}
                              </div>
                              <div className="text-xs uppercase tracking-wide text-slate-300">
                                Zone: {zoneLabel}
                              </div>
                            </div>
                            <div className="mt-1 text-sm text-slate-200">
                              {zoneHint}
                            </div>
                            {coord ? (
                              <div className="mt-1 text-xs text-slate-300">
                                {coord}
                              </div>
                            ) : null}
                            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                              {dist ? (
                                <span className="rounded bg-slate-800 px-2 py-1">
                                  Distance: {dist}
                                </span>
                              ) : null}
                              {prio ? (
                                <span className="rounded bg-slate-800 px-2 py-1">
                                  Priority: {prio}
                                </span>
                              ) : null}
                              {reason ? (
                                <span className="rounded bg-slate-800 px-2 py-1">
                                  {reason}
                                </span>
                              ) : null}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-slate-700 px-4 py-3 shrink-0">
              <button
                className="btn-primary"
                onClick={() => setPlacementOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      {rollModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setRollModalOpen(false)}
          />
          <div className="relative z-10 w-full max-w-2xl rounded-lg border border-slate-800 bg-slate-800 p-4">
            <h3 className="text-lg font-semibold">Enter Dice Results</h3>
            <p className="text-sm text-slate-300">
              Enter physical dice rolls for the AI pending actions.
            </p>
            <div className="mt-3 space-y-3 max-h-[60vh] overflow-auto">
              {(pausedActions || []).map((a) => {
                const err = rollValidationErrors[a.request_id];
                return (
                  <div
                    key={a.request_id}
                    className="rounded border border-slate-700 p-3"
                  >
                    <div className="font-semibold">
                      {a.unit} —{" "}
                      {a.card_title || (a.card && a.card.title) || "Action"}
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      <label className="text-xs text-slate-300">
                        Roll (d6):
                      </label>
                      <input
                        type="number"
                        min={1}
                        max={6}
                        className="input w-24"
                        value={rollInputs[a.request_id] ?? ""}
                        onChange={(e) => {
                          const val = e.target.value;
                          setRollInputs((r) => ({ ...r, [a.request_id]: val }));
                          const n = Number(val);
                          setRollValidationErrors((errs) => ({
                            ...errs,
                            [a.request_id]:
                              !Number.isInteger(n) || n < 1 || n > 6,
                          }));
                        }}
                      />
                      {err ? (
                        <div className="text-xs text-rose-400 ml-2">
                          Enter a whole number between 1 and 6
                        </div>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                className="btn-secondary"
                onClick={() => setRollModalOpen(false)}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={async () => {
                  // Build action results array from rollInputs
                  const results = (pausedActions || []).map((a) => ({
                    request_id: a.request_id,
                    result: { roll: Number(rollInputs[a.request_id] || 0) },
                  }));
                  try {
                    const res = await api.resolveRolls(sessionId, results);
                    // Prefer to present checks first (white), then rolls (red small), then actions (yellow)
                    if (res && Array.isArray(res.events)) {
                      const inferredTurn =
                        res.events.find((e) => e && e.turn !== undefined)
                          ?.turn ??
                        res.events.find(
                          (e) =>
                            e && e.action_resolved && e.action_resolved.turn
                        )?.action_resolved.turn;
                      if (inferredTurn !== undefined)
                        appendTyped("turn", `=== AI Turn ${inferredTurn} ===`);
                      // normalize incoming events so shapes are consistent
                      const norm = res.events.map(
                        (e) => normalizeEvent(e) || e
                      );
                      // collect ordered lists
                      const checks = [];
                      const rolls = [];
                      const actions = [];
                      norm.forEach((ev) => {
                        if (ev.event === "aggression_check") checks.push(ev);
                        else if (
                          ev.event === "roll_result" ||
                          ev.event === "roll"
                        )
                          rolls.push(ev);
                        else if (
                          ev.event === "action_resolved" &&
                          ev.action_resolved
                        )
                          actions.push(ev);
                        else actions.push(ev);
                      });

                      // Append checks (white, compact)
                      checks.forEach((ac) => {
                        const line = `Aggression: ${ac.unit} -> ${
                          ac.aggression_check ? "ACT" : "HOLD"
                        }  (d6=${ac.roll ?? "?"} + mod=${
                          ac.modifier ?? 0
                        } => total=${ac.total ?? "?"} vs target=${
                          ac.target ?? "?"
                        })`;
                        appendTyped("check", line);
                      });

                      // Append explicit per-request roll results (red, small)
                      rolls.forEach((r) => {
                        appendTyped("roll", {
                          unit: r.unit || null,
                          card:
                            r.card_title || (r.card && r.card.title) || null,
                          needed: r.target ?? r.required ?? null,
                          actual: r.roll ?? r.value ?? null,
                          request_id: r.request_id ?? null,
                          raw: r,
                        });
                      });

                      // Append actions (yellow)
                      actions.forEach((ev) => {
                        if (
                          ev.event === "action_resolved" &&
                          ev.action_resolved
                        ) {
                          const ar = ev.action_resolved;
                          const details = ar.details || {};
                          const detailLines = Object.keys(details || {}).map(
                            (k) => `    ${k}: ${JSON.stringify(details[k])}`
                          );
                          const block = [
                            `AI action: ${ar.unit} -> ${
                              ar.card_title || "(action)"
                            }`,
                            `  initiative: ${ar.initiative || ""}`,
                            `  behavior: ${ar.behavior || ""}`,
                            ...(detailLines.length
                              ? ["  details:", ...detailLines]
                              : []),
                          ].join("\n");
                          // append as a block so classification picks it up as 'action'
                          appendBlock(block);
                        } else {
                          appendBlock(formatEvent(ev));
                        }
                      });
                    } else {
                      appendBlock("Resolved rolls (no events returned)");
                    }

                    // After resolving rolls, fetch the last turn to run remaining server logic and show events
                    try {
                      const last = await api.getLastTurn(sessionId);
                      (last.events || []).forEach((ev) => {
                        const n = normalizeEvent(ev) || ev;
                        if (n && n.event === "aggression_check") {
                          appendTyped("check", {
                            unit: n.unit || null,
                            needed: n.target ?? null,
                            actual: n.total ?? n.roll ?? null,
                            raw: n,
                          });
                        } else if (
                          n &&
                          (n.event === "roll_result" || n.event === "roll")
                        ) {
                          appendTyped("roll", {
                            unit: n.unit || null,
                            card:
                              n.card_title || (n.card && n.card.title) || null,
                            needed: n.target ?? n.required ?? null,
                            actual: n.roll ?? n.value ?? null,
                            request_id: n.request_id ?? null,
                            raw: n,
                          });
                        } else {
                          appendBlock(formatEvent(n));
                        }
                      });
                    } catch (err) {
                      appendBlock(
                        "Warn: could not fetch last turn: " + String(err)
                      );
                    }
                    // Clear paused state and inputs
                    setPausedActions(null);
                    setRollInputs({});
                    setRollValidationErrors({});
                    setRollModalOpen(false);
                  } catch (err) {
                    // Try to show a friendly server error if it's JSON
                    const msg = String(err);
                    try {
                      const parsed = JSON.parse(msg);
                      if (parsed && parsed.error) {
                        const rid = parsed.request_id
                          ? ` request=${parsed.request_id}`
                          : "";
                        const field = parsed.field
                          ? ` field=${parsed.field}`
                          : "";
                        const val =
                          parsed.value !== undefined
                            ? ` value=${parsed.value}`
                            : "";
                        appendLog(
                          `Roll rejected: ${parsed.error}${rid}${field}${val}`
                        );
                      } else {
                        appendLog("Warn: failed to resolve rolls: " + msg);
                      }
                    } catch (parseErr) {
                      // Not JSON, just log the message
                      appendLog("Warn: failed to resolve rolls: " + msg);
                    }
                  }
                }}
                disabled={
                  // disabled if any paused action is missing a valid roll
                  (pausedActions || []).some(
                    (a) =>
                      rollValidationErrors[a.request_id] ||
                      !rollInputs[a.request_id]
                  )
                }
              >
                Submit Rolls
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
