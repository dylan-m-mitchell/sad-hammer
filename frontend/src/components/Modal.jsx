import React from "react";

export default function Modal({
  open,
  onClose,
  title,
  children,
  className = "",
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div
        className={`relative z-10 w-full max-w-2xl rounded-lg border border-slate-800 bg-slate-800 p-4 overflow-y-auto ${className}`}
      >
        {title ? <h3 className="text-lg font-semibold">{title}</h3> : null}
        {/* make this wrapper a flex item so children using flex-1 can scroll correctly */}
        <div className="mt-3 flex-1 min-h-0">{children}</div>
      </div>
    </div>
  );
}
