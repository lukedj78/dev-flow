---
name: linear-scrum
description: 'Take a dev-flow project into Linear and run it with agile scrum. Creates/links a Linear Project under the workspace team, pushes `.workflow/tasks.md` into issues (story-point estimates, `area:web`/`area:agent` labels, milestones), sets up cycles/sprints (2-week cadence), and keeps Linear as the source of truth: sync pushes only new tasks, pulls status/velocity, plans the active sprint up to the velocity target, and reports. Triggers: "porta il progetto in Linear", "crea le issue in Linear", "setup scrum", "pianifica lo sprint", "report di velocity", "adotta questo progetto in Linear", or dev-flow routing from `prd_drafted`/`tasks_split`. Modes: Setup (new project), Adopt (existing Linear project), Sync (ongoing). Not for: writing or estimating the tasks themselves (use `prd-to-tasks`), building the app or agent (use design-md-to-app / eve-agent), or the headless server loop wiring (see docs/loop-engineering.md).'
---

# linear-scrum — Linear integration + agile scrum for a dev-flow project

(body written in Task 4)
