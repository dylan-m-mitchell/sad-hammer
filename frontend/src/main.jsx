import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import GameApp from "./game/GameApp.jsx";
import "./index.css";

const isLegacyRoute = window.location.pathname.startsWith("/legacy");

const container = document.getElementById("root");
const root = createRoot(container);
root.render(
  <React.StrictMode>
    {isLegacyRoute ? <App /> : <GameApp />}
  </React.StrictMode>
);
