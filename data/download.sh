#!/bin/bash

URL="https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip"
CURRENT_DIR="$(pwd)"
TARGET_DIR="data/eval"
ZIP_FILE="$TARGET_DIR/dev.zip"
UNZIP_DIR="$TARGET_DIR/dev_20240627"
INNER_ZIP_FILE="$UNZIP_DIR/dev_databases.zip"
__MACOSXDIR="$TARGET_DIR/__MACOSX"

# Function to perform the download and extraction
download_and_extract() {
    mkdir -p "$TARGET_DIR"
    echo "=> Starting to download the dataset for evaluation [BirdBench devset]."
    wget -O "$ZIP_FILE" "$URL"
    unzip "$ZIP_FILE" -d "$TARGET_DIR"
    rm "$ZIP_FILE"
    unzip "$INNER_ZIP_FILE" -d "$UNZIP_DIR"
    rm "$INNER_ZIP_FILE"
    mv "$UNZIP_DIR"/* "$TARGET_DIR"
    rmdir "$UNZIP_DIR"
    rmdir "$__MACOSXDIR"
    cd "$CURRENT_DIR"
    echo "Download and extraction complete."
}

# Checking if contents exists and whether --force is triggered or not 
FORCE=false
if [ "$1" == "--force" ]; then
    FORCE=true
fi

if [ "$(ls -A $TARGET_DIR)" ]; then
    if [ "$FORCE" == true ]; then
        echo "Cleaning up $TARGET_DIR as --force is used."
        rm -rf "$TARGET_DIR"/*
        download_and_extract
    else
        echo "$TARGET_DIR is not empty. Use --force to re-download and overwrite the contents."
    fi
else
    download_and_extract
fi
