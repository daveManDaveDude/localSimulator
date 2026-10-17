# Project progress dashboard

The dashboard is available at `/progress.html` while the local Vite server is running. It refreshes `public/project-progress.json` on page load and when **Refresh status** is selected. The request bypasses the browser cache, so a new snapshot appears without restarting Vite.

## Updating the snapshot

Update the JSON after a milestone handback or a material plan change:

- Set `asOf` to the report date.
- Update `currentIssue`, `currentNote`, `nextAction`, and `currentWork`.
- Change issue and milestone statuses only when their evidence supports it. Issue statuses are `complete`, `review`, and `not-started`; milestone statuses also allow `open`.
- Adjust the per-issue `forecast` ranges. The M6 and M7 total estimates are calculated from these ranges.
- Update `risks`, `forecastNotes`, and `evidence` to match the current project record.

The snapshot is a local, tracked file; the page does not infer completion from Git activity. Keep AOI coverage statuses accurate and preserve the existing pending status until OSM/OS building and road checks are reviewed. TVW-009 and later remain subject to separate user authorization.

## Run locally

From the repository root:

```powershell
npm run dev
```

Open `http://127.0.0.1:5173/progress.html`. The dashboard is also included in `npm run build` output.
