#!/usr/bin/env python3
import sys
import argparse
import json
import re
import errno
from pathlib import Path
from typing import Optional, TextIO

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Expand Bible references in text with actual verses.'
    )
    parser.add_argument('version', 
                        help='Bible version to use (e.g., ESV, NASB)')
    parser.add_argument('-v', '--version', 
                        dest='version',
                        help='Bible version to use')
    parser.add_argument('-f', '--file',
                        type=argparse.FileType('r'),
                        metavar='INFILE',
                        help='Input file (default: stdin)')
    parser.add_argument('-o', '--out',
                        type=argparse.FileType('w'),
                        metavar='OUTFILE',
                        help='Output file (default: stdout)')
    parser.add_argument('-l', '--limit', '--limit-verses',
                        type=int,
                        metavar='N',
                        help='Ignores verse references if the amount of verses is more than N')
    parser.add_argument('-p', '--after-paragraph',
                        action='store_true',
                        help='Place verse after next newline')
    
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("Limit must be a positive integer")

    return args

def load_bible_version(version: str) -> dict:
    """Load the specified Bible version from JSON file."""
    try:
        version_path = Path(__file__).parent / 'translations' / f'bible_{version.lower()}.json'
        with open(version_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Bible version '{version}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in Bible version file", file=sys.stderr)
        sys.exit(1)

def load_book_names() -> dict[str, str]:
    """Load book names and their variations from books.json."""
    try:
        with open(Path(__file__).parent / 'books.json', 'r', encoding='utf-8') as f:
            books_data = json.load(f)
            book_map = {}
            for book in books_data:
                canonical = book['book']
                for name in book['names']:
                    book_map[name.lower()] = canonical
            return book_map
    except (FileNotFoundError, json.JSONDecodeError):
        print("Error: Could not load books.json", file=sys.stderr)
        sys.exit(1)

def find_bible_references(text: str) -> list[tuple[str, int, int]]:
    """Find all Bible references in text and return list of (reference, start, end) tuples."""
    # Load book names for validation
    book_names = load_book_names()
    
    # Pattern matches:
    # - Optional book number (1, 2, 3)
    # - Book name
    # - Chapter number
    # - Optional verse number
    # - Optional verse range
    # - Optional chapter-verse range
    pattern = r'\b(?:[123] ?)?[A-Za-z]+(?: [oO][fF] (?:(?i:Songs?)|(?i:Solomon)))? ?\d+:\d+(?:-\d+(?::\d+)?)?\b'
    references = []
    
    for match in re.finditer(pattern, text):
        ref = match.group()
        # Split into book name and reference
        parts = ref.split(' ')
        
        # Handle multi-word book names and extract book name
        if parts[0] in ('1', '2', '3'):
            book_name = ' '.join(parts[:2]).lower()
            ref_part = ' '.join(parts[2:])
        else:
            book_name = parts[0].lower()
            ref_part = ' '.join(parts[1:])
            
        # Validate book name
        if book_name in book_names:
            references.append((ref, match.start(), match.end()))
            
    return references

def parse_reference(reference: str, book_names: dict) -> tuple[str, int, Optional[int], Optional[int], Optional[int]]:
    """Parse a Bible reference into its components."""
    parts = reference.split(' ')
    
    # Handle book name (including multi-word books)
    if parts[0] in ('1', '2', '3'):
        book_name = ' '.join(parts[:2]).lower()
        ref_part = ' '.join(parts[2:])
    else:
        book_name = parts[0].lower()
        ref_part = ' '.join(parts[1:])
    
    canonical_book = book_names.get(book_name)
    if not canonical_book:
        return None
        
    # Parse chapter and verse references
    chapter_verse = ref_part.split(':')
    chapter = int(chapter_verse[0])
    
    start_verse = end_verse = None
    end_chapter = None
    
    if len(chapter_verse) > 1:
        verse_range = chapter_verse[1]
        if '-' in verse_range:
            # Handle verse ranges
            verse_parts = verse_range.split('-')
            start_verse = int(verse_parts[0])
            
            if ':' in verse_parts[1]:
                # Handle chapter-verse range (e.g., 1:1-2:3)
                chap_verse = verse_parts[1].split(':')
                end_chapter = int(chap_verse[0])
                end_verse = int(chap_verse[1])
            else:
                # Handle simple verse range (e.g., 1:1-3)
                end_verse = int(verse_parts[1])
        else:
            # Single verse
            start_verse = end_verse = int(verse_range)
            
    return canonical_book, chapter, start_verse, end_chapter or chapter, end_verse

def get_verse_text(reference: str, bible_data: dict) -> Optional[str]:
    """Get the verse text for a given reference."""
    book_names = load_book_names()
    parsed = parse_reference(reference, book_names)
    
    if not parsed:
        return None
        
    book, start_chapter, start_verse, end_chapter, end_verse = parsed
    
    # Find the book in the Bible data
    book_data = None
    for b in bible_data['books']:
        if b['book'] == book:
            book_data = b
            break
    
    if not book_data:
        return None
    
    verses = []
    
    # Skip if no specific verse is specified (chapter-only references)
    if start_verse is None:
        return None
        
    # Collect all verses in the range
    for chapter in range(start_chapter, end_chapter + 1):
        chapter_data = next((c for c in book_data['chapters'] if c['chapter'] == chapter), None)
        if not chapter_data:
            continue
            
        verse_start = start_verse if chapter == start_chapter else 1
        verse_end = end_verse if chapter == end_chapter else len(chapter_data['verses'])
        
        verses.extend(f"{v['verse']} {v['text']}" for v in chapter_data['verses'] if verse_start <= v['verse'] <= (verse_end or verse_start))
    
    if not verses:
        return None
        
    # Format the verses
    formatted_ref = f"{book} {start_chapter}"
    if start_verse:
        formatted_ref += f":{start_verse}"
        if end_verse and (end_chapter != start_chapter or end_verse != start_verse):
            if end_chapter != start_chapter:
                formatted_ref += f"-{end_chapter}:{end_verse}"
            else:
                formatted_ref += f"-{end_verse}"
    verse = ' '.join(verses)
    verse = re.sub(r'^\d+', '', verse)  # Remove leading verse number
    return verse

def process_text(text: str, bible_data: dict, after_paragraph: bool) -> str:
    """Process text and expand/insert Bible references."""
    if not text:
        return text
        
    references = find_bible_references(text)
    if not references:
        return text
    
    # Process references in reverse order to maintain correct string indices
    references.reverse()
    result = text
    
    for ref, start, end in references:
        verse_text = get_verse_text(ref, bible_data)
        if verse_text is None:
            # Skip invalid references but preserve the original text
            print(f"Warning: Could not process reference '{ref}'", file=sys.stderr)
            continue
            
        if after_paragraph:
            # Find the next newline after the reference
            next_newline = result.find('\n', end)
            if next_newline == -1:
                # If no newline found, append to end with proper spacing
                if not result.endswith('\n'):
                    result += '\n'
                result += verse_text + '\n'
            else:
                # Insert after the newline with proper spacing
                # Check if we need to add a newline after the verse
                needs_newline = not result[next_newline + 1:].startswith('\n')
                result = (
                    result[:next_newline + 1] +  # Keep text up to newline
                    verse_text +                  # Add verse text
                    ('\n' if needs_newline else '') +  # Add newline if needed
                    result[next_newline + 1:]     # Rest of the text
                )
        else:
            # Insert verse text right after the reference
            # Check if we need spaces around the verse text
            needs_space_before = result[end:end + 1].strip() != ''
            needs_space_after = result[end:end + 1].strip() != ''
            
            result = (
                result[:end] +
                (' ' if needs_space_before else '') +
                verse_text +
                (' ' if needs_space_after else '') +
                result[end:]
            )
    
    return result

def main():
    args = parse_arguments()
    bible_data = load_bible_version(args.version)
    
    try:
        # Handle input
        if args.file:
            # Read from specified file
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            # Let shell handle stdin (pipe, redirection, or interactive)
            text = sys.stdin.read()
            
        if not text.strip():
            return
            
        result = process_text(text, bible_data, args.after_paragraph)
        
        # Handle output
        if args.out:
            # Write to specified file
            with open(args.out, 'w', encoding='utf-8') as f:
                f.write(result)
        else:
            # Write to stdout
            try:
                sys.stdout.write(result)
                sys.stdout.flush()
            except BrokenPipeError:
                # Handle broken pipe (e.g., when piping to 'head')
                sys.stderr.close()
                sys.exit(0)
                
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except UnicodeError:
        print("Error: Invalid character encoding in input", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()


# place after paragraph needs to place in order found in paragraph, right now it is reverse order
# script should break up text by paragraphs, then process each paragraph for references, then reassemble
# implement limit
