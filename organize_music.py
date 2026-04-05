#!/usr/bin/env python3
"""
MP3/M4A Organizer - Organizes audio files by genre or label based on metadata and online lookup.
"""
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import json
import os
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, Optional, Tuple
import urllib.parse
import urllib.request


def _extract_all_metadata(file_path: Path) -> Dict[str, Optional[str]]:
    """
    Extract all metadata tags from audio file in a single ffprobe call.

    Args:
        file_path: Path to audio file

    Returns:
        Dict with keys: artist, title, album, genre, date, label, Label, TPUB, publisher, track
    """
    result = {
        'artist': None, 'title': None, 'album': None, 'genre': None,
        'date': None, 'label': None, 'Label': None, 'TPUB': None,
        'publisher': None, 'track': None
    }

    try:
        proc = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format_tags',
             '-of', 'json', str(file_path)],
            capture_output=True, text=True, timeout=10
        )
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout)
            tags = data.get('format', {}).get('tags', {})
            for key in result:
                val = tags.get(key)
                if val and val.strip():
                    result[key] = val.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        pass

    return result


def _extract_metadata_tag(file_path: Path, tag: str) -> Optional[str]:
    """
    Extract a specific tag from audio file metadata.
    
    Args:
        file_path: Path to audio file
        tag: Metadata tag to extract
        
    Returns:
        Tag value if found, None otherwise
    """
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', f'format_tags={tag}', 
             '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None


