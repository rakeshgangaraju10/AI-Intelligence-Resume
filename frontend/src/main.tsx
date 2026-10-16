import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import { App } from "./App";
import { AuthProvider } from "./features/auth/AuthContext";
import { startWakeOnReturn } from "./services/wake";
import "./index.css";

const root = document.getElementById("root");
if (!root) throw new Error("Root element #root not found");

startWakeOnReturn();

createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
