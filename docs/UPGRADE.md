# Upgrade procedure

Upgrade the Node Exporter runtime base only in a feature branch. Record the upstream tag commit, resolve the multi-platform OCI digest, verify the binary revision from the exact digest, update the runtime-base lock and image-build manifest together, and run all exact-head checks.

After protected review, promote the same certified lineage through development, test, staging, production, and main. Release from the exact production head. Staging must prove host-metric coverage, mTLS, private exposure, bounded labels, restart recovery, and rollback before any production authorization.
