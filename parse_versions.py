#!/usr/bin/env python3
"""Parse BibleGatewayVersions.html and extract Bible version information."""

import re
from pathlib import Path
from bs4 import BeautifulSoup

def parse_versions(html_path: str):
    """Parse the HTML file and extract version shortnames, long names, and language."""
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    versions = []
    current_language = None
    
    # Find all option elements
    options = soup.find_all('option')
    
    for option in options:
        value = option.get('value', '')
        text = option.get_text(strip=True)
        option_class = option.get('class', [])
        
        # Check if this is a language header
        if 'lang' in option_class:
            # Extract language from the text (between --- markers)
            # Format: "---Language Name (CODE)---"
            lang_match = re.search(r'---(.+?)\s*\(([A-Z\-]+)\)---', text)
            if lang_match:
                current_language = {
                    'langname': lang_match.group(1).strip(),
                    'langcode': lang_match.group(2).strip()
                }
            else:
                # Fallback if format doesn't match
                fallback_match = re.search(r'---(.+?)---', text)
                if fallback_match:
                    lang_text = fallback_match.group(1).strip()
                    current_language = {
                        'langname': lang_text,
                        'langcode': None
                    }
            continue
        
        # Skip spacers
        if 'spacer' in option_class:
            continue
        
        # Skip empty options
        if not value or not text:
            continue
        
        # Extract the shortname from the text (usually in parentheses at the end)
        # Format is typically: "Long Name (SHORTNAME)"
        match = re.search(r'\(([A-Z0-9\-]+)\)\s*$', text)
        if match:
            shortname = match.group(1)
            # Remove the shortname from the text to get the long name
            longname = text[:match.start()].strip()
        else:
            # If no match, use the value as shortname and text as longname
            shortname = value
            longname = text
        
        versions.append({
            'shortname': shortname,
            'longname': longname,
            'langname': current_language['langname'] if current_language else None,
            'langcode': current_language['langcode'] if current_language else None
        })
    
    return versions

def main():
    html_path = Path(__file__).parent / 'BibleGatewayVersions.html'
    
    if not html_path.exists():
        print(f"Error: {html_path} not found")
        return
    
    versions = parse_versions(html_path)
    
    print(f"Found {len(versions)} Bible versions:\n")
    print(f"{'Shortname':<20} {'Lang Code':<12} {'Language Name':<30} {'Long Name'}")
    print("-" * 110)
    
    for v in versions:
        langcode = v['langcode'] or 'N/A'
        langname = v['langname'] or 'Unknown'
        print(f"{v['shortname']:<20} {langcode:<12} {langname:<30} {v['longname']}")
    
    # Optionally save to JSON
    import json
    output_path = Path(__file__).parent / 'bible_versions.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Versions saved to {output_path}")

if __name__ == '__main__':
    main()
