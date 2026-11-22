# Prototype (Emmanuel Teye Adjei)

Emmanuel's React prototype, from which the RiskTrack interface was ported and from which further interface changes to the app will be taken.

## Emmanuel: how to upload your current code

1. Put the source here, in this folder: `src/`, `package.json`, `package-lock.json`, config files and any assets.
2. **Leave out** `node_modules/`, build folders (`dist/`, `build/`) and any `.env` file or API key.
3. Upload on GitHub (Add file → Upload files) or push a branch, then open a pull request.
4. Add a line here saying how to run it (for example `npm install` then `npm run dev`).

## Current version

- **Live preview:** https://sites.google.com/view/alajocyberriskreg/full-page-embed
- **Source:** `the_alajo_enterprise_cyber_risk_register_grc_platform.tsx` (single-file React component, browser-only demo data)

`reference/emmanuel_prototype_extracted.html` is the earlier single-file version that was shared before this repository existed.

## Ideas to carry into the app (to be agreed with WS2)

- Likelihood and impact scale descriptions (probability ranges, outage hours, loss ranges; convert the $ ranges to ₦ for The Alajo)
- A "View scoring rubric" toggle on the risk register
- An in-app page explaining scoring, bands, appetite and the four governance controls
- Methodology differences to settle: Critical band from 15 (app) or 16 (prototype); top impact label "Severe" (app) or "Catastrophic" (prototype)
