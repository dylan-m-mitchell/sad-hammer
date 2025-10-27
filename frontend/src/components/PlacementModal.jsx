import React from "react";
import Modal from "./Modal";

export default function PlacementModal({
  open,
  placement,
  chosenZones,
  bpImgSrc,
  onClose,
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="AI Deployment"
      className="max-w-4xl max-h-[85vh] flex flex-col"
    >
      <p className="text-sm text-slate-300">
        The uploaded roster is the enemy AI. Deployment has been auto-picked
        based on the battleplan: {placement?.battleplan?.title || "Unknown"}
      </p>
      <div className="mt-3 flex-1 min-h-0 overflow-y-auto p-2">
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
                    <th className="px-3 py-2 text-left font-semibold">Unit</th>
                    <th className="px-3 py-2 text-left font-semibold">
                      Zone (AI-chosen)
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {(placement?.suggestions || []).map((s) => (
                    <tr key={s.unit} className="border-t border-slate-700">
                      <td className="px-3 py-2">{s.unit}</td>
                      <td className="px-3 py-2 text-slate-300">
                        {(chosenZones || {})[s.unit] || s.suggested_zone || "-"}
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
              <div className="mb-2 text-sm font-semibold">Deployment map</div>
              {bpImgSrc || placement?.map_src ? (
                <img
                  src={bpImgSrc || placement.map_src}
                  alt="Battleplan map"
                  className="max-h-[360px] w-full rounded object-contain"
                />
              ) : (
                <div className="text-sm text-slate-300">
                  No map image found. Use the grid below as a guide.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn-primary" onClick={onClose} id="placement-close">
          Close
        </button>
      </div>
    </Modal>
  );
}
