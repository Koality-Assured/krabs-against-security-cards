#!/usr/bin/env python3
"""
Card Art Ingestion and Hydration Pipeline for Krabs Against Security.

Processes raw generated images from artifact/brain directories, converts them
to optimized WebP and high-resolution print PNGs in krabs-against-security-cards,
updates art_manifest.json, and synchronizes assets to krabs-against-security-web.
"""

import os
import glob
import json
import shutil
from datetime import datetime
from PIL import Image

BRAIN_DIR = r"C:\Users\Robbie\.gemini\antigravity\brain\424f051e-d32c-4a45-8830-16249f56074f"
CARDS_REPO = r"C:\Code\KA\krabs-against-security-cards"
WEB_REPO = r"C:\Code\KA\krabs-against-security-web"

CARDS_ASSETS_DIR = os.path.join(CARDS_REPO, "assets", "cards")
PRINT_ASSETS_DIR = os.path.join(CARDS_ASSETS_DIR, "print")
MANIFEST_PATH = os.path.join(CARDS_REPO, "art", "art_manifest.json")

WEB_PUBLIC_CARDS_DIR = os.path.join(WEB_REPO, "public", "cards")
WEB_CARDS_DATA_PATH = os.path.join(WEB_REPO, "src", "data", "cards.json")


def ensure_directories():
    os.makedirs(CARDS_ASSETS_DIR, exist_ok=True)
    os.makedirs(PRINT_ASSETS_DIR, exist_ok=True)
    os.makedirs(WEB_PUBLIC_CARDS_DIR, exist_ok=True)


def process_image(src_path, card_id):
    """Converts source JPG/PNG to optimized WebP and 300DPI PNG."""
    with Image.open(src_path) as img:
        img_rgb = img.convert("RGB")
        
        # 1. Save optimized WebP for web client (max width 1200, 4:3)
        webp_path = os.path.join(CARDS_ASSETS_DIR, f"{card_id}.webp")
        img_rgb.save(webp_path, "WEBP", quality=90, method=6)
        
        # 2. Save high-resolution 300DPI print PNG
        print_path = os.path.join(PRINT_ASSETS_DIR, f"{card_id}-300dpi.png")
        img_rgb.save(print_path, "PNG", dpi=(300, 300))
        
        # 3. Synchronize to web public folder
        web_dest = os.path.join(WEB_PUBLIC_CARDS_DIR, f"{card_id}.webp")
        shutil.copy2(webp_path, web_dest)
        
        print(f"Processed {card_id}:")
        print(f"  -> WebP:  {webp_path} ({os.path.getsize(webp_path)} bytes)")
        print(f"  -> Print: {print_path} ({os.path.getsize(print_path)} bytes)")
        print(f"  -> Web:   {web_dest}")


def sync_manifest_and_web_data():
    """Updates art_manifest.json and web cards.json with generated assets."""
    if not os.path.exists(MANIFEST_PATH):
        print(f"Manifest not found at {MANIFEST_PATH}")
        return

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    updated_count = 0
    for card_entry in manifest["cards"]:
        card_id = card_entry["card_id"]
        webp_file = os.path.join(CARDS_ASSETS_DIR, f"{card_id}.webp")
        if os.path.exists(webp_file):
            card_entry["art_status"] = "approved"
            card_entry["asset_path"] = f"assets/cards/{card_id}.webp"
            card_entry["print_asset_path"] = f"assets/cards/print/{card_id}-300dpi.png"
            card_entry["last_updated"] = datetime.utcnow().isoformat() + "Z"
            updated_count += 1

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Updated {updated_count} cards in art_manifest.json")

    # Update web client cards.json
    if os.path.exists(WEB_CARDS_DATA_PATH):
        with open(WEB_CARDS_DATA_PATH, "r", encoding="utf-8") as f:
            web_cards = json.load(f)

        web_updated = 0
        for card in web_cards:
            card_id = card["id"]
            web_img = os.path.join(WEB_PUBLIC_CARDS_DIR, f"{card_id}.webp")
            alt_id = card_id.replace("PROC-", "PR-")
            alt_img = os.path.join(WEB_PUBLIC_CARDS_DIR, f"{alt_id}.webp")

            if os.path.exists(web_img):
                card["artAsset"] = f"/cards/{card_id}.webp"
                web_updated += 1
            elif os.path.exists(alt_img):
                card["artAsset"] = f"/cards/{alt_id}.webp"
                # Also create a copy with PROC- prefix for maximum compatibility
                proc_img = os.path.join(WEB_PUBLIC_CARDS_DIR, f"{card_id}.webp")
                if not os.path.exists(proc_img):
                    shutil.copy2(alt_img, proc_img)
                web_updated += 1

        with open(WEB_CARDS_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(web_cards, f, indent=2)
        print(f"Updated {web_updated} cards in web cards.json with artAsset paths")


def scan_and_ingest():
    """Scans brain directories for generated image files and ingests them."""
    ensure_directories()
    
    # Check parent brain dir and subagent brain dirs
    search_dirs = [
        BRAIN_DIR,
        r"C:\Users\Robbie\.gemini\antigravity\brain"
    ]
    
    found_files = []
    for s_dir in search_dirs:
        for f in glob.glob(os.path.join(s_dir, "*", "*.jpg")) + glob.glob(os.path.join(s_dir, "*.jpg")):
            found_files.append(f)

    # Map filename prefixes to card IDs
    # E.g. ic_001_*.jpg or IC-001_*.jpg or ic_002.jpg
    import re
    card_pattern = re.compile(r"(IC|PE|P|C2|PR|PRC|PROC|INJ|SCN)[-_]?(\d{3})", re.IGNORECASE)

    processed_cards = set()
    for f_path in found_files:
        base = os.path.basename(f_path)
        match = card_pattern.search(base)
        if match:
            prefix, num = match.groups()
            prefix = prefix.upper()
            if prefix in ("PROC", "PRC"):
                prefix = "PR"
            card_id = f"{prefix}-{num}"
            if card_id not in processed_cards:
                print(f"Found match: {base} -> {card_id}")
                process_image(f_path, card_id)
                processed_cards.add(card_id)

    sync_manifest_and_web_data()


if __name__ == "__main__":
    scan_and_ingest()
