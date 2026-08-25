#!/usr/bin/env bash
# Add a Linux SSH user to the shared hecate-exec checkout.
# Run on the VM (needs sudo), after their first gcloud compute ssh so /home/<user> exists.
#
#   sudo bash /opt/hecate/scripts/onboard_exec_vm_user.sh jacob
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: sudo bash $0 <linux-username> [more-users...]" >&2
  exit 1
fi

if [[ ! -d /opt/hecate ]]; then
  echo "ERROR: /opt/hecate missing. Shared checkout is not set up." >&2
  exit 1
fi

groupadd -f hecate

for user in "$@"; do
  if ! id "$user" >/dev/null 2>&1; then
    echo "ERROR: no Linux user ${user}. They must SSH once first." >&2
    exit 1
  fi
  usermod -aG hecate "$user"
  usermod -aG docker "$user" || true
  home="$(getent passwd "$user" | cut -d: -f6)"
  if [[ ! -d "$home" ]]; then
    echo "ERROR: home ${home} missing for ${user}" >&2
    exit 1
  fi
  ln -sfn /opt/hecate "${home}/hecate"
  chown -h "${user}:${user}" "${home}/hecate"
  echo "Onboarded ${user}: ${home}/hecate -> /opt/hecate"
done

echo "They must start a new SSH session for group membership to apply."
