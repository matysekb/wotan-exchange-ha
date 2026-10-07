#!/bin/sh
set -eu
umask 077
exec python /opt/wotan/launcher.py
