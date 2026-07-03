from __future__ import annotations

from app.sync.suppliers import pooltechnika

# Supplier code -> adapter module (fetch + parse). Shared by API triggers, repull and CLI.
ADAPTERS = {pooltechnika.CODE: pooltechnika}
