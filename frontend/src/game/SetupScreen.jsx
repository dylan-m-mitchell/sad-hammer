import React, { useState } from "react";

const PROFILE_ACCENTS = {
  aggressive: {
    ring: "border-rose-500/60 bg-rose-500/10",
    chip: "bg-rose-500/20 text-rose-200",
    icon: "⚔",
  },
  balanced: {
    ring: "border-amber-500/60 bg-amber-500/10",
    chip: "bg-amber-500/20 text-amber-200",
    icon: "⚖",
  },
  cautious: {
    ring: "border-emerald-500/60 bg-emerald-500/10",
    chip: "bg-emerald-500/20 text-emerald-200",
    icon: "🛡",
  },
};

function ErrorBanner({ error }) {
  if (!error) return null;
  return (
    <div
      role="alert"
      className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-100"
    >
      {error}
    </div>
  );
}

export default function SetupScreen({
  options,
  loading,
  error,
  busy,
  savedGameId,
  initialSettings,
  onStart,
  onResume,
  onImport,
  onDiscardSaved,
}) {
  const defaults = options?.defaults || {};
  const profiles = options?.profiles || [];
  const [aiProfile, setAiProfile] = useState(
    initialSettings?.ai_profile || defaults.ai_profile || "aggressive"
  );
  const [mission, setMission] = useState(
    initialSettings?.mission || defaults.mission || "contested-ground"
  );
  const [playerPack, setPlayerPack] = useState(
    initialSettings?.player_pack || defaults.player_pack || "stormcast-starter"
  );
  const [aiPack, setAiPack] = useState(
    initialSettings?.ai_pack || defaults.ai_pack || "skaven-starter"
  );
  const [seed, setSeed] = useState("");
  const [skipDeployment, setSkipDeployment] = useState(
    initialSettings?.skip_deployment ?? defaults.skip_deployment ?? true
  );
  const [showAdvanced, setShowAdvanced] = useState(false);

  const packOptions = options?.packs || [];
  const missionOptions = options?.missions || [];
  const selectedMission = missionOptions.find((item) => item.id === mission);
  const selectedProfile = profiles.find((item) => item.id === aiProfile);

  function handleSubmit(event) {
    event.preventDefault();
    const settings = {
      ai_profile: aiProfile,
      mission,
      player_pack: playerPack,
      ai_pack: aiPack,
      skip_deployment: skipDeployment,
    };
    if (seed.trim() !== "") settings.seed = Number(seed);
    onStart(settings);
  }

  return (
    <div className="min-h-screen bg-stone-950 text-stone-100">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-amber-600/10 blur-3xl" />
        <div className="absolute -bottom-40 right-0 h-[28rem] w-[28rem] rounded-full bg-sky-700/10 blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(120,113,108,0.12),transparent_55%)]" />
      </div>

      <main className="relative mx-auto flex min-h-screen w-full max-w-5xl flex-col justify-center px-4 py-10 sm:px-6">
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.35em] text-amber-400/90">
              Sad Hammer
            </p>
            <h1 className="text-3xl font-semibold tracking-tight text-stone-50 sm:text-5xl">
              Age of Sigmar 4th
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-300 sm:text-base">
              A quick, playable skirmish against the AI. Choose a style, take
              your Skaventide starter force and fight for the Contested Ground
              objectives over five battle rounds.
            </p>
          </div>
          <a
            className="hidden shrink-0 rounded-md border border-stone-700 px-3 py-2 text-xs text-stone-400 transition hover:border-stone-500 hover:text-stone-200 sm:block"
            href="/legacy"
          >
            Legacy simulator
          </a>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-stone-800 bg-stone-900/80 p-4 shadow-2xl shadow-black/30 backdrop-blur sm:p-6"
        >
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-stone-100">
                Choose your opponent
              </h2>
              <p className="text-xs text-stone-400">
                Aggression changes target priority, risk and objective focus.
              </p>
            </div>
            <span className="rounded-full border border-stone-700 bg-stone-950/60 px-3 py-1 text-[11px] text-stone-400">
              Stormcast vs Skaven
            </span>
          </div>

          {loading && (
            <div className="mb-4 rounded-lg border border-stone-800 bg-stone-950/60 px-4 py-3 text-sm text-stone-400">
              Preparing the battlefield…
            </div>
          )}
          <ErrorBanner error={error} />

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {profiles.length === 0 && !loading && (
              <div className="col-span-full rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
                AI profiles could not be loaded. Check that the backend is
                running, then refresh.
              </div>
            )}
            {profiles.map((profile) => {
              const accent =
                PROFILE_ACCENTS[profile.id] || PROFILE_ACCENTS.balanced;
              const active = profile.id === aiProfile;
              return (
                <button
                  key={profile.id}
                  type="button"
                  onClick={() => setAiProfile(profile.id)}
                  aria-pressed={active}
                  className={`rounded-xl border p-4 text-left transition ${
                    active
                      ? `${accent.ring} shadow-lg`
                      : "border-stone-800 bg-stone-950/40 hover:border-stone-600"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xl" aria-hidden="true">
                      {accent.icon}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${accent.chip}`}
                    >
                      {active ? "Selected" : "AI style"}
                    </span>
                  </div>
                  <div className="mt-3 text-sm font-semibold capitalize text-stone-100">
                    {profile.name}
                  </div>
                  <p className="mt-1 text-xs leading-5 text-stone-400">
                    {profile.description}
                  </p>
                </button>
              );
            })}
          </div>

          {selectedProfile && (
            <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-stone-400">
              <span className="rounded-full bg-stone-800 px-2.5 py-1">
                Objectives {selectedProfile.objective_focus.toFixed(2)}×
              </span>
              <span className="rounded-full bg-stone-800 px-2.5 py-1">
                Damage {selectedProfile.damage_focus.toFixed(2)}×
              </span>
              <span className="rounded-full bg-stone-800 px-2.5 py-1">
                Risk {selectedProfile.risk_tolerance.toFixed(2)}
              </span>
            </div>
          )}

          <div className="mt-5 rounded-xl border border-stone-800 bg-stone-950/40 p-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-sm font-medium text-stone-200">
                  {selectedMission?.name || "Contested Ground"}
                </div>
                <div className="text-xs text-stone-500">
                  {selectedMission
                    ? `${selectedMission.board.width}×${selectedMission.board.height} board · ${selectedMission.rounds} rounds · ${selectedMission.objectives} objectives`
                    : "44×30 board · 5 rounds · 4 objectives"}
                </div>
              </div>
              <div className="flex items-center gap-3 text-xs text-stone-400">
                <span>
                  {packOptions.find((pack) => pack.id === playerPack)?.name ||
                    "Stormcast Eternals"}
                </span>
                <span className="text-stone-600">vs</span>
                <span>
                  {packOptions.find((pack) => pack.id === aiPack)?.name ||
                    "Skaven"}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4">
            <button
              type="button"
              onClick={() => setShowAdvanced((value) => !value)}
              className="text-xs font-medium text-stone-400 underline-offset-4 transition hover:text-stone-200 hover:underline"
            >
              {showAdvanced ? "Hide advanced options" : "Advanced options"}
            </button>
            {showAdvanced && (
              <div className="mt-3 grid gap-3 rounded-xl border border-stone-800 bg-stone-950/40 p-3 sm:grid-cols-2">
                <label className="text-xs text-stone-400">
                  Seed (blank for a random game)
                  <input
                    type="number"
                    min="0"
                    value={seed}
                    onChange={(event) => setSeed(event.target.value)}
                    placeholder="Random"
                    className="input mt-1"
                  />
                </label>
                <label className="flex items-center gap-2 self-end rounded-md border border-stone-800 bg-stone-900 px-3 py-2 text-xs text-stone-300">
                  <input
                    type="checkbox"
                    checked={skipDeployment}
                    onChange={(event) =>
                      setSkipDeployment(event.target.checked)
                    }
                    className="h-4 w-4 accent-amber-500"
                  />
                  Start with both armies deployed
                </label>
                <label className="text-xs text-stone-400">
                  Mission
                  <select
                    value={mission}
                    onChange={(event) => setMission(event.target.value)}
                    className="input mt-1"
                  >
                    {missionOptions.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <label className="text-xs text-stone-400">
                    Your force
                    <select
                      value={playerPack}
                      onChange={(event) => setPlayerPack(event.target.value)}
                      className="input mt-1"
                    >
                      {packOptions.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="text-xs text-stone-400">
                    AI force
                    <select
                      value={aiPack}
                      onChange={(event) => setAiPack(event.target.value)}
                      className="input mt-1"
                    >
                      {packOptions.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>
            )}
          </div>

          <div className="mt-5 flex flex-col gap-2 sm:flex-row">
            <button
              type="submit"
              disabled={busy || loading || profiles.length === 0}
              className="btn flex-1 bg-amber-500 px-5 py-3 text-sm font-semibold text-stone-950 shadow-lg shadow-amber-900/30 hover:bg-amber-400 focus:ring-2 focus:ring-amber-300 disabled:cursor-not-allowed"
            >
              {busy ? "Deploying…" : "Start battle"}
            </button>
            {savedGameId && (
              <button
                type="button"
                onClick={onResume}
                disabled={busy}
                className="btn border border-stone-700 bg-stone-900 px-4 py-3 text-sm text-stone-200 hover:border-stone-500"
              >
                Resume saved game
              </button>
            )}
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-stone-500">
            <label className="cursor-pointer rounded-md border border-stone-800 px-3 py-2 transition hover:border-stone-600 hover:text-stone-300">
              Import saved game
              <input
                type="file"
                accept="application/json,.json"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) onImport(file);
                  event.target.value = "";
                }}
              />
            </label>
            {savedGameId && (
              <button
                type="button"
                onClick={onDiscardSaved}
                className="text-stone-500 underline-offset-4 hover:text-rose-300 hover:underline"
              >
                Forget saved game
              </button>
            )}
            <a
              href="/legacy"
              className="underline-offset-4 hover:text-stone-300 hover:underline sm:hidden"
            >
              Legacy simulator
            </a>
          </div>
        </form>

        <div className="mt-5 grid gap-2 text-xs text-stone-500 sm:grid-cols-3">
          <div className="rounded-lg border border-stone-900 bg-stone-950/40 p-3">
            <span className="font-semibold text-stone-300">1. Pick a unit</span>
            <p className="mt-1">Tap a friendly token or a unit chip.</p>
          </div>
          <div className="rounded-lg border border-stone-900 bg-stone-950/40 p-3">
            <span className="font-semibold text-stone-300">2. Give an order</span>
            <p className="mt-1">
              Move, shoot, charge, fight or spend a command point.
            </p>
          </div>
          <div className="rounded-lg border border-stone-900 bg-stone-950/40 p-3">
            <span className="font-semibold text-stone-300">3. End the phase</span>
            <p className="mt-1">
              The AI takes its turn automatically and explains each choice.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
