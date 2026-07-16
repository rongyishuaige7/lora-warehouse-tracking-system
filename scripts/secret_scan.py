#!/usr/bin/env python3
"""Fail on likely credentials or private keys in release-candidate files."""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS={".git",".pio",".gradle",".venv","venv","__pycache__","build"}
TEXT_SUFFIXES={"",".c",".cc",".cpp",".h",".hpp",".ini",".md",".py",".txt",".yml",".yaml",".json",".csv",".xml",".gradle",".properties",".svg"}
PATTERNS=[
 ("private key",re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
 ("GitHub token",re.compile(r"\b(?:gh[opusr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
 ("AWS access key",re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
 ("generic assigned secret",re.compile(r'''(?ix)\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|passwd|pwd)\b\s*[:=]\s*["']?(?!YOUR_|EXAMPLE|REPLACE|CHANGEME|REDACTED|<)([A-Za-z0-9+/=_!@#$%^&*.-]{8,})''')),
]
ALLOWED={"YOUR_WIFI_SSID","YOUR_WIFI_PASSWORD","你的本地密码","[REDACTED]"}

def files(root:Path)->list[Path]:
 try: raw=subprocess.run(["git","-C",str(root),"ls-files","-z"],check=True,capture_output=True).stdout
 except (subprocess.CalledProcessError,FileNotFoundError): raw=b""
 if raw: return [root/p.decode("utf-8","surrogateescape") for p in raw.split(b"\0") if p]
 return sorted(p for p in root.rglob("*") if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(root).parts))

def main()->int:
 parser=argparse.ArgumentParser();parser.add_argument("--root",default=".");root=Path(parser.parse_args().root).resolve();hits=[]
 for path in files(root):
  if not path.exists() or path.stat().st_size>2_000_000 or path.suffix.lower() not in TEXT_SUFFIXES: continue
  try: content=path.read_text(encoding="utf-8")
  except (UnicodeDecodeError,OSError): continue
  for line_no,line in enumerate(content.splitlines(),1):
   if any(value in line for value in ALLOWED): continue
   for label,pattern in PATTERNS:
    if pattern.search(line): hits.append(f"{path.relative_to(root)}:{line_no}: {label}")
 if hits:
  print("Secret scan: FAIL",file=sys.stderr);print("\n".join(hits),file=sys.stderr);return 1
 print("Secret scan: PASS");return 0
if __name__=="__main__": raise SystemExit(main())
