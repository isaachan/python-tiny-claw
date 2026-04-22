#!/bin/bash

# clean.sh - Delete all __pycache__ directories recursively from current directory

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Searching for __pycache__ directories...${NC}"

# Find all __pycache__ directories (excluding ./venv)
cache_dirs=$(find . -path ./venv -prune -o -type d -name "__pycache__" -print 2>/dev/null | sort)

if [[ -z "$cache_dirs" ]]; then
    echo -e "${GREEN}No __pycache__ directories found.${NC}"
    exit 0
fi

echo -e "${YELLOW}Found the following __pycache__ directories:${NC}"
echo "$cache_dirs"
echo

# Delete directories
echo -e "${RED}Deleting __pycache__ directories...${NC}"
for dir in $cache_dirs; do
    echo "Removing: $dir"
    rm -rf "$dir"
done

echo -e "${GREEN}Done. All __pycache__ directories have been removed.${NC}"