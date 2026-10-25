import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import GameApp from "./game/GameApp.jsx";
import TableApp from "./table/TableApp.jsx";
import "./index.css";

const path = window.location.pathname;
const isLegacyRoute = path === "/legacy" || path.startsWith("/legacy/");
const isDigitalRoute = path === "/digital" || path.startsWith("/digital/");

const container = document.getElementById("root");
const root = createRoot(container);
root.render(
  <React.StrictMode>
    {isLegacyRoute ? <App /> : isDigitalRoute ? <GameApp /> : <TableApp />}
  </React.StrictMode>
);
