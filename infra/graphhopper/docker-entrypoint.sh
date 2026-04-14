#!/bin/sh
set -eu

MODE="${GRAPHHOPPER_MODE:-standby}"
DATA_FILE="${GRAPHHOPPER_DATA_FILE:-/data/raw/busan.osm.pbf}"
CONFIG_FILE="${GRAPHHOPPER_CONFIG_FILE:-/opt/graphhopper/config.yml}"
GRAPH_LOCATION="${GRAPHHOPPER_GRAPH_LOCATION:-/graphhopper/data}"
EXTENSION_JAR="${GRAPHHOPPER_EXTENSION_JAR:-/opt/graphhopper/extensions/ieumgil-graphhopper-custom-ev.jar}"
CUSTOM_EV_JOIN_FILE="${IEUMGIL_CUSTOM_EV_JOIN_FILE:-}"
CUSTOM_EV_PROP=""

if [ ! -f "$DATA_FILE" ]; then
  echo "GraphHopper data file not found: $DATA_FILE" >&2
  exit 1
fi

if [ "$MODE" = "standby" ]; then
  echo "GraphHopper standby mode. Data file is mounted and ready: $DATA_FILE"
  exec tail -f /dev/null
fi

if [ -n "$CUSTOM_EV_JOIN_FILE" ]; then
  CUSTOM_EV_PROP="-Dieumgil.graphhopper.custom_ev_join_file=$CUSTOM_EV_JOIN_FILE"
fi

exec java ${JAVA_OPTS:-} \
  -Ddw.graphhopper.datareader.file="$DATA_FILE" \
  -Ddw.graphhopper.graph.location="$GRAPH_LOCATION" \
  ${CUSTOM_EV_PROP} \
  -cp "${EXTENSION_JAR}:/opt/graphhopper/graphhopper-web.jar" \
  com.graphhopper.application.GraphHopperApplication \
  server "$CONFIG_FILE"
