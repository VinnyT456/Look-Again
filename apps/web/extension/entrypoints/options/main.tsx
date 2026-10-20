import "@fontsource-variable/schibsted-grotesk";
import "../../styles.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { Options } from "./options";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Options />
  </StrictMode>,
);
