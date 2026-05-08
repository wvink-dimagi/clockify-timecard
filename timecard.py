#!/usr/bin/env python3
"""Clockify weekly time entry creator — GUI."""

from datetime import date, datetime, timedelta, timezone, time as dtime
import tkinter as tk
from tkinter import ttk, messagebox
import requests

# ── Configuration ─────────────────────────────────────────────────────────────
API_KEY      = "NWQyZDQzYTktNTllZi00Nzg4LWFjMDYtNTc0ZjQyYjc3MDIw"
WORKSPACE_ID = "600c355584390918698e348d"
BASE_URL     = "https://api.clockify.me/api/v1"

# +2 = South Africa Standard Time (SAST, no DST).
UTC_OFFSET_HOURS = 2
DAY_START_HOUR   = 9

HEADERS = {"X-Api-Key": API_KEY, "Content-Type": "application/json"}

# ── Tags ──────────────────────────────────────────────────────────────────────
TAG_CHC_2026         = "668cda21725b056bd7b6ea2a"  # Give Well:CommCare Connect CHC
TAG_CONNECT_CHLORINE = "697b059c8b2453181a6dd058"  # GiveWell:Connect-Chlorine Dispensers
TAG_RUTF             = "69c3c14323101c2317f864ba"  # CIFF:Connect - RUTF Nigeria
TAG_OVERHEAD         = "600c38be09c9406808cb74e6"  # Overhead

# ── Task catalogue ────────────────────────────────────────────────────────────
TASKS = [
    # ── Sol Client Work ───────────────────────────────────────────────────────
    {"label": "CHC 2026",              "project_id": "600c396109c9406808cb7852", "task_id": "600c396109c9406808cb7866", "description": "CHC 2026",              "tag_ids": [TAG_CHC_2026]},
    {"label": "Connect Chlorine",      "project_id": "600c396109c9406808cb7852", "task_id": "600c396109c9406808cb7866", "description": "Connect Chlorine",      "tag_ids": [TAG_CONNECT_CHLORINE]},
    {"label": "RUTF",                  "project_id": "600c396109c9406808cb7852", "task_id": "600c396109c9406808cb7866", "description": "RUTF",                  "tag_ids": [TAG_RUTF]},
    # ── Overhead (Global) ─────────────────────────────────────────────────────
    # "Connect overhead work" maps to Strategy task — update task_id if needed.
    {"label": "Internal meeting",      "project_id": "600c396009c9406808cb7798", "task_id": "600c396009c9406808cb77a2", "description": "Internal meeting",            "tag_ids": [TAG_OVERHEAD]},
    {"label": "Connect overhead work", "project_id": "600c396009c9406808cb7798", "task_id": "600c396009c9406808cb77ae", "description": "Connect overhead work",         "tag_ids": [TAG_OVERHEAD]},
    {"label": "People management",     "project_id": "600c396009c9406808cb7798", "task_id": "600c396009c9406808cb77a4", "description": "People Management / Mentoring", "tag_ids": [TAG_OVERHEAD]},
    {"label": "Performance Management","project_id": "600c396009c9406808cb7798", "task_id": "60b76924f3682e75a2da8bfe", "description": "Performance Management",        "tag_ids": [TAG_OVERHEAD]},
]

# ── Entry builder ─────────────────────────────────────────────────────────────

def build_entries(week_start: date, pto_days: list[int], hours: list[float]) -> list[dict]:
    working_days = [week_start + timedelta(days=i) for i in range(5) if i not in pto_days]
    if not working_days:
        return []

    def day_start_utc(d: date) -> datetime:
        return datetime.combine(d, dtime(DAY_START_HOUR, 0, 0), tzinfo=timezone.utc) \
               - timedelta(hours=UTC_OFFSET_HOURS)

    entries = []
    day_idx = 0
    day_remaining = 8.0
    cursor = day_start_utc(working_days[0])

    for task, task_hours in zip(TASKS, hours):
        if task_hours <= 0:
            continue
        remaining = task_hours
        while remaining > 0.001 and day_idx < len(working_days):
            chunk = min(remaining, day_remaining)
            entries.append({
                "start":       cursor.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end":         (cursor + timedelta(hours=chunk)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "projectId":   task["project_id"],
                "taskId":      task["task_id"],
                "description": task["description"],
                "tagIds":      task["tag_ids"],
                "_label":      task["label"],  # display only, stripped before POST
            })
            cursor        += timedelta(hours=chunk)
            day_remaining -= chunk
            remaining     -= chunk
            if day_remaining <= 0.001:
                day_idx += 1
                if day_idx < len(working_days):
                    day_remaining = 8.0
                    cursor = day_start_utc(working_days[day_idx])

    return entries

