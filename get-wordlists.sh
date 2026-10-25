#!/usr/bin/env bash
#
# get-wordlists.sh - Descarga las mejores wordlists para enumeracion web
#                    y (opcional) rockyou para crackeo de contrasenas.
#
# Uso:
#   ./get-wordlists.sh            # solo wordlists de directorios/ficheros
#   ./get-wordlists.sh --rockyou  # anade tambien rockyou (contrasenas, ~133 MB)
#
# En Kali/Parrot muchas ya vienen instaladas:
#   SecLists  -> /usr/share/seclists   (apt install seclists)
#   rockyou   -> /usr/share/wordlists/rockyou.txt(.gz)
# Este script sirve para cualquier maquina o si no las tienes.

set -euo pipefail

OUT="${1:-wordlists}"
[ "$OUT" = "--rockyou" ] && OUT="wordlists"
mkdir -p "$OUT/web" "$OUT/passwords"

RAW="https://raw.githubusercontent.com/danielmiessler/SecLists/master"

# --- Las wordlists de enumeracion web mas usadas (SecLists) ---
declare -A WEB=(
  ["common.txt"]="/Discovery/Web-Content/common.txt"
  ["directory-list-2.3-medium.txt"]="/Discovery/Web-Content/directory-list-2.3-medium.txt"
  ["directory-list-2.3-small.txt"]="/Discovery/Web-Content/directory-list-2.3-small.txt"
  ["raft-medium-directories.txt"]="/Discovery/Web-Content/raft-medium-directories.txt"
  ["raft-medium-files.txt"]="/Discovery/Web-Content/raft-medium-files.txt"
  ["big.txt"]="/Discovery/Web-Content/big.txt"
)

fetch() {
  local url="$1" dest="$2"
  if [ -s "$dest" ]; then
    echo "  [=] ya existe: $dest"
    return
  fi
  echo "  [>] $dest"
  curl -fsSL "$url" -o "$dest" || wget -q "$url" -O "$dest"
}

echo "[*] Descargando wordlists de enumeracion web en $OUT/web ..."
for name in "${!WEB[@]}"; do
  fetch "${RAW}${WEB[$name]}" "$OUT/web/$name"
done

# --- rockyou (opcional, solo para crackeo de contrasenas) ---
if [ "${1:-}" = "--rockyou" ] || [ "${2:-}" = "--rockyou" ]; then
  echo "[*] Descargando rockyou.txt (contrasenas) ..."
  if [ -f /usr/share/wordlists/rockyou.txt ]; then
    cp /usr/share/wordlists/rockyou.txt "$OUT/passwords/rockyou.txt"
    echo "  [=] copiada desde /usr/share/wordlists/rockyou.txt"
  elif [ -f /usr/share/wordlists/rockyou.txt.gz ]; then
    gunzip -c /usr/share/wordlists/rockyou.txt.gz > "$OUT/passwords/rockyou.txt"
    echo "  [=] descomprimida desde la copia local de Kali"
  else
    fetch "${RAW}/Passwords/Leaked-Databases/rockyou.txt.tar.gz" "$OUT/passwords/rockyou.txt.tar.gz"
    tar -xzf "$OUT/passwords/rockyou.txt.tar.gz" -C "$OUT/passwords" && \
      rm -f "$OUT/passwords/rockyou.txt.tar.gz"
  fi
fi

echo
echo "[+] Listo. Resumen:"
find "$OUT" -type f -exec du -h {} + 2>/dev/null | sort -k2

cat <<'TIP'

Que usar para que:
  - Enumerar directorios con dirscan.py  -> wordlists/web/*.txt
       ej: python dirscan.py -u http://IP/ -w wordlists/web/directory-list-2.3-medium.txt -x php,txt
  - Crackear contrasenas (hydra/john)    -> wordlists/passwords/rockyou.txt
       (rockyou NO sirve para enumerar directorios)
TIP
