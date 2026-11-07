#!/usr/bin/env bash
# V2: motor optimizado (recibo casi instantaneo). Puerto por defecto 8010.
source "$(dirname "$0")/_common.sh"
start_engine v2 "$V2_PORT"
