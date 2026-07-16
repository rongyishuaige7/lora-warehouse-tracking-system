#!/usr/bin/env python3
"""Repository release checks that do not require hardware."""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path

REQUIRED=[
 ".github/platformio-requirements.in",".github/platformio-requirements.txt",".github/workflows/validate.yml",".gitignore","HARDWARE.md","LICENSE","README.md","SECURITY.md","THIRD_PARTY_NOTICES.md","android_app/gradle/wrapper/gradle-wrapper.jar","android_app/gradle/wrapper/gradle-wrapper.properties","docs/GITHUB_METADATA.md","docs/HARDWARE_LAB_CARD.md","docs/PROJECT_STATUS.md","docs/PROTOCOL.md","docs/SOURCE_PROVENANCE.md","docs/VERIFICATION.md","docs/部署操作步骤.md","esp32_gateway/config.example.h","esp32_gateway/esp32_gateway.ino","esp32_tag/config.example.h","esp32_tag/esp32_tag.ino","firmware/gateway.cpp","firmware/tag.cpp","hardware/BOM.csv","hardware/wiring-diagram.svg","platformio.ini","scripts/check_repo.py","scripts/secret_scan.py","scripts/verify.sh","server/config.example.json","server/server.py"
]
FORBIDDEN_NAMES={"config.h","config.json","local.properties","warehouse.db",".env","id_rsa","id_ed25519"}
FORBIDDEN_DIRS={".pio",".gradle",".idea","__pycache__",".pytest_cache",".venv","venv","node_modules","build"}
FORBIDDEN_SUFFIXES={".o",".a",".elf",".bin",".hex",".map",".apk",".aab",".pyc",".pyo",".db",".sqlite",".sqlite3"}
MAX_FILE_BYTES=5*1024*1024

def candidate_files(root:Path)->list[Path]:
 try: raw=subprocess.run(["git","-C",str(root),"ls-files","-z"],check=True,capture_output=True).stdout
 except (subprocess.CalledProcessError,FileNotFoundError): raw=b""
 if raw:return [root/item.decode("utf-8","surrogateescape") for item in raw.split(b"\0") if item]
 return sorted(p for p in root.rglob("*") if p.is_file() and not any(part in {".git",".pio",".gradle","build","__pycache__",".pytest_cache"} for part in p.relative_to(root).parts))

def read(root:Path,rel:str)->str:return (root/rel).read_text(encoding="utf-8",errors="strict")
def main()->int:
 parser=argparse.ArgumentParser();parser.add_argument("--root",default=".");root=Path(parser.parse_args().root).resolve();errors=[]
 for rel in REQUIRED:
  if not (root/rel).is_file():errors.append(f"missing required file: {rel}")
 fs=candidate_files(root)
 for path in fs:
  rel=path.relative_to(root)
  if path.name in FORBIDDEN_NAMES:errors.append(f"forbidden local/config file: {rel}")
  if any(part in FORBIDDEN_DIRS for part in rel.parts):errors.append(f"forbidden generated directory: {rel}")
  if path.suffix.lower() in FORBIDDEN_SUFFIXES:errors.append(f"forbidden generated artifact: {rel}")
  if path.stat().st_size>MAX_FILE_BYTES:errors.append(f"file exceeds 5 MiB: {rel}")
 contracts={
  "platformio.ini":[r"platform = espressif32@6\.13\.0",r"board = esp32dev",r"#7a5f53f54a9e66579582e12d1d0495572220e877"],
  "server/config_loader.py":[r"DEFAULT_GATEWAY_IPS = \{\}"],
  "server/server.py":[r"final_region = region\.strip\(\) if gateway_region_known else tag_declared_region",r'"tag_delivery_confirmed": False'],
  "esp32_tag/esp32_tag.ino":[r'\\"battery\\":null',r"esp_sleep_enable_ext1_wakeup",r"LoRa\s+DIO0"],
  "android_app/app/build.gradle":[r"minSdk 23",r"buildConfig true"],
  "android_app/gradle/wrapper/gradle-wrapper.properties":[r"gradle-8\.2-bin\.zip",r"38f66cd6eef217b4c35855bb11ea4e9fbc53594ccccb5fb82dfd317ef8c2c5a3"],
  "README.md":[r"当前提交尚未做端到端真机复测",r"不能唤醒深睡标签",r"`null/N/A`"],
 }
 for rel,patterns in contracts.items():
  try:content=read(root,rel)
  except (OSError,UnicodeError):continue
  for pattern in patterns:
   if not re.search(pattern,content):errors.append(f"fact contract missing in {rel}: {pattern}")
 scan_files=["README.md","docs/PROJECT_STATUS.md","docs/VERIFICATION.md","docs/HARDWARE_LAB_CARD.md"]
 forbidden=["system online","hardware re-verified: pass"]
 for rel in scan_files:
  try:content=read(root,rel).lower()
  except (OSError,UnicodeError):continue
  for claim in forbidden:
   if claim in content:errors.append(f"unsupported status claim in {rel}: {claim}")
 for rel in ["server/config_loader.py","android_app/app/src/main/java/com/warehouse/tracker/api/ApiClient.kt","android_app/app/src/main/res/xml/network_security_config.xml"]:
  try:content=read(root,rel)
  except (OSError,UnicodeError):continue
  if re.search(r"192\.168\.1\.\d+",content):errors.append(f"historical LAN address remains in {rel}")
 for rel in ["README.md","HARDWARE.md","SECURITY.md","THIRD_PARTY_NOTICES.md",*[
  str(path.relative_to(root)) for path in (root/"docs").glob("*.md")
 ]]:
  try:content=read(root,rel)
  except (OSError,UnicodeError):continue
  if "/home/rongyi/" in content or "/mnt/shared/" in content:
   errors.append(f"private absolute path remains in public documentation: {rel}")
 if errors:
  print("Repository check: FAIL",file=sys.stderr)
  for error in sorted(set(errors)):print(f"- {error}",file=sys.stderr)
  return 1
 print(f"Repository check: PASS ({len(fs)} files checked)");return 0
if __name__=="__main__":raise SystemExit(main())
