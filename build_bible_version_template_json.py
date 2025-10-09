#!/usr/bin/env python3
import argparse
import csv
import json
from collections import defaultdict

REQUIRED_CSV_COLS = {
    "reference_id", "book_sequence", "book_abbrev", "chapter", "verse", "verse_sequence"
}

def load_books(path):
    with open(path, "r", encoding="utf-8") as f:
        books = json.load(f)
    # Map any provided name -> canonical book object
    name_to_book = {}
    for b in books:
        for n in b.get("names", []):
            name_to_book[n.strip().lower()] = b
        name_to_book[b["book"].strip().lower()] = b
    return books, name_to_book

def read_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        rdr = csv.DictReader(f)
        print(rdr.fieldnames)
        missing = REQUIRED_CSV_COLS - set(rdr.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")
        for r in rdr:
            r["book_sequence"]   = int(r["book_sequence"])
            r["chapter"]         = int(r["chapter"])
            r["verse"]           = int(r["verse"])
            r["verse_sequence"]  = int(r["verse_sequence"])
            r["book_abbrev"]     = r["book_abbrev"].strip()
            rows.append(r)
    return rows

def build_output(books_meta, name_map, refs):
    # Group refs by canonical book name resolved via 3-letter abbrev
    per_book = defaultdict(list)
    for r in refs:
        key = r["book_abbrev"].lower()
        # Per instructions, abbrev always exists in names
        canonical_book = name_map[key]["book"]
        per_book[canonical_book].append(r)

    # Derive book_sequence from CSV rows
    book_seq = {bname: min(r["book_sequence"] for r in rows)
                for bname, rows in per_book.items()}

    # Canonical metadata
    meta_by_name = {b["book"]: b for b in books_meta}

    # Order books by book_sequence
    ordered_books = sorted(per_book.keys(), key=lambda b: book_seq[b])

    # Build chapters and verses per book (chapter_sequence assigned later globally)
    books_out = []
    chapters_index = []  # (book_name, chapter_obj) to assign global chapter_sequence later
    for bname in ordered_books:
        meta = meta_by_name[bname]
        rows = per_book[bname]

        # Group by chapter
        by_chapter = defaultdict(list)
        for r in rows:
            by_chapter[r["chapter"]].append(r)

        chapter_objs = []
        for chap_num in sorted(by_chapter.keys()):
            vrows = by_chapter[chap_num]
            vrows.sort(key=lambda x: (x["verse_sequence"], x["verse"]))
            verses = [{
                "heading": None,
                "verse_sequence": vr["verse_sequence"],
                "verse": vr["verse"],
                "text": None,
                "cross_references": {"refers_to": [], "refers_me": []},
                "footnotes": []
            } for vr in vrows]

            ch_obj = {
                "chapter": chap_num,
                "chapter_sequence": None,   # fill later
                "num_verses": len(verses),
                "verses": verses
            }
            chapter_objs.append(ch_obj)
            chapters_index.append((bname, ch_obj))

        books_out.append({
            "book": bname,
            "book_sequence": book_seq[bname],
            "testament": meta.get("testament"),
            "names": meta.get("names", []),
            "num_chapters": len(chapter_objs),
            "chapters": chapter_objs
        })

    # Assign global chapter_sequence across all books ordered by book_sequence then chapter number
    # chapters_index is already in that order
    for i, (_bname, ch_obj) in enumerate(chapters_index, start=1):
        ch_obj["chapter_sequence"] = i

    return books_out

def main():
    ap = argparse.ArgumentParser(description="Build nested Bible JSON from books.json and references CSV.")
    ap.add_argument("--books", required=True, help="Path to books JSON")
    ap.add_argument("--csv", required=True, help="Path to references CSV")
    ap.add_argument("--out", required=True, help="Path to write output JSON")
    ap.add_argument("--indent", type=int, default=4, help="JSON indent (default 4)")
    args = ap.parse_args()

    books_meta, name_map = load_books(args.books)
    refs = read_csv(args.csv)
    books = build_output(books_meta, name_map, refs)

    out = {
        "name": None,
        "initials": None,
        "version": None,
        "citation": None,
        "books": books
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=args.indent)

if __name__ == "__main__":
    main()
