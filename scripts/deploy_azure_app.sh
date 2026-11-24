#!/usr/bin/env bash
# Mini deploy for the lecture demo: build locally, push to Azure Container Registry,
# run as Azure Container App. NOT hardened (public URL, DB firewall opened for Azure services).
#
#   (run with bash, not zsh: bash scripts/deploy_azure_app.sh up|down)
#   scripts/deploy_azure_app.sh up      # build + push + create/update the Container App
#   scripts/deploy_azure_app.sh down    # delete everything this script created (DB stays untouched)
#   DRY_RUN=1 scripts/deploy_azure_app.sh up   # only print what would happen
#
# Everything lives in its own tagged resource group (DEMO_RG). The script refuses to run if DEMO_RG
# equals the DB resource group, and `down` only deletes a group tagged purpose=hoteldb-demo.
# Reads .env (AZURE_*_DATABASE_URL, SESSION_SECRET, access codes, AZURE_RESOURCE_GROUP, AZURE_PG_SERVER).
set -euo pipefail
cd "$(dirname "$0")/.."

CMD="${1:-}"
DEMO_RG="${DEMO_RG:-hoteldb-demo-rg}"
APP_NAME=hoteldb
ENV_NAME=hoteldb-env
DRY_RUN="${DRY_RUN:-0}"

say() { printf '\n==> %s\n' "$*"; }
# Run a command, or only print it in dry-run mode. Never use for commands that carry secrets.
run() { if [ "$DRY_RUN" = 1 ]; then echo "[dry-run] $*"; else "$@"; fi; }
confirm() { read -r -p "$1 [y/N] " a; [ "$a" = y ]; }

[ -f .env ] || { echo '.env fehlt (siehe .env.example)'; exit 1; }
# Unreplaced <placeholders> would be parsed by bash as redirects, so check before sourcing (print line numbers only).
bad="$(grep -vE '^[[:space:]]*#' .env | grep -nE '<[A-Za-z_-]+>' | cut -d: -f1 | tr '\n' ' ' || true)"
[ -z "$bad" ] || { echo "In .env sind noch <Platzhalter> (Zeilen ohne Kommentare: $bad)"; exit 1; }
set -a; source .env; set +a
# Owner/admin credentials are never needed here: do not hand them to az/docker child processes.
unset AZURE_SEED_DATABASE_URL LOCAL_SEED_DATABASE_URL AZURE_PG_ADMIN_PASSWORD DB_PASSWORD

: "${AZURE_SUBSCRIPTION_ID:?}" "${AZURE_RESOURCE_GROUP:?}" "${AZURE_PG_SERVER:?}"
# Hard guard: the demo group must never be the group that holds the database.
if [ "$DEMO_RG" = "$AZURE_RESOURCE_GROUP" ]; then
  echo "DEMO_RG ($DEMO_RG) ist identisch mit AZURE_RESOURCE_GROUP (DB). Abbruch."; exit 1
fi
ACR_NAME="$(printf 'hoteldb%s' "${AZURE_SUBSCRIPTION_ID//-/}" | tr 'A-Z' 'a-z' | cut -c1-16)"   # globally unique, a-z0-9 only

case "$CMD" in
down)
  say "Loesche Resource Group $DEMO_RG (Container App, Environment, Registry)"
  # Only delete groups this script created (tagged in `up`).
  [ "$(az group show -n "$DEMO_RG" --query tags.purpose -o tsv 2>/dev/null)" = hoteldb-demo ] \
    || { echo "$DEMO_RG existiert nicht oder hat nicht den Tag purpose=hoteldb-demo. Abbruch."; exit 1; }
  confirm "Wirklich $DEMO_RG loeschen?" || exit 1
  run az group delete --name "$DEMO_RG" --yes --no-wait
  echo "Die Firewall-Regel AllowAzureServices am DB-Server bleibt. Entfernen mit:"
  echo "  az postgres flexible-server firewall-rule delete -g $AZURE_RESOURCE_GROUP -s $AZURE_PG_SERVER --name AllowAzureServices --yes"
  ;;
