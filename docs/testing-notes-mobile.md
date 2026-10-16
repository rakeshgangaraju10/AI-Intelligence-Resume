# Mobile testing notes: CareerForge

Tested by: Hamsa B M ([@hamsabm10](https://github.com/hamsabm10))
Date: 16 October 2026
Site: https://careerforge-h362.onrender.com

## Device

- Phone: Android phone
- Connection: mobile data (4G)

## What I tested

✅ worked · ⚠️ worked after a fix / with a problem · ❌ didn't work · — not tested yet

| Feature | Result | Notes |
|---|---|---|
| Create account (with college name and year of passing out) | ✅ | Account created; college name and passing-out year saved |
| Log in / log out | ✅ | Logged in to upload a resume |
| Forgot password email | — | Not tested yet |
| Upload a resume (PDF) | ⚠️ | Failed with "Can't reach the server" (see issue 1); fixed in a660e39 |
| Review and edit extracted skills | — | Not tested yet |
| Add a job (paste / sample job / job link) | — | Not tested yet |
| Run an analysis and read the score | — | Not tested yet |
| Compare two analyses | — | Not tested yet |
| Download the report | — | Not tested yet |
| Settings (edit profile) | — | Not tested yet |

## Issues I found

1. **"Can't reach the server" when uploading a resume**
   - What I did: opened the Upload page on my phone, chose my resume PDF (106.5 KB) and tapped **Upload and analyze**.
   - What happened: the page showed "This file can't be used. Can't reach the server. Check your connection and try again."
   - What I expected: the resume to upload and its skills to be shown.
   - Cause: the free-plan server had gone to sleep (or was restarting for an update), so the upload got no reply.
   - Status: fixed in commit `a660e39`. The site now wakes the server early, shows "Starting the server…", waits, and retries the upload once. A scheduled job also keeps the server awake.

## Suggestions

- Show a clearer message while the server is waking up (done in `a660e39`).
