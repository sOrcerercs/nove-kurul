# Nove Kurul Ofisi — sunucu imajı. Kod imaja GİRMEZ: depo bind mount ile /srv/nove-kurul'a bağlanır
# (compose.yaml). Sırlar da imajda değil; servisler .env'i bağlı depodan kendisi okur.
# Tüm sürümler tam sürümdür (kayan etiket, ^, ~ ya da aralık yok). apt paketleri sabit taban imaj etiketinden gelir.
ARG PYTHON_SURUM=3.12.8
ARG NODE_SURUM=22.12.0

FROM node:${NODE_SURUM}-bookworm-slim AS node

FROM python:${PYTHON_SURUM}-slim-bookworm

ARG TARGETARCH
ARG CLAUDE_CODE_SURUM=2.1.330
ARG PSYCOPG_SURUM=3.2.13
ARG SUPERCRONIC_SURUM=0.2.33
ARG SUPERCRONIC_SHA1_AMD64=71b0d58cc53f6bd72cf2f293e09e294b79c666d8
ARG SUPERCRONIC_SHA1_ARM64=e0f0c06ebc5627e43b25475711e694450489ab00
ARG UID=1000
ARG GID=1000

ENV TZ=Europe/Istanbul \
    DISABLE_AUTOUPDATER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata git ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# Node (claude-code için) ikinci aşamadan
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_SURUM} \
 && npm cache clean --force

RUN pip install --no-cache-dir "psycopg[binary]==${PSYCOPG_SURUM}"

# supercronic: indirilir, sağlama toplamı doğrulanmadan çalıştırılmaz
RUN case "${TARGETARCH}" in \
      amd64) SHA1="${SUPERCRONIC_SHA1_AMD64}" ;; \
      arm64) SHA1="${SUPERCRONIC_SHA1_ARM64}" ;; \
      *) echo "desteklenmeyen mimari: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
 && curl -fsSLo /usr/local/bin/supercronic \
      "https://github.com/aptible/supercronic/releases/download/v${SUPERCRONIC_SURUM}/supercronic-linux-${TARGETARCH}" \
 && echo "${SHA1}  /usr/local/bin/supercronic" | sha1sum -c - \
 && chmod +x /usr/local/bin/supercronic

# Grup yalnız yoksa açılır (Mac'te gid 20 Debian'da doludur)
RUN (getent group ${GID} || groupadd -g ${GID} nove-ajan) \
 && useradd -u ${UID} -g ${GID} -m -d /home/nove-ajan nove-ajan \
 && mkdir -p /home/nove-ajan/.claude /srv/nove-kurul \
 && chown -R ${UID}:${GID} /home/nove-ajan /srv/nove-kurul

USER nove-ajan
WORKDIR /srv/nove-kurul