up)
  for v in AZURE_DATABASE_URL AZURE_STUDENT_DATABASE_URL SESSION_SECRET STUDENT_ACCESS_CODE TEACHER_ACCESS_CODE; do
    [ -n "${!v:-}" ] || { echo "$v ist in .env leer"; exit 1; }
    case "${!v}" in *'<'*) echo "$v enthaelt noch einen <Platzhalter>"; exit 1;; esac
  done

  # Same rules the app enforces at startup (app/config.py check_runtime) - fail here, not in the cloud.
  [ "${#SESSION_SECRET}" -ge 32 ] || { echo 'SESSION_SECRET braucht mindestens 32 Zeichen'; exit 1; }
  [ "$STUDENT_ACCESS_CODE" != "$TEACHER_ACCESS_CODE" ] || { echo 'Student- und Teacher-Code muessen sich unterscheiden'; exit 1; }
  # Right roles in the public app: student URL = read-only hotel_student, app URL must not be the owner.
  [[ "$AZURE_STUDENT_DATABASE_URL" == *://hotel_student:* ]] || { echo 'AZURE_STUDENT_DATABASE_URL muss hotel_student nutzen'; exit 1; }
  [[ "$AZURE_DATABASE_URL" == *://hotel_app:* ]] || { echo 'AZURE_DATABASE_URL muss hotel_app nutzen'; exit 1; }

  LOCATION="$(az postgres flexible-server show -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_PG_SERVER" --query location -o tsv)"
  TAG="$(git rev-parse --short HEAD)-$(date +%H%M%S)"   # unique per run, also with uncommitted changes
  IMAGE="$ACR_NAME.azurecr.io/hoteldb:$TAG"
  say "Region $LOCATION, Registry $ACR_NAME, Image $IMAGE"

  say "1/6 Resource Group und Registry (Basic, ca. 0,15 EUR/Tag)"
  run az extension add --name containerapp --upgrade --yes
  run az provider register --namespace Microsoft.App --wait
  run az provider register --namespace Microsoft.ContainerRegistry --wait
  run az group create --name "$DEMO_RG" --location "$LOCATION" --tags purpose=hoteldb-demo -o none
  run az acr create --name "$ACR_NAME" --resource-group "$DEMO_RG" --sku Basic --admin-enabled true -o none

  say "2/6 Lokal bauen und pushen"
  run docker build --platform linux/amd64 -t "$IMAGE" .
  run az acr login --name "$ACR_NAME"
  run docker push "$IMAGE"

  say "3/6 Container Apps Environment (ohne Log Analytics = keine Zusatzkosten)"
  run az containerapp env create --name "$ENV_NAME" --resource-group "$DEMO_RG" \
    --location "$LOCATION" --logs-destination none -o none

  say "4/6 Container App (scale-to-zero, 0.25 CPU / 0.5 Gi)"
  if [ "$DRY_RUN" = 1 ]; then
    echo "[dry-run] az containerapp create/update $APP_NAME (Secrets werden nicht angezeigt)"
  else
    ACR_USER="$(az acr credential show -n "$ACR_NAME" --query username -o tsv)"
    ACR_PASS="$(az acr credential show -n "$ACR_NAME" --query 'passwords[0].value' -o tsv)"
    if az containerapp show -n "$APP_NAME" -g "$DEMO_RG" -o none 2>/dev/null; then
      # Re-run: refresh the secrets too (rotated codes, corrected URLs), then roll out the new image.
      az containerapp secret set -n "$APP_NAME" -g "$DEMO_RG" -o none --secrets \
        "db-url=$AZURE_DATABASE_URL" "student-db-url=$AZURE_STUDENT_DATABASE_URL" \
        "session=$SESSION_SECRET" "student-code=$STUDENT_ACCESS_CODE" "teacher-code=$TEACHER_ACCESS_CODE"
      az containerapp update -n "$APP_NAME" -g "$DEMO_RG" --image "$IMAGE" \
        --set-env-vars FORWARDED_ALLOW_IPS='*' -o none
    else
      az containerapp create -n "$APP_NAME" -g "$DEMO_RG" --environment "$ENV_NAME" --image "$IMAGE" \
        --registry-server "$ACR_NAME.azurecr.io" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
        --ingress external --target-port 8000 \
        --cpu 0.25 --memory 0.5Gi --min-replicas 0 --max-replicas 1 \
        --secrets "db-url=$AZURE_DATABASE_URL" "student-db-url=$AZURE_STUDENT_DATABASE_URL" \
                  "session=$SESSION_SECRET" "student-code=$STUDENT_ACCESS_CODE" "teacher-code=$TEACHER_ACCESS_CODE" \
        --env-vars DB_TARGET=azure COOKIE_SECURE=true FORWARDED_ALLOW_IPS='*' \
                   AZURE_DATABASE_URL=secretref:db-url AZURE_STUDENT_DATABASE_URL=secretref:student-db-url \
                   SESSION_SECRET=secretref:session STUDENT_ACCESS_CODE=secretref:student-code \
                   TEACHER_ACCESS_CODE=secretref:teacher-code \
        -o none
    fi
  fi

  say "5/6 DB-Firewall: Zugriff fuer Azure-Dienste (0.0.0.0) - bewusst unabgesichert"
  open_rules="$(az postgres flexible-server firewall-rule list -g "$AZURE_RESOURCE_GROUP" -s "$AZURE_PG_SERVER" \
    --query "[?startIpAddress=='0.0.0.0'] | length(@)" -o tsv)"   # own statement: an az failure stops the script
  if [ "$open_rules" = 0 ]; then
    if [ "$DRY_RUN" = 1 ]; then echo "[dry-run] Firewall-Regel AllowAzureServices wuerde angelegt"
    elif confirm "Regel AllowAzureServices am DB-Server $AZURE_PG_SERVER anlegen?"; then
      az postgres flexible-server firewall-rule create -g "$AZURE_RESOURCE_GROUP" -s "$AZURE_PG_SERVER" \
        --name AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0 -o none
    else echo "Uebersprungen - die App erreicht die DB dann evtl. nicht."; fi
  else echo "Regel existiert schon."; fi

  say "6/6 Health-Check (Kaltstart kann 10-20 s dauern)"
  [ "$DRY_RUN" = 1 ] && exit 0
  FQDN="$(az containerapp show -n "$APP_NAME" -g "$DEMO_RG" --query properties.configuration.ingress.fqdn -o tsv)"
  curl --fail --retry 8 --retry-delay 5 --retry-connrefused "https://$FQDN/health" \
    || { echo; echo "Health-Check fehlgeschlagen (DB-Firewall? Logs sind aus; 'az containerapp logs show' geht trotzdem live)"; exit 1; }
  echo
  echo "Fertig: https://$FQDN   (nach der Vorlesung: bash scripts/deploy_azure_app.sh down)"
  ;;
*)
  echo "Usage: $0 up|down   (DRY_RUN=1 zeigt nur an)"; exit 1 ;;
esac
