#!/usr/bin/env bash
# Update the VERSION file with a hash of all tracked files.
# The hash changes whenever any tracked file changes.
set -euo pipefail

# Compute hash of all tracked files excluding VERSION itself
# Sorted to ensure consistent ordering
hash=$(git ls-files | grep -v '^VERSION$' | sort | xargs cat | sha256sum | cut -d' ' -f1)

echo "$hash" > VERSION
echo "Generated version: $hash"
