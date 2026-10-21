# Kimmy

Backend: router -> service -> repository; tools call services. Absolute imports.
Frontend: app composes features and shared; features never import each other;
shared never imports features/app. Filenames use kebab-case.
One PostgreSQL database, single-tenant demo, server-owned user identity.
Fleet bigint IDs are decimal JSON strings. Database sessions use UTC.
No testing/eval/Playwright dependencies in V1. Verify with make check, make build,
and manual walkthrough. Add modules only when implemented, not empty blueprints.
