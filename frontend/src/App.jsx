import React, { useEffect, useMemo, useState } from "react";
import Header from "./components/Header";
import ClientControls from "./components/ClientControls";
import UploadModal from "./components/UploadModal";
import UnitsList from "./components/UnitsList";
import PlacementModal from "./components/PlacementModal";
import RollModal from "./components/RollModal";
import Log from "./components/Log";

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
  // (sessionful APIs removed — stateless endpoints below are used)
  // Stateless endpoints (derived-seed per-turn)
  createSessionStateless: async (file, rollMode = "ai", battleplan = "") => {
    const fd = new FormData();
    if (file) fd.append("file", file);
    fd.append("roll_mode", rollMode);
    if (battleplan) fd.append("battleplan", String(battleplan));
    const res = await fetch(`/api/session_stateless`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok)
      throw new Error(`Failed to create stateless session: ${res.status}`);
    return res.json();
  },
  aiTurnStateless: async ({
    seed,
    turn,
    ai_units,
    roll_mode = "ai",
    battleplan = null,
  }) => {
    const res = await fetch(`/api/ai_turn_stateless`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed, turn, ai_units, roll_mode, battleplan }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  resolveRollsStateless: async ({
    seed,
    turn,
    pending_actions,
    action_results,
  }) => {
    const res = await fetch(`/api/resolve_rolls_stateless`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed, turn, pending_actions, action_results }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  removeUnitStateless: async ({ ai_units, unit_name, turn = null }) => {
    const res = await fetch(`/api/remove_unit_stateless`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ai_units, unit_name, turn }),
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
  // client-run controls — app is stateless and uses derived seed/turn
  const [battleplan, setBattleplan] = useState(null);
  const [battleplans, setBattleplans] = useState([]);
  const [selectedBattleplan, setSelectedBattleplan] = useState("");
  const [rollMode, setRollMode] = useState("ai");
  const [placement, setPlacement] = useState(null);
  const [placementOpen, setPlacementOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [chosenZones, setChosenZones] = useState({});
  const [seed, setSeed] = useState(null);
  const [turn, setTurn] = useState(1);
  const [pausedActions, setPausedActions] = useState(null);
  const [rollInputs, setRollInputs] = useState({});
  const [rollModalOpen, setRollModalOpen] = useState(false);
  const [rollValidationErrors, setRollValidationErrors] = useState({});
  const [collapsedTurns, setCollapsedTurns] = useState({});

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
    setLog((l) => {
      const idx = l.length; // index of the new entry
      const out = [...l, { kind, text }];
      // If we're appending a new 'turn' header, auto-collapse previous turns and
      // ensure the new turn is expanded by default.
      if (kind === "turn") {
        setCollapsedTurns((prev) => {
          const next = { ...(prev || {}) };
          // mark any previously-seen turn indices as collapsed
          out.forEach((e, i) => {
            if (i === idx) return; // skip the new turn we want expanded
            if (e && e.kind === "turn") next[i] = true;
          });
          // ensure the new turn index is explicitly expanded
          next[idx] = false;
          return next;
        });
      }
      return out;
    });
  };

  // Ensure a turn header exists in the log for the given turn number.
  // This appends the header only if the most recent 'turn' header isn't
  // already the same, avoiding duplicates when both aiTurn and resolve
  // paths may attempt to add the header.
  const ensureTurnHeader = (turnNumber) => {
    if (turnNumber === undefined || turnNumber === null) return;
    const header = `=== AI Turn ${turnNumber} ===`;
    // find the most recent 'turn' entry in the log
    if (Array.isArray(log)) {
      for (let i = log.length - 1; i >= 0; i--) {
        const e = log[i];
        if (!e) continue;
        if (e.kind === "turn") {
          if (e.text === header) return; // already present
          break; // different turn header found, fall through to append
        }
      }
    }
    appendTyped("turn", header);
  };

  // Allow player to remove an enemy unit (call server endpoint and update UI)
  const handleRemoveUnit = async (unitName) => {
    if (!confirm(`Remove unit ${unitName} from the battle?`)) return;
    setBusy(true);
    try {
      // Use stateless removal: send current AI units to server to compute remaining list
      const ai_payload = (units || []).map((u) => ({
        name: u.name,
        aggression: u.aggression,
      }));
      const res = await api.removeUnitStateless({
        ai_units: ai_payload,
        unit_name: unitName,
        turn,
      });
      // Update UI from returned remaining_units
      const rem = res.remaining_units || [];
      setUnits(
        rem.map((r) => ({
          name: r.name,
          models: r.models || 1,
          aggression: r.aggression,
        }))
      );
      appendTyped("note", `Player removed unit: ${unitName}`);
    } catch (err) {
      appendLog(`Warn: failed to remove unit: ${String(err)}`);
    } finally {
      setBusy(false);
    }
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
      // Create a stateless session and receive a seed and initial AI units/profiles
      const created = await api.createSessionStateless(
        file,
        rollMode,
        selectedBattleplan ? String(selectedBattleplan) : ""
      );
      const s = created.seed;
      setSeed(s);
      if (created.battleplan) setBattleplan(created.battleplan);
      appendLog(`Created stateless session with seed ${s}`);

      // set units from ai_profiles
      const profiles = created.state?.ai_profiles || [];
      setUnits(
        profiles.map((p) => ({
          name: p.name,
          models: p.models,
          wounds_per_model: p.wounds_per_model,
          aggression: p.aggression,
        }))
      );
      appendLog(`Loaded ${profiles.length} AI units`);

      // If placement proposed, show and auto-confirm locally (stateless)
      try {
        const proposed = created.proposed_placement;
        if (proposed) {
          // If the server included battleplan info inside the proposed placement,
          // ensure our top-level battleplan state is set so the modal can show the name.
          if (!battleplan && proposed.battleplan) {
            setBattleplan(proposed.battleplan);
          }
          setPlacement(proposed);
          const aiChosen = {};
          const placements = (proposed.suggestions || []).map((sug) => {
            const zone =
              sug.suggested_zone || (proposed.allowed_zones?.[0] ?? "");
            if (sug.unit) aiChosen[sug.unit] = zone;
            return { unit: sug.unit, zone };
          });
          setChosenZones(aiChosen);
          setPlacementOpen(true);
          appendLog("Placement proposed by server (stateless);");
        }
      } catch (e) {
        appendLog(`Warn: could not process proposed placement: ${e.message}`);
      }
    } catch (e) {
      // Stateless endpoint failed — surface a clear error and abort. Sessions are removed.
      alert(
        `Failed to initialize stateless session: ${
          e.message || String(e)
        }.\nThis client requires the stateless API. Ensure the backend exposes /api/session_stateless.`
      );
      appendLog(`Error: failed to create stateless session: ${e.message}`);
      setBusy(false);
      setIsValidFile(false);
      return;
    } finally {
      setBusy(false);
      // Keep file selection but reset validity after upload to require re-validation
      setIsValidFile(false);
    }
  };

  // Trigger the hidden file input to open the OS file picker
  const handleChoose = () => {
    const el = document.getElementById("upload-file");
    if (el) el.click();
  };

  // Handle file selection (validate HTML extension/type)
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

  const handleRunAiTurn = async () => {
    setBusy(true);
    try {
      // Require stateless seed — the app is stateless-only now
      if (!seed) {
        alert(
          "No seed available: upload a roster first to initialize a stateless session."
        );
        setBusy(false);
        return;
      }

      // Call the stateless ai_turn endpoint
      {
        const ai_payload = (units || []).map((u) => ({
          name: u.name,
          aggression: u.aggression,
        }));
        const resp = await api.aiTurnStateless({
          seed,
          turn,
          ai_units: ai_payload,
          roll_mode: rollMode,
          battleplan: selectedBattleplan,
        });
        const events = resp.events || [];
        const pending = resp.pending_actions || [];

        const rr =
          events.find((ev) => ev.event === "roll_request") ||
          (pending.length
            ? {
                event: "roll_request",
                pending_actions: pending,
                turn: resp.turn,
              }
            : null);

        const inferredTurn =
          resp.turn ?? events.find((e) => e && e.turn !== undefined)?.turn;
        // Always ensure the turn header is present immediately so the UI
        // looks identical between AI-controlled and player-controlled
        // roll modes. Only advance the local turn counter when there are
        // no pending player actions; if there are pending actions the
        // header stays visible and the remainder of the events will be
        // printed after the player resolves their rolls.
        if (inferredTurn !== undefined) {
          ensureTurnHeader(inferredTurn);
          if (!(rr && rr.pending_actions && rr.pending_actions.length > 0)) {
            setTurn(inferredTurn + 1);
          }
        }
        if (rr && rr.pending_actions && rr.pending_actions.length > 0) {
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

          const pendingActions = rr.pending_actions || [];
          setPausedActions(pendingActions);
          setRollModalOpen(true);
          appendLog("");
          appendLog("=== PLAYER ROLL REQUEST ===");
          appendLog(
            "Please roll the required dice physically and enter each result in the dialog:"
          );
          pendingActions.forEach((p) => {
            const dice = p.dice ? `${p.dice.count}d${p.dice.sides}` : "1d6";
            const card = p.card_title || (p.card && p.card.title) || "(action)";
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
            else if (ev.event === "roll_result" || ev.event === "roll")
              rolls.push(ev);
            else if (ev.event === "action_resolved" && ev.action_resolved)
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
              `AI action: ${ar.unit} -> ${ar.card_title || "(action)"}`,
              `  initiative: ${ar.initiative || ""}`,
              `  behavior: ${ar.behavior || ""}`,
              ...(detailLines.length ? ["  details:", ...detailLines] : []),
            ].join("\n");
            appendBlock(block);
          });

          others.forEach((ev) => {
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
        }

        setBusy(false);
        return;
      }

      // Determine the turn number (if present) and append header so player knows which turn.
      const inferredTurn =
        events.find((e) => e && e.turn !== undefined)?.turn ??
        events.find((e) => e && e.action_resolved && e.action_resolved.turn)
          ?.action_resolved.turn;
      if (inferredTurn !== undefined) {
        appendTyped("turn", `=== AI Turn ${inferredTurn} ===`);
      }

      // If there's a roll_request present (player-mode), show a request block.
      const rr = events.find((ev) => ev.event === "roll_request");
      if (rr && rr.pending_actions && rr.pending_actions.length > 0) {
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
          const dice = p.dice ? `${p.dice.count}d${p.dice.sides}` : "1d6";
          const card = p.card_title || (p.card && p.card.title) || "(action)";
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
          else if (ev.event === "roll_result" || ev.event === "roll")
            rolls.push(ev);
          else if (ev.event === "action_resolved" && ev.action_resolved)
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
            `AI action: ${ar.unit} -> ${ar.card_title || "(action)"}`,
            `  initiative: ${ar.initiative || ""}`,
            `  behavior: ${ar.behavior || ""}`,
            ...(detailLines.length ? ["  details:", ...detailLines] : []),
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
      }
    } catch (e) {
      appendLog(`Warn: failed to run AI turn: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 antialiased">
      <Header />

      <main className="container-max py-6">
        <ClientControls
          file={file}
          onFileChange={handleFileChange}
          onUpload={onUpload}
          openUploadModal={uploadOpen}
          setOpenUploadModal={setUploadOpen}
          battleplans={battleplans}
          selectedBattleplan={selectedBattleplan}
          setSelectedBattleplan={setSelectedBattleplan}
          rollMode={rollMode}
          setRollMode={setRollMode}
          onRunAiTurn={handleRunAiTurn}
          units={units}
          busy={busy}
        />

        <UploadModal
          open={uploadOpen}
          onClose={() => setUploadOpen(false)}
          onFileChange={handleFileChange}
          onUpload={async () => {
            await onUpload();
            // close modal once upload completes
            setUploadOpen(false);
          }}
          busy={busy}
          battleplans={battleplans}
          selectedBattleplan={selectedBattleplan}
          setSelectedBattleplan={setSelectedBattleplan}
          rollMode={rollMode}
          setRollMode={setRollMode}
        />

        <section className="grid grid-cols-1 gap-4 md:grid-cols-3 items-start">
          <UnitsList
            units={units}
            onRemove={handleRemoveUnit}
            collapsible={true}
          />

          <div className="card md:col-span-2">
            <div className="card-header">
              <h2 className="card-title">Log</h2>
            </div>
            <div className="px-4 py-3">
              <Log
                log={log}
                collapsedTurns={collapsedTurns}
                setCollapsedTurns={setCollapsedTurns}
              />
            </div>
          </div>
        </section>
      </main>

      <PlacementModal
        open={placementOpen}
        placement={placement}
        chosenZones={chosenZones}
        bpImgSrc={bpImgSrc}
        battleplan={battleplan}
        onClose={() => setPlacementOpen(false)}
      />
      <RollModal
        open={rollModalOpen}
        pausedActions={pausedActions}
        rollInputs={rollInputs}
        rollValidationErrors={rollValidationErrors}
        onChangeInput={(rid, val) => {
          setRollInputs((r) => ({ ...r, [rid]: val }));
          const n = Number(val);
          setRollValidationErrors((errs) => ({
            ...errs,
            [rid]: !Number.isInteger(n) || n < 1 || n > 6,
          }));
        }}
        onCancel={() => setRollModalOpen(false)}
        onSubmit={async () => {
          // Build action results array from rollInputs
          const results = (pausedActions || []).map((a) => ({
            request_id: a.request_id,
            result: { roll: Number(rollInputs[a.request_id] || 0) },
          }));
          try {
            if (!seed) {
              alert(
                "No seed available: upload a roster first to initialize a stateless session."
              );
              return;
            }
            // stateless resolve only
            const res = await api.resolveRollsStateless({
              seed,
              turn: turn - 1,
              pending_actions: pausedActions,
              action_results: results,
            });
            // Prefer to present checks first (white), then rolls (red small), then actions (yellow)
            if (res && Array.isArray(res.events)) {
              const inferredTurn =
                res.events.find((e) => e && e.turn !== undefined)?.turn ??
                res.events.find(
                  (e) => e && e.action_resolved && e.action_resolved.turn
                )?.action_resolved.turn;
              if (inferredTurn !== undefined) ensureTurnHeader(inferredTurn);
              // normalize incoming events so shapes are consistent
              const norm = res.events.map((e) => normalizeEvent(e) || e);
              // collect ordered lists
              const checks = [];
              const rolls = [];
              const actions = [];
              norm.forEach((ev) => {
                if (ev.event === "aggression_check") checks.push(ev);
                else if (ev.event === "roll_result" || ev.event === "roll")
                  rolls.push(ev);
                else if (ev.event === "action_resolved" && ev.action_resolved)
                  actions.push(ev);
                else actions.push(ev);
              });

              // Append checks (white, compact)
              checks.forEach((ac) => {
                const line = `Aggression: ${ac.unit} -> ${
                  ac.aggression_check ? "ACT" : "HOLD"
                }  (d6=${ac.roll ?? "?"} + mod=${ac.modifier ?? 0} => total=${
                  ac.total ?? "?"
                } vs target=${ac.target ?? "?"})`;
                appendTyped("check", line);
              });

              // Append explicit per-request roll results (red, small)
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

              // Append actions (yellow)
              actions.forEach((ev) => {
                if (ev.event === "action_resolved" && ev.action_resolved) {
                  const ar = ev.action_resolved;
                  const details = ar.details || {};
                  const detailLines = Object.keys(details || {}).map(
                    (k) => `    ${k}: ${JSON.stringify(details[k])}`
                  );
                  const block = [
                    `AI action: ${ar.unit} -> ${ar.card_title || "(action)"}`,
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

            // advance local turn counter (we presented roll_request for turn-1 earlier)
            setTurn((t) => t + 1);
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
                const field = parsed.field ? ` field=${parsed.field}` : "";
                const val =
                  parsed.value !== undefined ? ` value=${parsed.value}` : "";
                appendLog(`Roll rejected: ${parsed.error}${rid}${field}${val}`);
              } else {
                appendLog("Warn: failed to resolve rolls: " + msg);
              }
            } catch (parseErr) {
              // Not JSON, just log the message
              appendLog("Warn: failed to resolve rolls: " + msg);
            }
          }
        }}
        disableSubmit={(pausedActions || []).some(
          (a) => rollValidationErrors[a.request_id] || !rollInputs[a.request_id]
        )}
      />
    </div>
  );
}
