#!/usr/bin/env bash
# Import the scanned artifact and verify the running revision.
set -euo pipefail
artifact_directory=$(realpath "${1:?artifact directory required}")
revision=${2:?commit SHA required}
if [[ ! "$revision" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Revision must be a full commit SHA" >&2
  exit 1
fi
image="secure-flask-app:$revision"
(
  cd "$artifact_directory"
  sha256sum -c image.tar.sha256
)
sudo k3s ctr images import "$artifact_directory/image.tar"
sed "s|image: secure-flask-app:latest|image: $image|" k8s-deployment.yaml |
  sudo k3s kubectl apply -f -
sudo k3s kubectl rollout status deployment/flask-app --timeout=180s
sudo k3s kubectl get pods -l app=flask-app -o wide
sudo k3s kubectl get svc flask-service
curl --fail --silent --show-error --retry 6 --retry-all-errors --retry-delay 2 \
  --connect-timeout 5 --max-time 15 http://192.168.15.151:30050/health |
  python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["status"]=="ok" and p["service"]=="flask-auth-app" and p["database"]=="ready", p'
for attempt in {1..4}; do
  curl --fail --silent --show-error --connect-timeout 5 --max-time 15 \
    http://192.168.15.151:30050/about |
    EXPECTED_REVISION="$revision" python3 -c 'import json,os,sys; p=json.load(sys.stdin); assert p["revision"]==os.environ["EXPECTED_REVISION"], p'
done
echo "Deployment verified at revision $revision"
