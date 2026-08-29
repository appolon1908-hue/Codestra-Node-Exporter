# syntax=docker/dockerfile:1.7

ARG GO_BUILDER_IMAGE
ARG NODE_EXPORTER_BASE_IMAGE

FROM ${GO_BUILDER_IMAGE} AS healthcheck-builder
WORKDIR /src
COPY codestra/deploy/healthcheck.go ./healthcheck.go
RUN CGO_ENABLED=0 GOOS=linux go build \
      -trimpath \
      -ldflags='-s -w -buildid=' \
      -o /out/node-exporter-healthcheck \
      ./healthcheck.go

FROM ${NODE_EXPORTER_BASE_IMAGE}
LABEL org.opencontainers.image.title="Codestra Corporate Node Exporter"
LABEL org.opencontainers.image.description="Private, mTLS-protected host metrics and operational evidence for Codestra"
LABEL org.opencontainers.image.vendor="Codestra"

COPY --from=healthcheck-builder --chown=10001:10001 --chmod=0555 /out/node-exporter-healthcheck /node-exporter-healthcheck
COPY --chown=10001:10001 --chmod=0444 codestra/web-config.yml /etc/node_exporter/web.yml

USER 10001:10001
