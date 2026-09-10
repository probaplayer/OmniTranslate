# templates/

Reference and starter workflow graphs for this app. Unlike `workspaces/`
(gitignored user data), files in this directory **are tracked in git** —
they're meant to be shared and versioned.

## Using a template

A workspace's canvas is loaded from its `workspaces/<name>/graph.json` file
via the `/api/workspaces/<name>/graph` endpoint (see `server/workspace.py`
and `web/js/workspace_tabs.js`). There is currently no in-app "paste JSON
onto the canvas" import feature, so to use a template:

1. Create (or pick) a workspace in the app so its `workspaces/<name>/`
   folder exists.
2. Copy the content of the template file (e.g.
   `templates/lm-studio-glossary-workflow.json`) into that workspace's
   `graph.json`, replacing its contents.
3. Open that workspace in the app — it loads the graph from disk onto the
   canvas.

Before running, adjust the example's literal values for your machine: the
`Provider` node's `model` (and `base_url`/`api_key` if needed), the path
fields (`LoadTextFile.path`, `SaveTextFile.path`,
`RecordChapter.source_path`/`output_path`), and any chapter id.
