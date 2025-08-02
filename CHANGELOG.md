# Version Command and Owner-Only Restrictions

## /version Command
- Added a new `/version` slash command (server owner only).
- Shows an embed with the current bot version and a list of features.

## Owner-Only Restrictions
- `/link`, `/fix`, and `/version` can now only be used by the server owner.
- Non-owners will receive an ephemeral error message if they try to use these commands.

## Usage
- `/version` — Shows bot version and features (server owner only)
- `/link` — Syncs guild members and calculates Activity Points (server owner only)
- `/fix` — Recalculates all Activity Points (server owner only)

All other commands remain available to all users.
