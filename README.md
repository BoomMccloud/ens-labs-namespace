# RWA ENS identity demo

## Deploy to Vercel

Import the repository into Vercel and set the project root to the directory that contains `vercel.json`. No build command or output directory is required.

The deployment serves the presentation at `/` and exposes the existing same-origin endpoints at `/api/lookup` and `/api/search` through Vercel Python Functions.

Set `SEC_USER_AGENT` in the Vercel project environment to a descriptive application name and monitored contact address before sharing the deployment publicly.

Keep the Vercel API entry points as thin `BaseHTTPRequestHandler` classes that delegate to `rwa_demo_server.handle_api_get`. Do not duplicate market-provider or routing logic inside `api/`.

**Why:** The 2026-09-04 Vercel packaging change preserved one implementation for local and hosted API behavior.

**Guarded by:** `test-market-hook.sh`

## Run locally

```sh
python3 rwa_demo_server.py
```

Open `http://127.0.0.1:8765/rwa-ens-identity-demo.html`.
