# Shared by the start/stop scripts. Source it, do not run it.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
RUN_DIR="$ROOT/scripts/.run"
V1_PORT="${V1_PORT:-8011}"
V2_PORT="${V2_PORT:-8010}"
mkdir -p "$RUN_DIR"

[ -x "$PY" ] || { echo "No existe .venv. Ejecuta: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"; exit 1; }

# start_engine <v1|v2> <port>
start_engine() {
  local engine="$1" port="$2" pidfile="$RUN_DIR/$1.pid"
  if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "[$engine] ya esta corriendo (pid $(cat "$pidfile")) en el puerto $port"; return 0
  fi
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[$engine] el puerto $port esta ocupado por otro proceso. Usa $(echo "$engine" | tr a-z A-Z)_PORT=<otro>"; return 1
  fi
  (cd "$ROOT" && RECEIPT_ENGINE="$engine" nohup "$PY" -m uvicorn api.index:app --port "$port" \
      >"$RUN_DIR/$engine.log" 2>&1 & echo $! >"$pidfile")
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.5
    curl -fs "http://127.0.0.1:$port/health" >/dev/null 2>&1 && { echo "[$engine] listo -> http://127.0.0.1:$port  (admin: /admin)"; return 0; }
  done
  echo "[$engine] no arranco. Revisa $RUN_DIR/$engine.log"; return 1
}

stop_engine() {
  local pidfile="$RUN_DIR/$1.pid"
  if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    kill "$(cat "$pidfile")" && echo "[$1] detenido"
  else
    echo "[$1] no estaba corriendo"
  fi
  rm -f "$pidfile"
}
