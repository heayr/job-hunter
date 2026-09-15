#!/bin/bash
cd "$(dirname "$0")"

echo "⚡ Starting Job Hunter CRM..."
exec .venv/bin/python crm.py
