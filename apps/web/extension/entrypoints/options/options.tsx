import { Check, Server } from "lucide-react";
import { useEffect, useState } from "react";
import { browser } from "wxt/browser";

import { WordmarkLockup } from "@/components/brand";
import { Button, cx, Panel, Ruled, ToggleRow, ValueRow } from "@/components/ui";
import { apiClient } from "@/lib/api/client";

import {
  DEFAULT_SERVER,
  loadExtensionSettings,
  normalizeServer,
  originPattern,
  saveExtensionSettings,
  type ExtensionSettings,
} from "../../lib/settings";

type Connection = { state: "idle" | "testing" } | { state: "ready" | "demo" | "unreachable"; server: string };

const connectionText = {
  ready: "Connected. The detector is ready.",
  demo: "Connected, but the detector is offline. Results will be labelled demos.",
  unreachable: "Nothing answered at that address.",
};

/** Bundled with the default server, so localhost needs no extra permission. */
const builtIn = (server: string) => /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(server);

export function Options() {
  const [settings, setSettings] = useState<ExtensionSettings | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [connection, setConnection] = useState<Connection>({ state: "idle" });

  useEffect(() => {
    void loadExtensionSettings().then((loaded) => {
      setSettings(loaded);
      setDraft(loaded.server);
      void test(loaded.server);
    });
  }, []);

  async function test(server: string) {
    setConnection({ state: "testing" });
    try {
      const ready = await apiClient(server).detectorReady();
      setConnection({ state: ready ? "ready" : "demo", server });
    } catch {
      setConnection({ state: "unreachable", server });
    }
  }

  async function update(change: Partial<ExtensionSettings>) {
    if (!settings) return;
    const next = { ...settings, ...change };
    setSettings(next);
    await saveExtensionSettings(next);
  }

  async function saveServer(value: string) {
    const server = normalizeServer(value);
    if (!server) {
      setError("Enter a web address, like https://verify.example.edu.");
      return;
    }
    setError(null);
    // Any server other than localhost needs the person's permission to be contacted.
    if (!builtIn(server)) {
      const granted = await browser.permissions.request({ origins: [originPattern(server)] }).catch(() => false);
      if (!granted) {
        setError("WildcatVerify needs permission to reach that server. Choose Allow when your browser asks.");
        return;
      }
    }
    setDraft(server);
    await update({ server });
    setSaved(true);
    setTimeout(() => setSaved(false), 1600);
    void test(server);
  }

  if (!settings) return null;

  return (
    <div className="min-h-dvh">
      <header className="bg-uv text-on-uv">
        <div className="mx-auto flex min-h-14 max-w-[960px] items-center px-4 sm:px-6">
          <WordmarkLockup compact />
        </div>
      </header>

      <main className="mx-auto flex max-w-[960px] flex-col gap-10 px-4 pt-8 pb-16 sm:px-6">
        <div>
          <h1 className="text-title font-extrabold tracking-[-0.015em]">Extension options</h1>
          <p className="mt-1.5 max-w-[65ch] text-muted">Check photos on Bluesky from the page you found them on. These settings stay in this browser.</p>
        </div>

        <Panel title="Server" footer="The extension sends photos to this WildcatVerify web app to be checked. It doesn't keep them.">
          <form
            className="flex flex-col gap-3 p-4 sm:p-6"
            onSubmit={(event) => {
              event.preventDefault();
              void saveServer(draft);
            }}
          >
            <label htmlFor="server" className="font-semibold">
              WildcatVerify address
            </label>
            <div className="flex flex-col gap-2 sm:flex-row">
              <div className="flex min-h-12 flex-1 items-center gap-2 rounded-md border border-rule-strong bg-label pl-3 transition-colors focus-within:border-accent focus-within:outline-2 focus-within:outline-offset-0 focus-within:outline-accent/25">
                <Server aria-hidden className="size-[18px] shrink-0 text-muted" />
                <input
                  id="server"
                  type="text"
                  inputMode="url"
                  autoComplete="off"
                  spellCheck={false}
                  value={draft}
                  aria-invalid={error ? true : undefined}
                  aria-describedby={error ? "server-error" : undefined}
                  onChange={(event) => setDraft(event.target.value)}
                  className="min-w-0 flex-1 bg-transparent py-2.5 pr-3 focus:outline-none"
                />
              </div>
              <Button type="submit" icon={saved ? Check : undefined} className="min-h-12">
                {saved ? "Saved" : "Save"}
              </Button>
            </div>
            {error && (
              <p id="server-error" role="alert" className="text-small font-semibold text-ai">
                {error}
              </p>
            )}
            {draft !== DEFAULT_SERVER && (
              <button type="button" onClick={() => void saveServer(DEFAULT_SERVER)} className="self-start text-small font-semibold text-accent hover:underline">
                Use {DEFAULT_SERVER.replace("http://", "")}
              </button>
            )}
          </form>
          <Ruled className="border-t border-rule">
            <div className="flex min-h-12 items-center gap-3 px-4 py-3 sm:px-6">
              <span
                aria-hidden
                className={cx(
                  "size-2 shrink-0 rounded-full",
                  connection.state === "ready" ? "bg-glow ring-1 ring-ink/25" : connection.state === "testing" || connection.state === "idle" ? "bg-rule-strong/60" : "border border-muted",
                )}
              />
              <p role="status" className="flex-1 text-small text-muted">
                {connection.state === "testing" || connection.state === "idle" ? "Testing connection…" : connectionText[connection.state]}
              </p>
              <Button variant="quiet" onClick={() => void test(settings.server)} disabled={connection.state === "testing"} className="min-h-9 py-1.5 text-small">
                Test again
              </Button>
            </div>
          </Ruled>
        </Panel>

        <Panel title="Results">
          <ToggleRow
            title="Show where the detector looked"
            detail="On Likely AI results, Detector light lights up the areas that pushed the detector toward AI. They show influence, not proof."
            checked={settings.showHeatmap}
            onChange={(showHeatmap) => void update({ showHeatmap })}
          />
        </Panel>

        <Panel title="Privacy" footer="Results aren't saved by the extension. Open in My Checks hands one result to the web app, which keeps it only if Keep My Checks is on there.">
          <Ruled>
            <ValueRow label="Photos" value="Checked, then discarded" />
            <ValueRow label="Results" value="Cleared when you press Done" />
            <ValueRow label="Sites it can read" value="bsky.app, your server" />
          </Ruled>
        </Panel>
      </main>
    </div>
  );
}
