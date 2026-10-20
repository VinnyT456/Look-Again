import "@fontsource-variable/schibsted-grotesk";
import "../../styles.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { Panel } from "./panel";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Panel />
  </StrictMode>,
);
