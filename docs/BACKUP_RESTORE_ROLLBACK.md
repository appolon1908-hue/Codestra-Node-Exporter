# Backup, restore, and rollback

Node Exporter is stateless. Back up the reviewed Compose manifest, mTLS configuration path, textfile-metric directory ownership and checksum inventory, production source SHA, immutable image digest, and release evidence. Do not copy secret contents into evidence.

Rollback uses the previous approved image digest and configuration checksum. Render the previous manifest, verify required mounted secret files and private networking, pull the exact rollback digest, and apply only the Node Exporter Compose service without rebuilding or destroying volumes. Prove `/metrics` through mTLS and Prometheus target recovery before closing the rollback.
