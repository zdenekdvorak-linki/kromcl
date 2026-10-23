# -*- coding: utf-8 -*-
"""Registr zdrojů.

Přidání dalšího zdroje = jeden nový modul vedle tohohle a jeden řádek v REGISTR.
Modul musí mít SOURCE_ID, SOURCE_NAME, fetch_items() a fetch_detail(item).
"""

from . import mesto_kromeriz

REGISTR = {
    mesto_kromeriz.SOURCE_ID: mesto_kromeriz,
}


def vsechny():
    return list(REGISTR.values())


def podle_id(source_id):
    return REGISTR[source_id]
