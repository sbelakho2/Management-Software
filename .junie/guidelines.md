# Junie Operational Guidelines for Sensei OS

To avoid triggering the "Junie has been working on this problem for some time" message and to ensure efficient task resolution in this repository, follow these guidelines:

## 1. Efficiency & Directness
- **Minimize Tool Calls**: Aim to solve problems in fewer than 10 steps. If a task is trivial, do it in 1-3 steps.
- **Avoid Excessive Exploration**: Do not call `ls -R` or broad `grep` commands unless absolutely necessary. Use `search_project` for targeted searches.
- **Limit File Reads**: Avoid reading large files (>50KB) unless they are core to the logic being fixed. Never read large log files or JSON progress files.

## 2. Noisy Files to Ignore
- Ignore all `*.log` files in the root.
- Ignore `massive_progress.json`, `cleaning_stats.json`, and `system_training_report.json`.
- Ignore the numerous `downloader` and `cleaner` scripts in the root unless the task specifically involves them.

## 3. Decision Making
- If a task is ambiguous, ask for clarification early instead of trying many different approaches.
- When you find the relevant code, apply the fix immediately instead of continuing to search for "better" locations.

## 4. Platform Optimization
- If you find yourself taking many steps without progress, stop and re-evaluate your strategy.
- Prioritize using specialized tools over general bash commands.
