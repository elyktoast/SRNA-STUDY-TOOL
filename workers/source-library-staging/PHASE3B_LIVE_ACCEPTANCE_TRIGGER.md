# Phase 3B staging acceptance run

This file marks the explicitly authorized one-time disposable staging acceptance run. The existing staging workflow executes the live job only when the push commit message includes `[phase3b-live-acceptance]`. Subsequent ordinary commits do not run the live job.

Retry after staging R2 token permission was changed from read-only to read/write.
