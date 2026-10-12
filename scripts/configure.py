"""Cria apenas configurações locais ausentes, sem sobrescrever as existentes."""
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / ".env"
if not path.exists():
    template = (ROOT / ".env.example").read_text(encoding="utf-8")
    template = template.replace("CHANGE_DATABASE_PASSWORD", secrets.token_hex(16))
    template = template.replace("CHANGE_JWT_SECRET", secrets.token_hex(32))
    path.write_text(template, encoding="utf-8")
    print(".env local criado; credenciais de demo em DEMO_PASSWORD.")
else:
    print(".env existente preservado.")
frontend = ROOT / "frontend/.env.local"
if not frontend.exists():
    frontend.write_text((ROOT / "frontend/.env.example").read_text(encoding="utf-8"), encoding="utf-8")
