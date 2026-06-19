# Clockify Timecard

A macOS GUI app that creates weekly time entries in Clockify. It pops up every Friday at 10:00 AM automatically via a macOS LaunchAgent.

## Setup for a new user

### 1. API key

Copy `.env.example` to `.env` and add your Clockify API key:

```
CLOCKIFY_API_KEY=your_key_here
```

Find your API key at: Clockify → Profile Settings → API.

### 2. Workspace ID

In `timecard.py`, update `WORKSPACE_ID` with your own workspace ID.

Find it at: Clockify → Workspace Settings → the ID in the URL (`app.clockify.me/workspaces/<WORKSPACE_ID>/settings`).

### 3. Projects, tasks, and tags

The `TASKS` list in `timecard.py` defines the rows shown in the GUI. Each entry needs:

- `label` — display name shown in the app
- `project_id` — Clockify project ID
- `task_id` — Clockify task ID within that project
- `description` — text written into the time entry
- `tag_ids` — list of Clockify tag IDs to apply

To find these IDs, use the Clockify API (replace `YOUR_API_KEY` and `YOUR_WORKSPACE_ID`):

```bash
# List projects
curl -H "X-Api-Key: YOUR_API_KEY" \
  https://api.clockify.me/api/v1/workspaces/YOUR_WORKSPACE_ID/projects

# List tasks for a project
curl -H "X-Api-Key: YOUR_API_KEY" \
  https://api.clockify.me/api/v1/workspaces/YOUR_WORKSPACE_ID/projects/PROJECT_ID/tasks

# List tags
curl -H "X-Api-Key: YOUR_API_KEY" \
  https://api.clockify.me/api/v1/workspaces/YOUR_WORKSPACE_ID/tags
```

Replace the existing `TASKS` list and tag constants with your own values.

### 4. Timezone

`UTC_OFFSET_HOURS` is set to `+2` (South Africa Standard Time). Change it to match your timezone offset from UTC.

### 5. Python dependency

Requires Python 3.13 with Tkinter:

```bash
brew install python@3.13 python-tk@3.13
pip3.13 install requests
```

### 6. Weekly auto-launch (macOS LaunchAgent)

To have the app pop up automatically every Friday at 10:00 AM:

1. Copy the plist below to `~/Library/LaunchAgents/io.github.timecard.plist`
2. Run: `launchctl load ~/Library/LaunchAgents/io.github.timecard.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.github.timecard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/python3.13</string>
        <string>/path/to/clockify-timecard/timecard.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key> <integer>5</integer>
        <key>Hour</key>    <integer>10</integer>
        <key>Minute</key>  <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/timecard.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/timecard.log</string>
</dict>
</plist>
```

Replace `/path/to/clockify-timecard/timecard.py` with the actual path on your machine.

If it does not launch, check `/tmp/timecard.log` for errors.
