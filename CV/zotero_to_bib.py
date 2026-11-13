#!/usr/bin/env python3
"""Regenerate publication.bib from the Zotero library (the master record).

CV-Amano.tex pulls entries from publication.bib by citation key
(\\bibentry{Amano2007a} etc.), so this script's main job is:

  1. Select the publication set from Zotero: top-level items of type
     journalArticle / conferencePaper where Amano is an author.
  2. Ask the Zotero API for those items in BibTeX format.
  3. Rewrite the result in this file's conventions:
       - citation keys already used in the current publication.bib are
         preserved (matched by DOI, then by normalised title), so the
         keys referenced from the .tex never change;
       - fields are limited to the ones the CV bibliography style uses
         (abstracts, URLs, ISSNs, language tags etc. are dropped);
       - a missing month is restored from the item's date in Zotero
         (the API's BibTeX export drops some months the desktop
         export used to emit);
       - entries are sorted by (year, first author, key);
       - formatting matches the historical file (2-space indent).
  4. Print a summary of what changed relative to the current file.

Usage (Web API; a private library needs a read-only API key):
    export ZOTERO_API_KEY=<your Zotero API key>
    python3 zotero_to_bib.py            # rewrite publication.bib
    python3 zotero_to_bib.py --dry-run  # report only, write nothing

Usage (no key; talks to the Zotero desktop app on this machine):
    python3 zotero_to_bib.py --local

The Web API key is taken from the environment only; create one at
https://www.zotero.org/settings/keys . A private library cannot be
read without a key (the API answers 403), so without a key either use
--local with the Zotero desktop app running (Zotero 7's local API
needs no key), or make the library public.
The user ID defaults to the library owner's and can be overridden with
--user-id or the ZOTERO_USER_ID environment variable.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.zotero.org"
LOCAL_API_BASE = "http://localhost:23119/api"
DEFAULT_USER_ID = "13150460"
BASE = API_BASE  # switched by --local in main()
ITEM_TYPES = ("journalArticle", "conferencePaper")

# Fields kept in the output, in the order they are printed.
FIELD_ORDER = [
    "title", "author", "editor", "year", "month", "journal", "booktitle",
    "volume", "number", "series", "pages", "publisher", "address",
    "edition", "doi", "isbn",
]

MONTH_MACROS = ["jan", "feb", "mar", "apr", "may", "jun",
                "jul", "aug", "sep", "oct", "nov", "dec"]
MONTH_NAMES = {name: i + 1 for i, name in enumerate([
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december"])}

# How the owner appears as a creator in the library.
OWNER_LASTNAME = "Amano"
OWNER_FIRSTNAME_PREFIX = "T"
OWNER_SINGLE_NAMES = {"Takanobu Amano", "T. Amano", "T Amano"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused; check the API endpoint")


def api_get(path, api_key, accept_json=True):
    headers = {"Zotero-API-Version": "3", "User-Agent": "zotero_to_bib.py"}
    if api_key:
        headers["Zotero-API-Key"] = api_key
    req = urllib.request.Request(BASE + path, headers=headers)
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            total = resp.headers.get("Total-Results")
    except urllib.error.HTTPError as exc:
        if exc.code == 403 and BASE == API_BASE and not api_key:
            raise RuntimeError(
                "the Zotero API refused an unauthenticated request (403): "
                "a private library needs a read-only API key in "
                "ZOTERO_API_KEY, or use --local with the Zotero desktop "
                "app running") from exc
        if exc.code in (400, 403) and BASE != API_BASE:
            raise RuntimeError(
                "the Zotero local API refused the request: is the "
                "Zotero desktop app running, with local integration "
                "allowed in its advanced settings?") from exc
        raise
    except urllib.error.URLError as exc:
        if BASE != API_BASE:
            raise RuntimeError(
                "could not reach the Zotero local API at "
                f"{BASE}: is the Zotero desktop app running?") from exc
        raise RuntimeError(f"could not reach the Zotero API: {exc}") from exc
    if accept_json:
        return json.loads(body), (int(total) if total is not None else None)
    return body, None


def is_owner_creator(creator):
    if creator.get("creatorType", "author") != "author":
        return False
    last = creator.get("lastName") or ""
    first = creator.get("firstName") or ""
    if last == OWNER_LASTNAME and first.startswith(OWNER_FIRSTNAME_PREFIX):
        return True
    return (creator.get("name") or "") in OWNER_SINGLE_NAMES


def select_publication_keys(user_id, api_key):
    """Return (item keys, date lookup) for the publication set.

    The date lookup maps normalised DOI and normalised title to the
    item's raw Zotero date, for restoring months after the BibTeX fetch.
    """
    keys, date_by_doi, date_by_title = [], {}, {}
    for item_type in ITEM_TYPES:
        start, total = 0, None
        while total is None or start < total:
            path = (
                f"/users/{user_id}/items/top?format=json"
                f"&itemType={item_type}&limit=100&start={start}"
            )
            payload, total = api_get(path, api_key)
            if total is None:
                total = start + len(payload)
            for item in payload:
                data = item.get("data", {})
                if any(is_owner_creator(c) for c in data.get("creators", [])):
                    if data.get("title"):
                        keys.append(item["key"])
                        date = data.get("date") or ""
                        doi = (data.get("DOI") or "").strip().lower()
                        if doi:
                            date_by_doi[doi] = date
                        date_by_title[normalise_title(data["title"])] = date
            start += len(payload) if payload else 100
    return keys, (date_by_doi, date_by_title)


def month_macro(date_str):
    """Extract a BibTeX month macro (jan..dec) from a Zotero date.

    Handles the formats present in the library: ISO (2026-11-13,
    2026-1-5), month-year (5 2007, 11/2024), Japanese (2026年11月)
    and English month names (May 2007).
    """
    if not date_str:
        return None
    s = date_str.strip()
    m = re.search(r"\d{4}-(\d{1,2})(?:-\d{1,2})?\b", s)
    if m and 1 <= int(m.group(1)) <= 12:
        return MONTH_MACROS[int(m.group(1)) - 1]
    m = re.search(r"(\d{1,2})月", s)
    if m and 1 <= int(m.group(1)) <= 12:
        return MONTH_MACROS[int(m.group(1)) - 1]
    m = re.fullmatch(r"(\d{1,2})[ /](\d{4})", s)
    if m and 1 <= int(m.group(1)) <= 12:
        return MONTH_MACROS[int(m.group(1)) - 1]
    for name, num in MONTH_NAMES.items():
        if re.search(rf"\b{name}\b", s, re.IGNORECASE):
            return MONTH_MACROS[num - 1]
    return None


def fetch_bibtex(user_id, api_key, keys):
    chunks = []
    for i in range(0, len(keys), 50):
        batch = ",".join(keys[i:i + 50])
        path = (
            f"/users/{user_id}/items?format=bibtex"
            f"&itemKey={urllib.parse.quote(batch, safe=',')}"
        )
        body, _ = api_get(path, api_key, accept_json=False)
        chunks.append(body)
    return "\n".join(chunks)


# --- Minimal BibTeX parsing (brace-aware) ---------------------------------

def parse_bibtex(text):
    """Parse entries into {key: (type, {field: (value, was_braced)})}."""
    entries = {}
    order = []
    i, n = 0, len(text)
    while True:
        m = re.search(r"@(\w+)\s*\{", text[i:])
        if not m:
            break
        entry_type = m.group(1).lower()
        pos = i + m.end()  # just after '{'
        comma = text.index(",", pos)
        key = text[pos:comma].strip()
        pos = comma + 1
        fields = {}
        while pos < n:
            while pos < n and text[pos] in " \t\r\n,":
                pos += 1
            if pos >= n or text[pos] == "}":
                pos += 1
                break
            fm = re.match(r"(\w+)\s*=\s*", text[pos:])
            if not fm:
                break
            name = fm.group(1).lower()
            pos += fm.end()
            if pos < n and text[pos] == "{":
                depth, start = 0, pos
                while pos < n:
                    if text[pos] == "{":
                        depth += 1
                    elif text[pos] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    pos += 1
                fields[name] = (text[start + 1:pos], True)
                pos += 1
            elif pos < n and text[pos] == '"':
                end = text.index('"', pos + 1)
                fields[name] = (text[pos + 1:end], True)
                pos = end + 1
            else:
                vm = re.match(r"[^\s,}]+", text[pos:])
                fields[name] = (vm.group(0), False)
                pos += vm.end()
        entries[key] = (entry_type, fields)
        order.append(key)
        i = pos
    return entries, order


def normalise_title(value):
    t = re.sub(r"[{}\\]", "", value or "")
    t = re.sub(r"[^0-9A-Za-z\u0080-\uffff]+", " ", t).strip().lower()
    return t


def normalise_doi(fields):
    raw = fields.get("doi", ("", True))[0]
    doi = re.sub(r"[{}\s]", "", raw).lower()
    return doi.replace("https://doi.org/", "").replace("http://doi.org/", "")


def first_author_surname(fields):
    author = fields.get("author", ("", True))[0]
    first = re.split(r"\s+and\s+", author)[0]
    surname = first.split(",")[0] if "," in first else first.split()[-1]
    return re.sub(r"[{}\\]", "", surname).strip().lower()


def entry_year(fields):
    raw = re.sub(r"\D", "", fields.get("year", ("", True))[0])
    return int(raw) if raw else 9999


def restore_months(new_entries, date_lookup):
    """Fill in a missing month from the item's Zotero date."""
    date_by_doi, date_by_title = date_lookup
    for _, fields in new_entries.values():
        if "month" in fields:
            continue
        date = date_by_doi.get(normalise_doi(fields)) or date_by_title.get(
            normalise_title(fields.get("title", ("", True))[0]), "")
        macro = month_macro(date)
        if macro:
            fields["month"] = (macro, False)


