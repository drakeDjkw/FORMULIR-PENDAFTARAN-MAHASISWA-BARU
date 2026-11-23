"""
Compiles locale/*/LC_MESSAGES/django.po into django.mo without GNU gettext.

Django's own `python manage.py compilemessages` needs the gettext tools (on macOS: `brew install gettext`).
This script does the same job in pure Python, so it works everywhere:

    python tools/compile_messages.py
"""

import ast
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse_po(text):
    """Returns {msgid: msgstr}, including the header entry (msgid "")."""
    messages, msgid, msgstr, section = {}, None, None, None

    def flush():
        if msgid is not None and msgstr is not None:
            messages[msgid] = msgstr

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("msgid "):
            flush()
            msgid, msgstr, section = ast.literal_eval(line[6:]), None, "id"
        elif line.startswith("msgstr "):
            msgstr, section = ast.literal_eval(line[7:]), "str"
        elif line.startswith('"'):
            if section == "id":
                msgid += ast.literal_eval(line)
            else:
                msgstr += ast.literal_eval(line)
    flush()
    return messages


def build_mo(messages):
    """GNU .mo format: a header, two tables of (length, offset), then the strings."""
    keys = sorted(messages)
    ids = [k.encode("utf-8") for k in keys]
    strs = [messages[k].encode("utf-8") for k in keys]
    count = len(keys)
    header_size = 7 * 4
    ids_table = header_size
    strs_table = ids_table + count * 8
    data_start = strs_table + count * 8

    offsets, data = [], b""
    for item in ids + strs:
        offsets.append((len(item), data_start + len(data)))
        data += item + b"\0"

    out = struct.pack("<7I", 0x950412DE, 0, count, ids_table, strs_table, 0, 0)
    for length, offset in offsets:
        out += struct.pack("<2I", length, offset)
    return out + data


def main():
    for po in sorted(ROOT.glob("locale/*/LC_MESSAGES/*.po")):
        messages = {k: v for k, v in parse_po(po.read_text(encoding="utf-8")).items() if v}
        po.with_suffix(".mo").write_bytes(build_mo(messages))
        print(f"{po.relative_to(ROOT)}: {len(messages) - 1} messages")


if __name__ == "__main__":
    main()
