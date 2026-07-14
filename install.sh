#!/bin/bash

# Gestione del parametro $Path (il primo argomento passato allo script)
PATH_DEST="$1"

if [ -z "$PATH_DEST" ]; then
    echo "Errore: Devi specificare un percorso di destinazione."
    echo "Uso: $0 /percorso/di/destinazione"
    exit 1
fi

echo "deploy..."
CWD=$(pwd)

# Copia dei file (gestendo anche gli spazi e i backslash convertiti in slash)
cp ./config.yaml "$PATH_DEST/config.yaml"
cp graphrag_cache.json "$PATH_DEST/graphrag_cache.json"
cp graphrag_startup.ps1 "$PATH_DEST/graphrag_startup.ps1"
cp 'http serve.ps1' "$PATH_DEST/http serve.ps1"
cp ./.env.default "$PATH_DEST/.env"
cp package.json "$PATH_DEST/package.json"
cp mcp_stdio_to_http.py "$PATH_DEST/mcp_stdio_to_http.py"

# Creazione della cartella input
mkdir -p "$PATH_DEST/input"

# Cambio directory
cd "$PATH_DEST" || exit 1

echo "creating venv"
python3 -m venv .venv

# Su Linux/macOS i binari del venv sono in bin/, non in Scripts/
./.venv/bin/python -m pip install -r "$CWD/requirements.txt"
npm install

./.venv/bin/python -m graphrag init --model . --embedding .

# Nota: Questa riga nel tuo script originale copia da .\settings.yaml a $Path\settings.yaml
# ma sei già dentro la cartella $Path (ci sei entrato con 'cd').
# L'ho lasciata coerente con la logica originale.
cp ./settings.yaml "$PATH_DEST/settings.yaml"

rm package.json
