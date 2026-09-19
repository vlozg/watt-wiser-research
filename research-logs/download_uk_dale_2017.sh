#!/bin/bash

# Target URL
TARGET_URL="https://dap.ceda.ac.uk/edc/d1/7d78f943-f9fe-413b-af52-1816f9d968b0/"

echo "🕷️ Step 1: Recursively mapping out the site structure with wget..."
# Run wget in spider mode to gather all links without downloading files
wget -e robots=off --spider --recursive --no-parent --no-verbose "$TARGET_URL" 2>&1 | \
# 1. Grab everything starting with http/https up to the next whitespace
grep -o 'http[s]*://[^ ]*' | \
# 2. Strip off any trailing wget logging indicators like '[486]->' or '->'
awk '{sub(/\[.*$/, ""); sub(/->$/, ""); print}' | \
# 3. Filter out directories, index files, or query strings
grep -E -v '(\?|index\.html|/$)' | \
# 4. Remove duplicates
sort -u > clean_links.txt

# Count how many files were found
FILE_COUNT=$(wc -l < clean_links.txt)
echo "✅ Found $FILE_COUNT unique files to download."

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "❌ No files discovered. Please check the URL or your network connection."
    rm clean_links.txt
    exit 1
fi

echo "🚀 Step 2: Downloading files in parallel using aria2c..."
# -j 10: Downloads up to 10 files at the same time
# -x 8:  Uses 8 connections per file to max out bandwidth
aria2c -i clean_links.txt -j 10 -x 8 --check-certificate=false

# Clean up the temporary link tracker file
rm clean_links.txt
echo "🎉 Mirroring complete!"
