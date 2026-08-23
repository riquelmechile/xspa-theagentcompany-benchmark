#!/bin/bash
set -euo pipefail

BACKUP_VOLUME="${XSPA_PLANE_BACKUP_VOLUME:-xspa-plane-official-backup}"

restore_one() {
  local stem="$1"
  local volume="plane-app_${stem}"

  docker volume rm -f "$volume" >/dev/null 2>&1 || true
  docker volume create "$volume" >/dev/null

  docker run --rm \
    -v "$volume:/vol" \
    -v "$BACKUP_VOLUME:/backup:ro" \
    busybox sh -c "set -eu; test -s /backup/${stem}.tar.gz; rm -rf /restore; mkdir -p /restore; tar -xzf /backup/${stem}.tar.gz -C /restore; test -d /restore/${stem}; cp -a /restore/${stem}/. /vol/"
}

for stem in pgdata redisdata uploads; do
  restore_one "$stem"
done

echo "Plane restore completed from local official backup volume: $BACKUP_VOLUME"
