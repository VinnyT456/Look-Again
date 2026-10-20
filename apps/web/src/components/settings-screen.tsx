"use client";

import { Trash2 } from "lucide-react";
import { useState } from "react";

import { appLinks } from "@/lib/links";
import { app, eraseAllData, updateSettings } from "@/lib/store/app";
import { useStore } from "@/lib/store/store";

import { PageHeader } from "./shell";
import { Button, ConfirmDialog, LinkRow, Panel, Ruled, ToggleRow, ValueRow } from "./ui";

export const APP_VERSION = "1.0";

export function SettingsScreen() {
  const settings = useStore(app, (s) => s.settings);
  const ready = useStore(app, (s) => s.detectorReady);
  const [confirmingErase, setConfirmingErase] = useState(false);

  return (
    <div className="flex max-w-[960px] flex-col gap-8">
      <PageHeader title="Settings" />

      <Panel title="My Checks">
        <ToggleRow
          title="Keep My Checks"
          detail={
            settings.keepHistory
              ? "Your checks and small copies of the photos you checked are saved in this browser only. Turning this off deletes them."
              : "Off: My Checks clears when you close this tab. Nothing is saved."
          }
          checked={settings.keepHistory}
          onChange={(keepHistory) => updateSettings({ keepHistory })}
        />
      </Panel>

      <Panel title="Results">
        <ToggleRow
          title="Show heatmap"
          detail="The heatmap appears under Detector light on Likely AI results and shows which areas influenced the detector most."
          checked={settings.showHeatmap}
          onChange={(showHeatmap) => updateSettings({ showHeatmap })}
        />
      </Panel>

      <Panel
        title="Detector"
        footer="The detector looks for signs of AI generation. It can't tell whether a real photo was edited or shared with a misleading caption, and no detector is always right."
      >
        <Ruled>
          <ValueRow label="Model" value={ready === false ? "Demo (detector offline)" : "CommunityForensics ViT"} />
          <ValueRow label="Runs on" value="The WildcatVerify server" />
          <ValueRow label="Answers" value="Likely Real or Likely AI" />
          <ValueRow label="Calls it AI at" value="50% or higher" />
        </Ruled>
      </Panel>

      <Panel title="About" footer="Detector based on Community Forensics by Jeongsoo Park and Andrew Owens (CVPR 2025).">
        <Ruled>
          <div className="px-4 py-3">
            <p className="font-semibold">WildcatVerify {APP_VERSION}</p>
            <p className="text-small text-muted">Helps you judge whether a photo on Bluesky is genuine, edited, or AI-generated.</p>
          </div>
          <LinkRow title="Privacy Policy" href="/privacy" />
          <LinkRow title="Credits" href="/credits" />
          <LinkRow title="Contact Support" href={appLinks.support} />
        </Ruled>
      </Panel>

      <Panel title="Erase" footer="Deletes My Checks, any saved photos, your best Look Again score, and resets settings.">
        <div className="p-4">
          <Button variant="danger" icon={Trash2} onClick={() => setConfirmingErase(true)}>
            Erase all data
          </Button>
        </div>
      </Panel>

      <ConfirmDialog
        open={confirmingErase}
        title="Erase all data?"
        message="Deletes My Checks, any saved photos, and resets settings."
        confirm="Erase all data"
        onCancel={() => setConfirmingErase(false)}
        onConfirm={() => {
          setConfirmingErase(false);
          void eraseAllData();
        }}
      />
    </div>
  );
}
