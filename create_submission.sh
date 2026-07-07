#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [--extra-credit-scene <scene_file>] [--extra-credit-image <image_file>]"
  exit 1
}

EXTRA_CREDIT_SCENE=""
EXTRA_CREDIT_IMAGE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --extra-credit-scene)
      [[ $# -lt 2 ]] && usage
      EXTRA_CREDIT_SCENE="$2"
      shift 2
      ;;
    --extra-credit-image)
      [[ $# -lt 2 ]] && usage
      EXTRA_CREDIT_IMAGE="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUBMISSION_NAME="submission"
DEST_DIR="${ROOT_DIR}/${SUBMISSION_NAME}"

FILES=(
  "./src/cs248a_renderer/model/material.py"
  "./src/cs248a_renderer/model/bvh.py"
  "./src/cs248a_renderer/model/scene_object.py"
  "./src/cs248a_renderer/slang_shaders/math/ray.slang"
  "./src/cs248a_renderer/slang_shaders/math/bounding_box.slang"
  "./src/cs248a_renderer/slang_shaders/model/bvh.slang"
  "./src/cs248a_renderer/slang_shaders/model/camera.slang"
  "./src/cs248a_renderer/slang_shaders/primitive/triangle.slang"
  "./src/cs248a_renderer/slang_shaders/renderer/mesh_renderer/mesh_illumination.slang"
  "./src/cs248a_renderer/slang_shaders/renderer/mesh_renderer/mesh_material.slang"
  "./src/cs248a_renderer/slang_shaders/renderer/mesh_renderer/ray_mesh_intersection.slang"
  "./src/cs248a_renderer/slang_shaders/renderer/mesh_renderer.slang"
  "./src/cs248a_renderer/slang_shaders/brdf/lambertian.slang"
  "./src/cs248a_renderer/slang_shaders/brdf/mirror.slang"
  "./src/cs248a_renderer/slang_shaders/brdf/glass.slang"
  "./src/cs248a_renderer/slang_shaders/light/rect_light.slang"
  "./src/cs248a_renderer/slang_shaders/texture/diff_texture.slang"
  "./src/cs248a_renderer/slang_shaders/texture/texture.slang"
)

rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

for rel in "${FILES[@]}"; do
  src="${ROOT_DIR}/${rel}"
  if [[ ! -f "$src" ]]; then
    echo "missing source file: $rel" >&2
    exit 1
  fi
  dst_dir="${DEST_DIR}/$(dirname "$rel")"
  mkdir -p "$dst_dir"
  cp "$src" "$dst_dir/"
done

if [[ -n "$EXTRA_CREDIT_SCENE" || -n "$EXTRA_CREDIT_IMAGE" ]]; then
  EC_DIR="${DEST_DIR}/extra_credit"
  mkdir -p "$EC_DIR"
  if [[ -n "$EXTRA_CREDIT_SCENE" ]]; then
    if [[ -d "$EXTRA_CREDIT_SCENE" ]]; then
      cp -r "$EXTRA_CREDIT_SCENE" "$EC_DIR/"
    elif [[ -f "$EXTRA_CREDIT_SCENE" ]]; then
      cp "$EXTRA_CREDIT_SCENE" "$EC_DIR/"
    else
      echo "missing extra credit scene: $EXTRA_CREDIT_SCENE" >&2
      exit 1
    fi
  fi
  if [[ -n "$EXTRA_CREDIT_IMAGE" ]]; then
    if [[ ! -f "$EXTRA_CREDIT_IMAGE" ]]; then
      echo "missing extra credit image file: $EXTRA_CREDIT_IMAGE" >&2
      exit 1
    fi
    cp "$EXTRA_CREDIT_IMAGE" "$EC_DIR/"
  fi
fi

ZIP_NAME="${SUBMISSION_NAME}.zip"
rm -f "${ROOT_DIR}/${ZIP_NAME}"
(cd "$ROOT_DIR" && zip -r "$ZIP_NAME" "$(basename "$DEST_DIR")")
rm -rf "$DEST_DIR"
echo "Created $ZIP_NAME"