def normalise_numbers(new_entries):
    """Strip leading zeros from purely numeric issue numbers (05 -> 5)."""
    for _, fields in new_entries.values():
        if "number" in fields:
            value, braced = fields["number"]
            if re.fullmatch(r"0\d+", value.strip()):
                fields["number"] = (str(int(value)), braced)


def preserve_keys(new_entries, old_entries):
    """Rename new entries to the keys the current .bib already uses.

    Matching is by DOI first, then by (normalised title, year), then by
    normalised title. Returns (old_key, api_key) renames applied.
    """
    by_doi, by_title_year, by_title = {}, {}, {}
    for key, (_, fields) in old_entries.items():
        doi = normalise_doi(fields)
        if doi:
            by_doi.setdefault(doi, key)
        title = normalise_title(fields.get("title", ("", True))[0])
        by_title_year.setdefault((title, entry_year(fields)), key)
        by_title.setdefault(title, key)
    renames = []
    taken = set(new_entries)
    for key in list(new_entries):
        _, fields = new_entries[key]
        title = normalise_title(fields.get("title", ("", True))[0])
        match = (by_doi.get(normalise_doi(fields))
                 or by_title_year.get((title, entry_year(fields)))
                 or by_title.get(title))
        if match and match != key:
            if match in taken:
                print(f"warning: key {match} already taken; keeping {key}",
                      file=sys.stderr)
                continue
            new_entries[match] = new_entries.pop(key)
            taken.discard(key)
            taken.add(match)
            renames.append((match, key))
    return renames


