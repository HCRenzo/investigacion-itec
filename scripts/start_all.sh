#!/usr/bin/env bash
# Levanta V1 y V2 al mismo tiempo, comparten la misma base de datos.
source "$(dirname "$0")/_common.sh"
start_engine v2 "$V2_PORT"
start_engine v1 "$V1_PORT"
