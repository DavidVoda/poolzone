#!/usr/bin/env bash
# Deploy poolzoneV2 to a Rosti stack (https://rosti.cz) via rosticli.
#
#   ./deploy.sh init        one-time: pick company/profile, create stack, write secrets
#   ./deploy.sh             build + upload image + compose up (repeat for every release)
#   ./deploy.sh seed-db     copy the LOCAL dev DB into the stack (overwrites prod data!)
#   ./deploy.sh admin EMAIL PASSWORD   create the first admin login
#   ./deploy.sh logs | ssh  stream logs / shell on the stack VM
set -euo pipefail
cd "$(dirname "$0")"

# VM login shell is fish and rosticli quotes each arg, so run everything via sh -c.
# Commands start in /srv/stack (compose file lives there as docker-compose.yml).
remote() { rosticli stacks ssh sh -c "$*"; }
# Container of a compose service, found by label so the compose project name doesn't matter.
cid() { echo "\$(docker ps -qf label=com.docker.compose.service=$1)"; }

need_docker() {
  docker info >/dev/null 2>&1 || { echo "Docker daemon not running — start Docker Desktop."; exit 1; }
}

push() {
  need_docker
  # Build for the VM's CPU, not this Mac's (arm64 image won't run on an x86 VM).
  case "$(remote uname -m | tail -1 | tr -d '\r')" in
    aarch64|arm64) export DOCKER_DEFAULT_PLATFORM=linux/arm64 ;;
    *)             export DOCKER_DEFAULT_PLATFORM=linux/amd64 ;;
  esac
  echo "Building for $DOCKER_DEFAULT_PLATFORM"
  rosticli stacks push --no-input
}

case "${1:-push}" in
  init)
    rosticli companies >/dev/null 2>&1 || rosticli login
    # Answers "keep existing" to the Dockerfile + compose prompts; asks company/profile.
    { echo 1; sleep 2; echo 1; cat; } | rosticli stacks init --disable-ai --single --name poolzone
    # Secrets live only on the VM; created once, never overwritten. Own file, not .env:
    # Rosti pre-creates /srv/stack/.env and may manage it.
    pg=$(openssl rand -hex 24); key=$(openssl rand -hex 32)
    remote "test -s secrets.env || (umask 077 && printf '%s\n' \
      POSTGRES_USER=poolzone POSTGRES_PASSWORD=$pg POSTGRES_DB=poolzone \
      DATABASE_URL=postgresql+psycopg://poolzone:$pg@db:5432/poolzone \
      POOLZONE_SECRET_KEY=$key > secrets.env)"
    push
    ;;
  push) push ;;
  seed-db)
    read -rp "Overwrite the PRODUCTION database with local data? [y/N] " ok
    [[ $ok == y ]] || exit 1
    need_docker
    docker compose up -d db
    until docker compose exec -T db pg_isready -U poolzone -q; do sleep 1; done
    docker compose exec -T db pg_dump -U poolzone --clean --if-exists --no-owner poolzone \
      | remote "docker exec -i $(cid db) psql -q -v ON_ERROR_STOP=1 -U poolzone poolzone"
    ;;
  admin)
    [[ $# -eq 3 ]] || { echo "usage: $0 admin EMAIL PASSWORD"; exit 1; }
    remote "docker exec $(cid app) poolz create-user --admin '$2' '$3'"
    ;;
  logs) rosticli stacks logs -f ;;
  ssh)  rosticli stacks ssh ;;
  *) sed -n '2,9p' "$0"; exit 1 ;;
esac