# ── GUI ───────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    _DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

    def __init__(self):
        super().__init__()
        self.title("Clockify Timecard")
        self.resizable(False, False)
        self._build()
        self._refresh()

    def _build(self):
        pad = {"padx": 16, "pady": 6}

        # ── Week ──
        row = ttk.Frame(self)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Week:").pack(side="left")
        self._week_dates, labels = zip(*self._week_options())
        self._week_combo = ttk.Combobox(row, values=list(labels), state="readonly", width=30)
        self._week_combo.current(5)  # index 5 = this week (offsets -5…+2)
        self._week_combo.pack(side="left", padx=(8, 0))

        # ── PTO ──
        pto_frame = ttk.LabelFrame(self, text="PTO days")
        pto_frame.pack(fill="x", **pad)
        self._pto_vars: list[tk.BooleanVar] = []
        for day in self._DAYS:
            v = tk.BooleanVar()
            v.trace_add("write", self._on_change)
            self._pto_vars.append(v)
            ttk.Checkbutton(pto_frame, text=day, variable=v).pack(side="left", padx=8, pady=4)

        # ── Hours ──
        self._hour_vars: list[tk.StringVar] = []
        for section_label, task_slice in [("Sol Client Work", TASKS[:3]), ("Overhead (Global)", TASKS[3:])]:
            section = ttk.LabelFrame(self, text=section_label)
            section.pack(fill="x", **pad)
            for task in task_slice:
                r = ttk.Frame(section)
                r.pack(fill="x", padx=8, pady=3)
                ttk.Label(r, text=task["label"], width=26, anchor="w").pack(side="left")
                v = tk.StringVar(value="0")
                v.trace_add("write", self._on_change)
                self._hour_vars.append(v)
                ttk.Entry(r, textvariable=v, width=6, justify="right").pack(side="left")
                ttk.Label(r, text=" h").pack(side="left")

        # ── Total + button ──
        self._total_lbl = ttk.Label(self, font=("", 12, "bold"))
        self._total_lbl.pack(pady=(6, 0))

        self._btn = ttk.Button(self, text="Create Entries", command=self._submit)
        self._btn.pack(pady=(8, 16))

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _this_monday() -> date:
        t = date.today()
        return t - timedelta(days=t.weekday())

    @staticmethod
    def _week_options() -> list[tuple[date, str]]:
        monday = App._this_monday()
        options = []
        for delta in range(-5, 3):  # 5 past, current, 2 future
            d = monday + timedelta(weeks=delta)
            if delta == 0:
                rel = "this week"
            elif delta == -1:
                rel = "last week"
            elif delta == 1:
                rel = "next week"
            elif delta < 0:
                rel = f"{abs(delta)} weeks ago"
            else:
                rel = f"in {delta} weeks"
            options.append((d, f"{d.strftime('%-d %b %Y')}  ({rel})"))
        return options

    def _pto_indices(self) -> list[int]:
        return [i for i, v in enumerate(self._pto_vars) if v.get()]

    def _target(self) -> float:
        return (5 - len(self._pto_indices())) * 8.0

    def _total(self) -> float:
        total = 0.0
        for v in self._hour_vars:
            try:
                total += max(0.0, float(v.get() or 0))
            except ValueError:
                pass
        return total

    def _on_change(self, *_):
        self._refresh()

    def _refresh(self):
        target = self._target()
        total  = self._total()
        ok     = abs(total - target) < 0.01
        self._total_lbl.config(
            text=f"Total: {total:.1f} / {target:.0f} h",
            foreground="#2a7d2a" if ok else "#c0392b",
        )
        self._btn.config(state="normal" if ok else "disabled")

    # ── Submit ────────────────────────────────────────────────────────────────

    def _submit(self):
        week_start = self._week_dates[self._week_combo.current()]

        hours = []
        for i, v in enumerate(self._hour_vars):
            try:
                hours.append(max(0.0, float(v.get() or 0)))
            except ValueError:
                messagebox.showerror("Invalid input", f"Bad value for '{TASKS[i]['label']}'.")
                return

        entries = build_entries(week_start, self._pto_indices(), hours)

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        preview = "\n".join(
            f"{day_names[date.fromisoformat(e['start'][:10]).weekday()]}  "
            f"{e['start'][11:16]}–{e['end'][11:16]}  {e['_label']}"
            for e in entries
        )
        if not messagebox.askyesno("Preview", f"Create {len(entries)} entries?\n\n{preview}"):
            return

        self._btn.config(state="disabled", text="Creating…")
        self.update()
        try:
            url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/time-entries"
            for e in entries:
                payload = {k: v for k, v in e.items() if not k.startswith("_")}
                r = requests.post(url, headers=HEADERS, json=payload)
                r.raise_for_status()
            messagebox.showinfo("Done", f"Created {len(entries)} entries.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
        finally:
            self._btn.config(state="normal", text="Create Entries")
            self._refresh()


if __name__ == "__main__":
    App().mainloop()
