import React from "react";

export default function UiSelect({
  value,
  onChange,
  children,
  id,
  className = "",
  ...props
}) {
  return (
    <select
      id={id}
      value={value}
      onChange={onChange}
      className={`input ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}
