# services/utils.py
"""
Geocoding utilities for converting addresses/postcodes to coordinates.
"""
import requests
from typing import Optional, Tuple


def geocode_postcode(postcode: str) -> Optional[Tuple[float, float]]:
    """
    Convert UK postcode to latitude/longitude using free Postcodes.io API.
    
    Args:
        postcode: UK postcode (e.g., "M1 1AE", "SW1A 1AA")
    
    Returns:
        Tuple of (latitude, longitude) or None if not found
    
    Example:
        >>> geocode_postcode("M1 1AE")
        (53.479324, -2.245115)
    """
    try:
        # Clean postcode
        postcode = postcode.strip().upper().replace(' ', '')
        
        # Use free Postcodes.io API (no API key required for UK postcodes)
        url = f"https://api.postcodes.io/postcodes/{postcode}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200 and data.get('result'):
                result = data['result']
                return (result['latitude'], result['longitude'])
        
        return None
    except Exception as e:
        print(f"Geocoding error for postcode '{postcode}': {e}")
        return None


def geocode_address(address: str, postcode: str = None) -> Optional[Tuple[float, float]]:
    """
    Convert address to coordinates. Tries postcode first (more accurate), then full address.
    
    Args:
        address: Full address string
        postcode: Optional UK postcode for more accurate results
    
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    # Try postcode first if provided (most accurate for UK)
    if postcode:
        coords = geocode_postcode(postcode)
        if coords:
            return coords
    
    # Fallback: You could integrate Google Geocoding API, Mapbox, or OpenCage here
    # For now, return None to keep it free
    # To add paid geocoding:
    # 1. Install: pip install googlemaps
    # 2. Get API key from Google Cloud Console
    # 3. Use: gmaps = googlemaps.Client(key='YOUR_API_KEY')
    #         result = gmaps.geocode(address)
    
    return None


def get_available_zones_for_location(latitude: float, longitude: float):
    """
    Get all active service zones that contain the given coordinates.
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
    
    Returns:
        QuerySet of ServiceZone objects that contain this point
    """
    from .models import ServiceZone
    
    available_zones = []
    for zone in ServiceZone.objects.filter(is_active=True):
        if zone.contains_point(latitude, longitude):
            available_zones.append(zone)
    
    return available_zones


def get_available_zones_for_postcode(postcode: str):
    """
    Get all service zones available for a given UK postcode.
    
    Args:
        postcode: UK postcode
    
    Returns:
        List of ServiceZone objects or None if postcode invalid
    """
    coords = geocode_postcode(postcode)
    if not coords:
        return None
    
    latitude, longitude = coords
    return get_available_zones_for_location(latitude, longitude)
