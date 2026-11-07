#!/usr/bin/env bash
# V1: motor heredado e ineficiente a proposito (~30 s por recibo). Puerto por defecto 8011.
source "$(dirname "$0")/_common.sh"
start_engine v1 "$V1_PORT"
