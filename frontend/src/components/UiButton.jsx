import React from "react";

export default function UiButton({
  children,
  onClick,
  className = "",
  ...props
}) {
  return (
    <button onClick={onClick} className={`btn ${className}`} {...props}>
      {children}
    </button>
  );
}
