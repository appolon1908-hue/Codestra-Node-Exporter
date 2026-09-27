# Repository profile

- Authority: `appolon1908-hue/Codestra-Node-Exporter`
- Component: `node-exporter`
- Artifact model: repository-built, signed immutable image
- Runtime exposure: private observability network only; no host port publication
- Runtime base: Node Exporter v1.12.1 at an exact OCI digest and upstream commit
- Build context: `codestra/`, bounded by `codestra/.dockerignore`
- Promotion path: `development -> test -> staging -> production -> main`
- Production activation from this source: `NO`

The vendored upstream tree is a separately reviewed source snapshot used by broader source tests. It is not represented as the runtime binary. Runtime provenance is locked independently in `codestra/release/runtime-base.lock.json` and verified from the binary revision readback.

Whitespace enforcement applies to Codestra-owned files. The reviewed `upstream/` snapshot is byte-preserved and exempt through `.gitattributes`.