def format_entries(entries):
    def sort_key(item):
        key, (_, fields) = item
        return (entry_year(fields), first_author_surname(fields), key)

    blocks = []
    for key, (entry_type, fields) in sorted(entries.items(), key=sort_key):
        lines = [f"@{entry_type}{{{key},"]
        kept = [f for f in FIELD_ORDER if f in fields]
        for idx, name in enumerate(kept):
            value, braced = fields[name]
            rendered = f"{{{value}}}" if braced else value
            comma = "," if idx < len(kept) - 1 else ""
            lines.append(f"  {name} = {rendered}{comma}")
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def filter_fields(entries):
    keep = set(FIELD_ORDER)
    for _, fields in entries.values():
        for name in list(fields):
            if name not in keep:
                del fields[name]


def summarise(old_entries, new_entries):
    lines = []
    added = sorted(set(new_entries) - set(old_entries))
    removed = sorted(set(old_entries) - set(new_entries))
    if added:
        lines.append(f"added ({len(added)}): {', '.join(added)}")
    if removed:
        lines.append(f"removed ({len(removed)}): {', '.join(removed)}")
    changed = []
    for key in sorted(set(old_entries) & set(new_entries)):
        _, of = old_entries[key]
        _, nf = new_entries[key]
        diffs = []
        for name in sorted(set(of) | set(nf)):
            ov = re.sub(r"\s+", " ", of.get(name, ("", True))[0]).strip()
            nv = re.sub(r"\s+", " ", nf.get(name, ("", True))[0]).strip()
            # brace-only differences are formatting, not content
            ov = re.sub(r"[{}]", "", ov)
            nv = re.sub(r"[{}]", "", nv)
            if name == "doi":
                ov, nv = ov.lower(), nv.lower()
            if ov != nv:
                diffs.append(name)
        if diffs:
            changed.append(f"{key}: {', '.join(diffs)}")
    if changed:
        lines.append(f"changed ({len(changed)}):")
        lines.extend(f"  {c}" for c in changed)
    if not lines:
        lines.append("no changes")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user-id", default=os.environ.get(
        "ZOTERO_USER_ID", DEFAULT_USER_ID))
    parser.add_argument("--output", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "publication.bib"))
    parser.add_argument("--dry-run", action="store_true",
                        help="print the change summary without writing")
    parser.add_argument("--local", action="store_true",
                        help="use the Zotero desktop app's local API "
                             "(no API key; Zotero must be running)")
    args = parser.parse_args()

    global BASE
    api_key = os.environ.get("ZOTERO_API_KEY")
    if args.local:
        BASE = LOCAL_API_BASE
        args.user_id = "0"
        api_key = None
    elif not api_key:
        print("note: no ZOTERO_API_KEY set; trying anonymously "
              "(works only if the library is public)", file=sys.stderr)

    try:
        keys, date_lookup = select_publication_keys(args.user_id, api_key)
        print(f"selected {len(keys)} items from Zotero", file=sys.stderr)
        bib_text = fetch_bibtex(args.user_id, api_key, keys)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    new_entries, _ = parse_bibtex(bib_text)
    filter_fields(new_entries)
    restore_months(new_entries, date_lookup)
    normalise_numbers(new_entries)

    old_entries = {}
    if os.path.exists(args.output):
        with open(args.output, encoding="utf-8") as fh:
            old_entries, _ = parse_bibtex(fh.read())
        # compare on the same field profile as the generated output
        filter_fields(old_entries)
    renames = preserve_keys(new_entries, old_entries)
    for kept, api_key_name in renames:
        print(f"key preserved: {api_key_name} -> {kept}", file=sys.stderr)

    for line in summarise(old_entries, new_entries):
        print(line)

    if not args.dry_run:
        header = ("% Generated from the Zotero library by zotero_to_bib.py.\n"
                  "% Do not edit by hand; update Zotero and re-run the script.\n\n")
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(header + format_entries(new_entries))
        print(f"wrote {args.output} ({len(new_entries)} entries)",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
