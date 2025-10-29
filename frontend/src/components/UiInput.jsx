import React from "react";

export default function UiInput({
  id,
  value,
  onChange,
  type = "text",
  className = "",
  ...props
}) {
  return (
    <input
      id={id}
      value={value}
      onChange={onChange}
      type={type}
      className={`input ${className}`}
      {...props}
    />
  );
}
