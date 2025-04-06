#!/bin/sh

# author: martin@affolter.net

yellow() { printf "\e[33m$*\e[0m\n"; }
green() { printf  "\e[32m$*\e[0m\n"; }

# names
registry="$1"
image_name="$2"

yellow "Building Docker image for \"$registry/$image_name\"..."

# detect changes
# ==============
# Compute checksum of the source directory to detect changes
checksum_file="./../.${image_name}_checksum"
source_dir="./app"
new_checksum=$(find $source_dir -type f -exec shasum {} \; | shasum | awk '{print $1}')
version_file="./../${image_name}_version.txt"

if [ -f "$checksum_file" ]; then
  old_checksum=$(cat $checksum_file)
else
  old_checksum=""
fi

if [ "$new_checksum" != "$old_checksum" ]; then
  yellow "Changes detected. Building Docker image \"$image_name\"..."

  # Ensure the version file exists
  if [ ! -f "$version_file" ]; then
    echo "0.0" > $version_file
  fi

  # Read and increment version
  current_version=$(cat $version_file)

  # Split the version into major and minor parts
  major=$(echo "$current_version" | cut -d. -f1)
  minor=$(echo "$current_version" | cut -d. -f2)

  # Validate that both parts are numbers
  if ! [[ "$major" =~ ^[0-9]+$ ]] || ! [[ "$minor" =~ ^[0-9]+$ ]]; then
    echo "Error: Version file does not contain a valid version. Resetting to 0.1."
    major=0
    minor=1
  fi

  # Increment the minor version
  minor=$((minor + 1))

  # Combine the major and incremented minor version
  new_version="$major.$minor"

  echo "major: $major"
  echo "minor: $minor"
  echo $new_version > $version_file

  # build the image
  # LOGIN:
  az acr login --name "$registry"

  # to create linux/amd64 images on mac os (linux/arm64)
  # "buildx" is used
  # ====================================================
  # Create a new builder instance
  docker buildx create --use --name mybuilder

  # Inspect the builder to ensure it supports multi-platform builds
  docker buildx inspect mybuilder --bootstrap

  # Build the Docker image for linux/amd64
  docker buildx build --push --platform linux/amd64 -t "$registry/$image_name:$new_version" -f Dockerfile .

  # Update checksum file
  echo $new_checksum > $checksum_file
else
  green "No changes detected. Skipping Docker build for \"$image_name\"."
fi
