# ZIMStudy AI — Phase 1

An offline-first study app for ZIMSEC students, built with Kotlin and
Jetpack Compose. This is the Phase 1 slice of a larger planned system:
onboarding, subject management, exam countdown, a study timer, and a
local database — all working fully offline, no backend or API keys
required.

## What's here

- **Onboarding** — name, school, grade, exam board, exam year
- **Subjects** — add/remove the subjects you're studying
- **Dashboard** — countdown to your next exam, quick-start buttons per subject
- **Study timer** — tracks a session and logs it once completed
- **Local database** (Room) — everything persists between app launches, on-device only

## Getting a build

### Option A — GitHub Actions (no local setup)
Push this repo to GitHub and the included workflow
(`.github/workflows/build-apk.yml`) builds a debug `.apk` automatically
on every push to `main`. Grab it from the run's **Artifacts** section.

> Note: this workflow was written without the ability to test it end to
> end (the environment that generated this repo has no internet
> access). It follows standard practice for GitHub-hosted Android
> builds, but if the Actions log shows an error on first run, it's
> usually a one-line dependency/version fix — open an issue or ping
> whoever's helping you with it.

### Option B — Android Studio (local development)
1. Install [Android Studio](https://developer.android.com/studio).
2. **File → Open** and select this repo's root folder.
3. Let it sync (first sync downloads dependencies — needs internet).
4. Click **Run ▶** to install on a connected device/emulator, or
   **Build → Build App Bundle(s) / APK(s) → Build APK(s)** to get an
   installable file at `app/build/outputs/apk/debug/app-debug.apk`.

## Roadmap

Phase 1 (this repo) covers the on-device basics only. The fuller
ZIMStudy AI concept — AI tutor, past-paper analysis, document
upload with RAG, YouTube-transcript learning, voice mode, mastery
scoring, grade forecasting, alarms/widgets — needs a separate backend
service holding the AI provider API key (keys should never ship
inside the app itself) plus additional native Android work. Those are
tracked as future phases, not part of this repo yet.

## Tech stack

Kotlin, Jetpack Compose, Material 3, Navigation Compose, Room, Kotlin
Coroutines. Min SDK 26 (Android 8.0+).

## Web edition

The same Phase 1 feature set is also available as a browser-based
webapp with a pure-Python (standard library only) backend — see
[`web/README.md`](web/README.md). Useful if you want to try the app
in a browser without setting up Android Studio first.