def _write_metadata_tag(file_path: Path, tag: str, value: str) -> bool:
    """
    Write a specific tag to audio file metadata.
    
    Args:
        file_path: Path to audio file
        tag: Metadata tag to write
        value: Value to write for the tag
        
    Returns:
        True if successful, False otherwise
    """
    try:
        escaped_value = value.replace("'", "'\\''")
        suffix = file_path.suffix.lower()
        temp_path = str(file_path) + '.tmp' + suffix
        
        cmd = [
            'ffmpeg', '-i', str(file_path),
            '-map', '0',
            '-metadata', f'{tag}={escaped_value}',
            '-codec', 'copy',
            '-id3v2_version', '3',
            '-y',
            temp_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            os.replace(temp_path, str(file_path))
            return True
        else:
            logger.warning(f"Failed to write metadata tag {tag} to {file_path}: {result.stderr[:200]}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        logger.warning(f"Error writing metadata tag {tag} to {file_path}: {str(e)}")
        temp_path = str(file_path) + '.tmp' + suffix if 'suffix' in locals() else str(file_path) + '.tmp'
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return False


def get_label_from_metadata(file_path: Path, label_source_tag: Optional[str]) -> Optional[str]:
    """
    Extract label from audio file metadata only.
    
    Args:
        file_path: Path to audio file
        label_source_tag: Optional specific tag to check (with uppercase variant)
        
    Returns:
        Label string if found, None otherwise
    """
    # Common label-related tags to check
    label_tags = ['label', 'Label', 'TPUB', 'publisher']
    if label_source_tag:
        label_tags = [label_source_tag, label_source_tag.upper()]
    
    for tag in label_tags:
        tag_value = _extract_metadata_tag(file_path, tag)
        if tag_value is not None:
            return tag_value
    
    return None


def get_genre_from_metadata(file_path: Path) -> Optional[str]:
    """
    Extract genre from audio file metadata only.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Genre string if found, None otherwise
    """
    return _extract_metadata_tag(file_path, 'genre')


def lookup_label_online(artist: str, title: str) -> Optional[str]:
    """
    Lookup label via online services (iTunes primary with track ID lookup).
    Falls back to Bandcamp if iTunes fails.
    
    Args:
        artist: Artist name
        title: Track title
        
    Returns:
        Label string if found, None otherwise
    """
    itunes_data = _lookup_itunes_all_metadata(artist, title)
    if itunes_data.get('label'):
        return itunes_data['label']
    
    _, bandcamp_label = get_genre_from_bandcamp(artist, title)
    if bandcamp_label:
        return bandcamp_label
    
    return None


def _lookup_itunes_all_metadata(artist: str, title: str) -> Dict[str, Optional[str]]:
    """
    Single iTunes lookup returning all available metadata.
    
    Returns dict with keys: label, genre, album, year, track_number, artist, title
    """
    result = {
        'label': None, 'genre': None, 'album': None,
        'year': None, 'track_number': None,
        'artist': None, 'title': None
    }
    
    try:
        query = urllib.parse.quote(f"{artist} {title}")
        url = f"https://itunes.apple.com/search?term={query}&entity=musicTrack&attribute=songTerm&limit=5"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data['resultCount'] > 0:
                for track in data['results'][:3]:
                    label = track.get('label')
                    if label and label.strip():
                        result['label'] = label.strip()
                        break
                    elif 'trackId' in track:
                        track_id = track['trackId']
                        detail_url = f"https://itunes.apple.com/lookup?id={track_id}"
                        with urllib.request.urlopen(detail_url, timeout=10) as detail_response:
                            detail_data = json.loads(detail_response.read().decode())
                            if detail_data['resultCount'] > 0:
                                detail_label = detail_data['results'][0].get('label')
                                if detail_label and detail_label.strip():
                                    result['label'] = detail_label.strip()
                                    break
                
                first = data['results'][0]
                result['genre'] = first.get('primaryGenreName')
                result['album'] = first.get('collectionName')
                result['track_number'] = first.get('trackNumber')
                release_date = first.get('releaseDate')
                if release_date:
                    result['year'] = release_date[:4] if len(release_date) >= 4 else None
                result['artist'] = first.get('artistName')
                result['title'] = first.get('trackName')
    except Exception:
        pass
    
    return result


def get_additional_metadata_online(artist: str, title: str) -> Dict[str, Optional[str]]:
    """
    Lookup additional metadata (album, year, track_number) from online services.
    Uses the unified iTunes lookup to avoid redundant API calls.
    """
    itunes_data = _lookup_itunes_all_metadata(artist, title)
    return {
        'album': itunes_data.get('album'),
        'year': itunes_data.get('year'),
        'track_number': itunes_data.get('track_number'),
    }


def find_label_destination(label: str, label_to_dest: Dict[str, str]) -> Optional[str]:
    """
    Find destination folder for a given label.
    
    Args:
        label: Label name to map
        label_to_dest: Mapping of label strings to destination paths
        
    Returns:
        Destination path if label is mapped, None otherwise
    """
    # Normalize label for comparison
    normalized_label = label.lower().strip()
    
    # Special case: if label contains both "drum" and "bass" -> map to "Drum n Base"
    if 'drum' in normalized_label and 'bass' in normalized_label:
        normalized_label = 'drum n base'
    
    # Look for exact match in config (keys are normalized to lowercase)
    for config_key, dest in label_to_dest.items():
        if normalized_label == config_key.lower().strip():
            return dest
        # Also check if config key contains comma-separated values
        if ',' in config_key:
            for part in config_key.split(','):
                if normalized_label == part.lower().strip():
                    return dest
    
    return None


def get_genre_from_metadata(file_path: Path) -> Optional[str]:
    """
    Extract genre from audio file metadata only.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Genre string if found, None otherwise
    """
    return _extract_metadata_tag(file_path, 'genre')


# Cache for genre lookups to avoid repeated API calls
_genre_cache = {}
_bandcamp_cache = {}

def _is_electronic_genre(genre: str) -> bool:
    """Check if a genre is likely electronic music."""
    if not genre:
        return False
    
    genre_lower = genre.lower().strip()
    
    electronic_keywords = {
        'electronic', 'techno', 'house', 'trance', 'drum and bass', 'drum n bass', 
        'drum & bass', 'jungle', 'dubstep', 'electronica', 'ambient', 'industrial',
        'edm', 'dance', 'garage', 'breakbeat', 'hardcore', 'hard house', 'progressive',
        'minimal', 'deep house', 'tech house', 'acid house', 'hard techno', 'hard trance',
        'gabber', 'happy hardcore', 'uk garage', '2step', 'breaks', 'electro', 'synthpop',
        'idm', 'intelligent dance music', 'chiptune', 'glitch', 'hardstyle', 'hardcore techno',
        'power noise', 'noisecore', 'dark ambient', 'vrtechno', 'hard dance', 
        'nu skool breaks', 'funky breaks', 'bassline', 'uk funky', 'future garage', 
        'post dubstep', 'future bass', 'trap', 'downtempo', 'chillout', 'lounge', 
        'nu jazz', 'electro swing', 'electroclash', 'new rave', 'bleep', 'bmore club', 
        'baltimore club', 'ghetto house', 'juke', 'footwork', 'seapunk', 'vaporwave', 
        'cloud rap', 'witch house', 'salem', 'drag'
    }
    
    for keyword in electronic_keywords:
        if keyword in genre_lower:
            return True
    
    label_indicators = ['records', 'music', 'sound', 'audio', 'trax', 'beats', 'sounds']
    for indicator in label_indicators:
        if indicator in genre_lower and len(genre_lower) < 20:
            return True
            
    return False


def get_genre_from_bandcamp(artist: str, title: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Lookup genre and label via Bandcamp search.
    Bandcamp is excellent for electronic music genres as artists explicitly tag their music.
    
    Args:
        artist: Artist name
        title: Track title
        
    Returns:
        Tuple of (genre, label) or (None, None) if not found
    """
    cache_key = f"{artist.lower()}:{title.lower()}"
    if cache_key in _bandcamp_cache:
        return _bandcamp_cache[cache_key]
    
    result = (None, None)
    
    try:
        query = urllib.parse.quote(f"{artist} {title}")
        search_url = f"https://bandcamp.com/search?q={query}&item_type=t"
        
        request = urllib.request.Request(
            search_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        
        with urllib.request.urlopen(request, timeout=10) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
            
            result = _parse_bandcamp_search_results(html_content, artist, title)
            
            if result[0] is None:
                result = _parse_bandcamp_from_json_ld(html_content)
                
            if result[0] is None and result[1] is None:
                result = _try_direct_bandcamp_url(artist, title)
            
            if result[0] is not None or result[1] is not None:
                _bandcamp_cache[cache_key] = result
                return result
                
    except Exception:
        pass
    
    _bandcamp_cache[cache_key] = (None, None)
    return (None, None)


def _try_direct_bandcamp_url(artist: str, title: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Try to access Bandcamp page directly using artist name.
    Uses multiple URL pattern variations to find the track.
    """
    artist_slug = artist.lower().replace(' ', '-').replace('&', '').replace("'", '').strip()
    title_slug = title.lower().replace(' ', '-').replace('(', '').replace(')', '').replace('[', '').replace(']', '').replace("'", '').replace('&', '').strip()
    
    url_patterns = [
        f"https://{artist_slug}.bandcamp.com/track/{title_slug}",
        f"https://{artist_slug}.bandcamp.com/track/{artist_slug}-{title_slug}",
    ]
    
    for url in url_patterns:
        try:
            request = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    html_content = response.read().decode('utf-8', errors='ignore')
                    
                    result = _parse_bandcamp_from_json_ld(html_content)
                    if result[0] is not None or result[1] is not None:
                        return result
                    
        except Exception:
            continue
    
    return (None, None)


def _parse_bandcamp_from_json_ld(html_content: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse Bandcamp JSON-LD schema to extract genre keywords and label.
    
    Bandcamp embeds structured data with keywords/tags in the page.
    """
    genre = None
    label = None
    
    json_ld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>([^<]+)</script>'
    matches = re.findall(json_ld_pattern, html_content, re.IGNORECASE)
    
    keywords_found = []
    
    for match in matches:
        try:
            data = json.loads(match)
            
            if isinstance(data, dict):
                keywords = data.get('keywords', [])
                if isinstance(keywords, list):
                    keywords_found.extend([k.lower() for k in keywords])
                
                publisher = data.get('publisher', {})
                if isinstance(publisher, dict):
                    label = publisher.get('name')
                
                if not label:
                    by_artist = data.get('byArtist', {})
                    if isinstance(by_artist, dict):
                        label = by_artist.get('name')
                    
        except (json.JSONDecodeError, TypeError):
            continue
    
    keywords_lower = [k.lower() for k in keywords_found]
    
    house_keywords = {'house', 'tech house', 'afro house', 'deep house', 'disco house',
                     'melodic house', 'organic house', 'future house', 'progressive house',
                     'tropical house', 'funky house', 'garage', 'funky'}
    
    dnb_keywords = {'drum and bass', 'drum and bass', 'dnb', 'drum&bass', 'drum n bass',
                   'jungle', 'neurofunk', 'techstep', 'darkdrumandbass', 'deepdrumandbass'}
    
    techno_keywords = {'techno', 'hard techno', 'minimal'}
    trance_keywords = {'trance', 'psytrance', 'progressive trance'}
    
    for kw in keywords_lower:
        if kw in house_keywords:
            genre = 'House'
            break
        elif kw in dnb_keywords:
            genre = 'DnB'
            break
        elif kw in techno_keywords:
            genre = 'Techno'
            break
        elif kw in trance_keywords:
            genre = 'Trance'
            break
    
    if not genre:
        for kw in keywords_lower:
            if 'house' in kw:
                genre = 'House'
                break
            elif 'drum' in kw and 'bass' in kw:
                genre = 'DnB'
                break
    
    return (genre, label)


def _parse_bandcamp_search_results(html_content: str, artist: str, title: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse Bandcamp search results HTML to find genre and label.
    Tries JSON-LD schema parsing first, then falls back to HTML tag parsing.
    
    Args:
        html_content: HTML content from Bandcamp search
        artist: Artist name to match
        title: Track title to match
        
    Returns:
        Tuple of (genre, label) or (None, None)
    """
    genre = None
    label = None
    
    json_ld_result = _parse_bandcamp_from_json_ld(html_content)
    if json_ld_result[0] is not None or json_ld_result[1] is not None:
        return json_ld_result
    
    search_result = _extract_first_search_result(html_content)
    if search_result:
        result = _fetch_and_parse_track_page(search_result)
        if result[0] is not None or result[1] is not None:
            return result
    
    tag_pattern = r'<a[^>]+class="tag"[^>]*>([^<]+)</a>'
    tags = re.findall(tag_pattern, html_content, re.IGNORECASE)
    
    house_related = {'house', 'tech house', 'afro house', 'deep house', 'disco house', 
                     'melodic house', 'organic house', 'future house', 'progressive house',
                     'tropical house', 'funky house'}
    
    electronic_genres = {'techno', 'tech house', 'trance', 'ambient', 'electronica', 
                        'downtempo', 'chillout', 'electro', 'dubstep', 'drum and bass',
                        'dnb', 'drone', 'idm', 'experimental'}
    
    all_tags = [tag.strip().lower() for tag in tags]
    
    for tag in all_tags:
        if tag in house_related:
            genre = 'House'
            break
        elif tag in electronic_genres:
            genre = tag.title()
            break
        elif tag == 'electronic':
            genre = 'Electronic'
            break
    
    if not genre:
        for tag in all_tags:
            if 'house' in tag:
                genre = 'House'
                break
            elif 'techno' in tag:
                genre = 'Techno'
                break
            elif 'trance' in tag:
                genre = 'Trance'
                break
    
    label_pattern = r'<div[^>]+class="artist"[^>]*>.*?<a[^>]*>([^<]+)</a>'
    label_match = re.search(label_pattern, html_content, re.IGNORECASE | re.DOTALL)
    if label_match:
        label = label_match.group(1).strip()
    
    return (genre, label)


def _extract_first_search_result(html_content: str) -> Optional[str]:
    """
    Extract the first track URL from Bandcamp search results.
    
    Args:
        html_content: HTML content from Bandcamp search
        
    Returns:
        First track URL or None
    """
    item_pattern = r'data-item-url="([^"]+)"'
    matches = re.findall(item_pattern, html_content)
    
    for match in matches:
        if '/track/' in match:
            return match
    
    link_pattern = r'<a[^>]+href="(https://[^"]+\.bandcamp\.com/track/[^"]+)"'
    matches = re.findall(link_pattern, html_content, re.IGNORECASE)
    if matches:
        return matches[0]
    
    return None


def _fetch_and_parse_track_page(track_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch and parse a Bandcamp track page.
    
    Args:
        track_url: URL to the Bandcamp track page
        
    Returns:
        Tuple of (genre, label)
    """
    try:
        request = urllib.request.Request(
            track_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        
        with urllib.request.urlopen(request, timeout=10) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
            
            return _parse_bandcamp_from_json_ld(html_content)
            
    except Exception:
        pass
    
    return (None, None)


def _normalize_genre(genre: str) -> str:
    """Normalize genre to standard forms."""
    if not genre:
        return ""
    
    genre = genre.strip()
    
    normalizations = {
        'drum and bass': 'DRUM N BASS',
        'drum & bass': 'DRUM N BASS',
        'electronic dance music': 'EDM',
        'intelligent dance music': 'IDM',
        'uk garage': 'UKG',
    }
    
    genre_lower = genre.lower()
    for key, value in normalizations.items():
        if key in genre_lower:
            genre = genre.lower().replace(key, value)
    
    if genre.lower() == genre.strip().lower() and genre == genre.strip():
        applied_normalization = False
        for key in normalizations.keys():
            if key in genre_lower:
                applied_normalization = True
                break
        
        if not applied_normalization:
            return genre.title()
    
    return genre

def get_genre_online(artist: str, title: str) -> Optional[str]:
    """
    Lookup genre via online services with improved accuracy for electronic music.
    Uses unified iTunes lookup to avoid redundant API calls.
    """
    cache_key = f"{artist.lower()}:{title.lower()}"
    if cache_key in _genre_cache:
        return _genre_cache[cache_key]
    
    itunes_data = _lookup_itunes_all_metadata(artist, title)
    itunes_genre = itunes_data.get('genre')
    if itunes_genre:
        normalized = _normalize_genre(itunes_genre)
        if _is_electronic_genre(itunes_genre):
            _genre_cache[cache_key] = normalized
            return normalized
    
    bandcamp_genre, _ = get_genre_from_bandcamp(artist, title)
    if bandcamp_genre:
        _genre_cache[cache_key] = bandcamp_genre
        return bandcamp_genre
    
    try:
        query = urllib.parse.quote(f'artist:"{artist}" AND recording:"{title}"')
        url = f"https://musicbrainz.org/ws/2/recording/?query={query}&fmt=json&limit=5"
        request = urllib.request.Request(
            url, 
            headers={'User-Agent': 'MP3Organizer/1.0 (https://github.com/holger-kampffmeyer/organize_mp3s)'}
        )
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data['recordings']:
                for recording in data['recordings'][:3]:
                    recording_id = recording['id']
                    rg_url = f"https://musicbrainz.org/ws/2/release-group/?recording={recording_id}&fmt=json"
                    rg_request = urllib.request.Request(
                        rg_url,
                        headers={'User-Agent': 'MP3Organizer/1.0 (https://github.com/holger-kampffmeyer/organize_mp3s)'}
                    )
                    with urllib.request.urlopen(rg_request, timeout=10) as rg_response:
                        rg_data = json.loads(rg_response.read().decode())
                        if rg_data['release-groups']:
                            rg_id = rg_data['release-groups'][0]['id']
                            tag_url = f"https://musicbrainz.org/ws/2/release-group/{rg_id}?inc=tags&fmt=json"
                            tag_request = urllib.request.Request(
                                tag_url,
                                headers={'User-Agent': 'MP3Organizer/1.0 (https://github.com/holger-kampffmeyer/organize_mp3s)'}
                            )
                            with urllib.request.urlopen(tag_request, timeout=10) as tag_response:
                                tag_data = json.loads(tag_response.read().decode())
                                if 'tags' in tag_data['release-group'] and tag_data['release-group']['tags']:
                                    genre_candidates = []
                                    for tag in tag_data['release-group']['tags']:
                                        tag_name = tag['name'].strip()
                                        if _is_electronic_genre(tag_name):
                                            genre_candidates.append((tag['count'], _normalize_genre(tag_name)))
                                    
                                    if genre_candidates:
                                        genre_candidates.sort(reverse=True)
                                        best_genre = genre_candidates[0][1]
                                        _genre_cache[cache_key] = best_genre
                                        return best_genre
                                    elif tag_data['release-group']['tags']:
                                        try:
                                            tag_data['release-group']['tags'].sort(key=lambda x: x.get('count', 0), reverse=True)
                                        except Exception:
                                            pass
                                        best_genre = _normalize_genre(tag_data['release-group']['tags'][0]['name'])
                                        _genre_cache[cache_key] = best_genre
                                        return best_genre
    except Exception:
        pass
    
    if itunes_genre:
        normalized = _normalize_genre(itunes_genre)
        _genre_cache[cache_key] = normalized
        return normalized
    
    _genre_cache[cache_key] = None
    return None


def find_genre_destination(genre: str, genre_to_dest: Dict[str, str]) -> Optional[str]:
    """
    Find destination folder for a given genre.
    
    Args:
        genre: Genre name to map
        genre_to_dest: Mapping of genre strings to destination paths
        
    Returns:
        Destination path if genre is mapped, None otherwise
    """
    if not genre:
        return None
    
    normalized_genre = genre.lower().strip()
    
    # Special case: if genre contains both "drum" and "bass" -> map to "Drum n Base"
    if 'drum' in normalized_genre and 'bass' in normalized_genre:
        normalized_genre = 'drum n base'
    
    # Look for exact match in config (keys are normalized to lowercase)
    for config_key, dest in genre_to_dest.items():
        if normalized_genre == config_key.lower().strip():
            return dest
        # Also check if config key contains comma-separated values
        if ',' in config_key:
            for part in config_key.split(','):
                if normalized_genre == part.lower().strip():
                    return dest
    
    # Subgenre hierarchy: extract parent genre and try again
    parent_genre = _extract_parent_genre(normalized_genre)
    if parent_genre and parent_genre != normalized_genre:
        result = find_genre_destination(parent_genre, genre_to_dest)
        if result:
            return result
    
    # Fuzzy matching: try to find similar genre in config
    fuzzy_threshold = 0.8  # Default, can be overridden via config
    fuzzy_result = _find_fuzzy_genre(genre, genre_to_dest, fuzzy_threshold)
    if fuzzy_result:
        return fuzzy_result
    
    return None


GENRE_SYNONYMS = {
    "hip hop": "Hip-Hop/Rap",
    "hiphop": "Hip-Hop/Rap",
    "hip-hop": "Hip-Hop/Rap",
    "rap": "Hip-Hop/Rap",
    "edm": "Electronic",
    "electro": "Electronic",
    "dnb": "Drum n Bass",
    "drum & bass": "Drum n Bass",
    "drum and bass": "Drum n Bass",
    "drumnbass": "Drum n Bass",
    "dnbf": "Drum n Bass",
    "liquid": "Drum n Bass",
    "neurofunk": "Drum n Bass",
    "neuro": "Drum n Bass",
    "jungle": "Drum n Bass",
    "progressive house": "House",
    "prog house": "House",
    "electro house": "House",
    "deep house": "House",
    "tech house": "House",
    "future house": "House",
    "tropical house": "House",
    "melodic house": "House",
    "organic house": "House",
    "disco house": "House",
    "afro house": "House",
    "funky house": "House",
    "garage": "House",
    "trance": "Trance",
    "psytrance": "Trance",
    "progressive trance": "Trance",
    "techno": "Techno",
    "hard techno": "Techno",
    "minimal": "Techno",
    "dark techno": "Techno",
    "dubstep": "Dubstep",
    "dub": "Dubstep",
    "bass": "Dubstep",
    "experimental": "Experimental",
    "ambient": "Ambient",
    "chill": "Ambient",
    "downtempo": "Ambient",
    "idm": "Electronic",
    "electronica": "Electronic",
}


def _find_fuzzy_genre(genre: str, genre_to_dest: Dict[str, str], threshold: float = 0.8) -> Optional[str]:
    """
    Find genre in config using fuzzy matching.
    
    Uses Levenshtein distance ratio to find similar genres.
    
    Args:
        genre: Genre string to match
        genre_to_dest: Mapping of config genres to destinations
        threshold: Minimum similarity score (0-1) for match
        
    Returns:
        Destination string if match found, None otherwise
    """
    if not genre or not genre_to_dest:
        return None
    
    # Check synonyms first
    normalized = genre.lower().strip()
    if normalized in GENRE_SYNONYMS:
        canonical = GENRE_SYNONYMS[normalized]
        if canonical in genre_to_dest:
            return genre_to_dest[canonical]
    
    # Try fuzzy matching with difflib (already imported at module level)
    best_match = None
    best_score = 0.0
    
    for config_genre in genre_to_dest.keys():
        score = SequenceMatcher(None, normalized, config_genre.lower()).ratio()
        
        # Also check against canonical names from synonyms
        if normalized in GENRE_SYNONYMS:
            canonical = GENRE_SYNONYMS[normalized].lower()
            alt_score = SequenceMatcher(None, canonical, config_genre.lower()).ratio()
            score = max(score, alt_score)
        
        if score > best_score:
            best_score = score
            best_match = config_genre
    
    if best_score >= threshold:
        return genre_to_dest[best_match]
    
    return None


def _extract_parent_genre(genre: str) -> Optional[str]:
    """
    Extract parent genre from a subgenre string.
    
    E.g., "Electro House" -> "House", "Progressive House" -> "House"
    
    Args:
        genre: Normalized genre string
        
    Returns:
        Parent genre string or None if no parent found
    """
    if not genre:
        return None
    
    genre_lower = genre.lower()
    
    if 'drum' in genre_lower and 'bass' in genre_lower:
        return 'drum n bass'
    if 'house' in genre_lower:
        return 'house'
    if 'techno' in genre_lower:
        return 'techno'
    if 'trance' in genre_lower:
        return 'trance'
    if 'edm' in genre_lower:
        return 'edm'
    if 'dance' in genre_lower:
        return 'dance'
    if 'electronic' in genre_lower:
        return 'electronic'
    if 'ambient' in genre_lower:
        return 'ambient'
    if 'dubstep' in genre_lower:
        return 'dubstep'
    if 'breakbeat' in genre_lower:
        return 'breakbeat'
    if 'experimental' in genre_lower:
        return 'experimental'
    
    return None


def determine_destination(
    label: Optional[str],
    genre: Optional[str],
    label_to_dest: Dict[str, str], 
    genre_to_dest: Dict[str, str]
) -> Tuple[Optional[str], bool, bool, Optional[str], Optional[str]]:
    """
    Determine destination directory based on label and genre priority.
    
    Assumes label and genre parameters already represent the final values
    (from metadata or online lookup, as determined by process_files).
    
    Priority Logic:
    1. If label mapping configured and we have a label:
       a. Try to map the label to destination
       b. If successful, we're done (used_label = True)
    2. If label mapping not successful (no label, or label not mapped):
       - Fall back to genre mapping if genre is available
    
    Returns:
        Tuple of (destination_dir, used_label, used_genre, detected_genre, detected_label)
        where:
        - destination_dir: Final destination path or None
        - used_label: True if label mapping was used for destination
        - used_genre: True if genre mapping was used for destination  
        - detected_genre: Genre that was provided as input (passed through for logging)
        - detected_label: Label that was provided as input (passed through for logging)
    """
    used_label = False
    used_genre = False
    detected_genre_for_log = genre
    detected_label_for_log = label
    dest_dir = None

    # Priority 1: Label-based mapping (if label_to_dest is configured and we have a label)
    if label_to_dest and label is not None:
        detected_label_for_log = label
        dest_dir = find_label_destination(label, label_to_dest)
        if dest_dir is not None:
            used_label = True

    # Priority 2: Genre-based mapping (fallback if label mapping failed or no label)
    if dest_dir is None and genre is not None:
        detected_genre_for_log = genre
        dest_dir = find_genre_destination(genre, genre_to_dest)
        if dest_dir is not None:
            used_genre = True

    return dest_dir, used_label, used_genre, detected_genre_for_log, detected_label_for_log


def determine_failure_reason(label: Optional[str], label_to_dest: Dict[str, str], genre: Optional[str]) -> str:
    """
    Determine the reason for failure to find a destination.
    
    Logic mirrors determine_destination priority:
    1. If we have a label and label_map configured, and it wasn't mapped -> label_not_mapped
    2. If we have a label but no label_map configured -> label_not_mapped (can't use it)
    3. If we have no label but label_map exists -> check genre
       - If genre is available and mapped -> genre_not_mapped (shouldn't happen with current logic)
       - If genre is available but not mapped -> genre_not_mapped
       - If no genre -> lookup_failed
    4. If we have no label and no genre -> lookup_failed
    5. If we have genre but it's not mapped -> genre_not_mapped
    """
    has_label_map = bool(label_to_dest)
    has_label = label is not None
    
    if has_label and has_label_map:
        return "label_not_mapped"
    elif has_label and not has_label_map:
        return "label_not_mapped"
    elif not has_label and has_label_map:
        if genre is not None:
            return "genre_not_mapped"
        else:
            return "lookup_failed"
    elif not has_label and not has_label_map and not genre:
        return "lookup_failed"
    elif genre is not None:
        return "genre_not_mapped"
    return "lookup_failed"


def _parse_filename_to_artist_title(file_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse an audio filename into artist and title components.

    Expected format: "Artist - Title.ext" or "Artist Title.ext"
    Returns (artist, title) or (None, None) if parsing fails.
    """
    stem = file_path.stem.strip()
    if not stem:
        return (None, None)

    if ' - ' in stem:
        parts = stem.split(' - ', 1)
        return (parts[0].strip(), parts[1].strip())

    return (None, None)


def _normalize_for_comparison(text: str) -> str:
    """Normalize text for fuzzy comparison: lowercase, strip punctuation/whitespace."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def _check_substring_match(meta_title: str, filename_title: str) -> Tuple[bool, float]:
    """
    Check if metadata title is contained in filename title (or vice versa).
    
    This handles cases like:
    - meta: "Locked In", filename: "Lost In The Abyss - 02 Locked In" -> match
    - meta: "Way Of The Wub", filename: "Second Opinion LP - 06 Way Of The Wub" -> match
    
    Returns:
        Tuple of (is_match, similarity_score)
    """
    if not meta_title or not filename_title:
        return (False, 0.0)
    
    norm_meta = _normalize_for_comparison(meta_title)
    norm_filename = _normalize_for_comparison(filename_title)
    
    if not norm_meta or not norm_filename:
        return (False, 0.0)
    
    # Direct substring check (meta in filename or filename in meta)
    if norm_meta in norm_filename or norm_filename in norm_meta:
        return (True, 1.0)
    
    # Check if significant words from metadata are in filename
    # Tokenize and check overlap
    meta_words = set(norm_meta.split())
    filename_words = set(norm_filename.split())
    
    if not meta_words or not filename_words:
        return (False, 0.0)
    
    # Check if all meta words are found in filename (order-independent match)
    if meta_words.issubset(filename_words):
        return (True, 1.0)
    
    # Calculate word overlap ratio
    common_words = meta_words & filename_words
    if common_words:
        overlap_ratio = len(common_words) / len(meta_words)
        # If >70% of meta words are in filename, consider it a match
        if overlap_ratio >= 0.7:
            return (True, overlap_ratio)
    
    return (False, 0.0)


def _check_metadata_mismatch(
    file_path: Path,
    meta_artist: Optional[str],
    meta_title: Optional[str],
    threshold: float = 0.6
) -> Dict[str, Optional[str]]:
    """
    Compare metadata artist/title against what's parsed from the filename.

    Returns dict with keys:
        - filename_artist: Artist parsed from filename (or None)
        - filename_title: Title parsed from filename (or None)
        - artist_mismatch: True if metadata artist differs significantly from filename artist
        - title_mismatch: True if metadata title differs significantly from filename title
        - artist_similarity: Similarity score for artist (0-1)
        - title_similarity: Similarity score for title (0-1)
    """
    result = {
        'filename_artist': None,
        'filename_title': None,
        'artist_mismatch': False,
        'title_mismatch': False,
        'artist_similarity': None,
        'title_similarity': None,
    }

    filename_artist, filename_title = _parse_filename_to_artist_title(file_path)
    result['filename_artist'] = filename_artist
    result['filename_title'] = filename_title

    if meta_artist and filename_artist:
        norm_meta = _normalize_for_comparison(meta_artist)
        norm_file = _normalize_for_comparison(filename_artist)
        score = SequenceMatcher(None, norm_meta, norm_file).ratio()
        result['artist_similarity'] = round(score, 2)
        if score < threshold:
            result['artist_mismatch'] = True

    if meta_title and filename_title:
        # First check: substring match (primary check for titles with additional context)
        is_substring_match, substring_score = _check_substring_match(meta_title, filename_title)
        
        if is_substring_match:
            # Substring match found - metadata title is contained in filename title
            result['title_similarity'] = round(substring_score, 2)
            result['title_mismatch'] = False
        else:
            # Fallback to Levenshtein similarity
            norm_meta = _normalize_for_comparison(meta_title)
            norm_file = _normalize_for_comparison(filename_title)
            score = SequenceMatcher(None, norm_meta, norm_file).ratio()
            result['title_similarity'] = round(score, 2)
            if score < threshold:
                result['title_mismatch'] = True

    return result


def process_file(file_path: Path, config: Dict, dry_run: bool = False, enrich_metadata: bool = False) -> Dict:
    """
    Process a single audio file.

    Optimized flow:
    1. Single ffprobe call for all metadata
    2. Single iTunes lookup for all online metadata (label, genre, album, year, track)
    3. Early-exit when label already maps to destination (skip genre lookup)
    4. Only fallback to Bandcamp/MusicBrainz when iTunes fails
    """
    result = {
        'file_path': str(file_path.absolute()),
        'artist': None,
        'title': None,
        'album': None,
        'genre': None,
        'label': None,
        'destination': None,
        'action': None,
        'reason': None,
        'enriched_tags': [],
        'metadata_mismatch': None,
    }

    try:
        # Step 1: Extract ALL metadata in a single ffprobe call
        all_meta = _extract_all_metadata(file_path)
        artist = all_meta.get('artist')
        title = all_meta.get('title')

        # Clean title: Remove artist prefix if present
        if artist and title and title.lower().startswith(artist.lower() + ' - '):
            title = title[len(artist) + 3:].strip()

        # Clean title: Remove remix/version suffixes for better online lookups
        if title:
            title = re.sub(r'\s*\([^)]*\)\s*$', '', title).strip()
            title = re.sub(r'\s*-\s*remix\s*$', '', title, flags=re.IGNORECASE).strip()
            title = re.sub(r'\s*-\s*edit\s*$', '', title, re.IGNORECASE).strip()

        # Check for metadata vs filename mismatch
        mismatch_info = _check_metadata_mismatch(file_path, artist, title)
        has_mismatch = mismatch_info['artist_mismatch'] or mismatch_info['title_mismatch']
        if has_mismatch:
            result['metadata_mismatch'] = mismatch_info
            logger.warning(
                f"MISMATCH: {file_path.name} - "
                f"metadata artist='{artist}' vs filename artist='{mismatch_info['filename_artist']}' "
                f"(similarity={mismatch_info['artist_similarity']}), "
                f"metadata title='{title}' vs filename title='{mismatch_info['filename_title']}' "
                f"(similarity={mismatch_info['title_similarity']})"
            )

        if not artist or not title:
            missing_field = 'artist' if not artist else 'title' if not title else 'both'
            result['reason'] = f'missing_metadata_{missing_field}'
            result['action'] = 'leave'
            return result

        # If mismatch detected, try to use filename as fallback for online lookup
        lookup_artist = artist
        lookup_title = title
        if has_mismatch:
            if mismatch_info['filename_artist'] and mismatch_info['filename_title']:
                logger.info(f"Using filename artist/title for online lookup: '{mismatch_info['filename_artist']}' - '{mismatch_info['filename_title']}'")
                lookup_artist = mismatch_info['filename_artist']
                lookup_title = mismatch_info['filename_title']
            elif mismatch_info['filename_artist']:
                logger.info(f"Using filename artist for online lookup: '{mismatch_info['filename_artist']}'")
                lookup_artist = mismatch_info['filename_artist']
            elif mismatch_info['filename_title']:
                logger.info(f"Using filename title for online lookup: '{mismatch_info['filename_title']}'")
                lookup_title = mismatch_info['filename_title']

        result['artist'] = artist
        result['title'] = title

        # Step 2: Get label from metadata
        label_from_metadata = get_label_from_metadata(file_path, config.get('label_source_tag'))
        label_to_dest = config.get('label_map', {})
        genre_to_dest = config.get('genre_map', {})

        # Step 3: Determine if we need online lookups
        need_label_online = label_from_metadata is None and bool(label_to_dest)

        # Always need genre lookup for fallback when label is not available
        genre_from_metadata = all_meta.get('genre')
        need_genre_online = True  # Always do genre lookup for fallback

        # Check if we need additional metadata (album, year) for enrich
        enrich_enabled = (enrich_metadata or config.get('enrich_metadata', False)) and not dry_run
        album_from_metadata = all_meta.get('album')
        need_additional_online = enrich_enabled and (
            album_from_metadata is None or (need_label_online and need_genre_online)
        )

        # Step 4: Single iTunes lookup if any online data needed
        itunes_data = {}
        if need_label_online or need_genre_online or need_additional_online:
            itunes_data = _lookup_itunes_all_metadata(lookup_artist, lookup_title)

        # Step 5: Determine final label
        final_label = label_from_metadata
        if final_label is None and itunes_data.get('label'):
            final_label = itunes_data['label']

        # Also try Bandcamp for label if iTunes didn't find it
        if final_label is None and need_label_online:
            _, bandcamp_label = get_genre_from_bandcamp(lookup_artist, lookup_title)
            if bandcamp_label:
                final_label = bandcamp_label

        result['label'] = final_label

        # Step 6: Determine destination - try label first, then genre fallback
        # Always do genre lookup to enable fallback when label doesn't work
        final_genre = genre_from_metadata
        if final_genre is None and itunes_data.get('genre'):
            itunes_genre = itunes_data['genre']
            if _is_electronic_genre(itunes_genre):
                final_genre = _normalize_genre(itunes_genre)

        if final_genre is None and need_genre_online:
            final_genre = get_genre_online(lookup_artist, lookup_title)

        result['genre'] = final_genre

        # Determine destination: label priority, then genre fallback
        dest_dir, used_label, used_genre, _, _ = determine_destination(
            final_label, final_genre, label_to_dest, genre_to_dest
        )

        # Enrich genre metadata if enabled and genre was found online
        enriched_tags = []
        if enrich_enabled and final_genre and not genre_from_metadata:
            if _write_metadata_tag(file_path, 'genre', final_genre):
                enriched_tags.append('genre')

        # Step 7: Enrich metadata if enabled
        if enrich_enabled:
            # Get additional metadata from online if needed
            additional_metadata = {}
            if album_from_metadata is None or final_label is None or final_genre is None:
                if itunes_data:
                    additional_metadata = {
                        'album': itunes_data.get('album'),
                        'year': itunes_data.get('year'),
                        'track_number': itunes_data.get('track_number'),
                    }
                else:
                    additional_metadata = get_additional_metadata_online(lookup_artist, lookup_title)

            if final_label and not label_from_metadata and 'label' not in enriched_tags:
                label_tag = config.get('label_source_tag', 'label')
                if _write_metadata_tag(file_path, label_tag, final_label):
                    enriched_tags.append(label_tag)

            if final_genre and not genre_from_metadata and 'genre' not in enriched_tags:
                if _write_metadata_tag(file_path, 'genre', final_genre):
                    enriched_tags.append('genre')

            if additional_metadata.get('album') and not album_from_metadata:
                if _write_metadata_tag(file_path, 'album', additional_metadata['album']):
                    enriched_tags.append('album')

            if additional_metadata.get('year'):
                existing_year = all_meta.get('date')
                if not existing_year:
                    if _write_metadata_tag(file_path, 'date', additional_metadata['year']):
                        enriched_tags.append('year')

        result['enriched_tags'] = enriched_tags

        # Step 8: Move or leave
        result['destination'] = str(dest_dir) if dest_dir else None

        if dest_dir is None:
            result['reason'] = determine_failure_reason(final_label, label_to_dest, final_genre)
            result['action'] = 'leave'
        else:
            target_path = Path(dest_dir) / file_path.name
            if target_path.exists():
                result['reason'] = 'target_exists'
                result['action'] = 'leave'
            else:
                move_enabled = not dry_run and config.get('move', True)
                if move_enabled:
                    Path(dest_dir).mkdir(parents=True, exist_ok=True)
                    file_path.rename(target_path)
                result['action'] = 'move'
                result['destination'] = str(target_path.absolute())

        return result

    except Exception as e:
        result['reason'] = f'processing_error: {str(e)}'
        result['action'] = 'leave'
        return result


def organize_music(source_dir: str = ".", dry_run: bool = False, enrich_metadata: bool = False) -> None:
    """
    Main function to organize MP3 and M4A files.
    
    Args:
        source_dir: Directory to scan for audio files
        dry_run: If True, only simulate the operation
        enrich_metadata: If True, write missing metadata from online sources to files
    """
    source_path = Path(source_dir).resolve()
    
    # Load config
    config_path = source_path / "config.json"
    if not config_path.exists():
        logger.error(f"config.json not found in {source_path}")
        sys.exit(1)
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config.json: {e}")
        sys.exit(1)
    
    # Find audio files
    audio_files = []
    for ext in ['*.mp3', '*.m4a']:
        audio_files.extend(source_path.rglob(ext))
    
    if not audio_files:
        logger.info("No MP3 or M4A files found.")
        return
    
    logger.info(f"Found {len(audio_files)} audio files to process.")
    
    # Process files
    results = []
    for audio_file in audio_files:
        result = process_file(audio_file, config, dry_run, enrich_metadata)
        results.append(result)
        
        # Print progress
        if result['action'] == 'move':
            logger.info(f"MOVED: {audio_file.name} -> {result['destination']}")
        elif result['action'] == 'leave':
            logger.info(f"LEFT:  {audio_file.name} ({result['reason']})")
    
    # Generate report
    if dry_run:
        report_path = source_path / "organization_audit.json"
        report_key = "audit"
    else:
        report_path = source_path / "organization_results.json"
        report_key = "results"
    
    report = {
        report_key: results,
        'summary': {
            'total_files': len(audio_files),
            'files_moved': len([r for r in results if r['action'] == 'move']),
            'files_left': len([r for r in results if r['action'] == 'leave'])
        }
    }
    
    try:
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to: {report_path}")
    except Exception as e:
        logger.error(f"Error writing report: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Organize MP3/M4A files by genre or label")
    parser.add_argument("source_directory", nargs="?", default=".", 
                       help="Directory to scan for audio files (default: current directory)")
    parser.add_argument("--dry-run", "-n", action="store_true",
                       help="Only show what would be done, don't actually move files")
    parser.add_argument("--enrich-metadata", "-e", action="store_true",
                       help="Enrich missing metadata tags from online sources (label, genre, album, year)")
    
    args = parser.parse_args()
    
    organize_music(args.source_directory, args.dry_run, args.enrich_metadata)