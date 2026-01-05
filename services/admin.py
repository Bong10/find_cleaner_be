from django.contrib import admin
from django.utils.html import format_html
from .models import Service, Category, ServiceZone


@admin.register(ServiceZone)
class ServiceZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'get_coordinates', 'get_cleaners_count', 'get_total_cleaners', 'is_active', 'updated_at')
    list_filter = ('is_active', 'parent', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'get_interactive_map', 'get_map_preview', 'get_suggested_parent', 'get_child_zones_display')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Zone Hierarchy', {
            'fields': ('parent', 'get_suggested_parent', 'get_child_zones_display'),
            'description': 'Parent zones (e.g., England) automatically include cleaners from child zones (e.g., Cambridgeshire). Cleaners only select their most specific zone.'
        }),
        ('Geographic Data', {
            'fields': ('center_latitude', 'center_longitude', 'boundary_data', 'get_interactive_map'),
            'description': 'Search and select a location. The system will automatically use the actual city/county boundary.'
        }),
        ('OpenStreetMap Reference', {
            'fields': ('osm_type', 'osm_id'),
            'classes': ('collapse',),
            'description': 'Auto-filled from OpenStreetMap for reference.'
        }),
        ('Map Preview', {
            'fields': ('get_map_preview',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    class Media:
        css = {
            'all': ('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',)
        }
        js = (
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
        )
    
    def get_coordinates(self, obj):
        """Display coordinates in a readable format."""
        return f"{obj.center_latitude}, {obj.center_longitude}"
    get_coordinates.short_description = 'Center Point'
    
    def get_cleaners_count(self, obj):
        """Show how many cleaners are directly in this zone."""
        count = obj.cleaners.count()
        return format_html('<strong>{}</strong>', count)
    get_cleaners_count.short_description = 'Direct Cleaners'
    
    def get_total_cleaners(self, obj):
        """Show total cleaners including child zones."""
        total = obj.get_all_cleaners().count()
        direct = obj.cleaners.count()
        if total > direct:
            return format_html('<strong>{}</strong> <span style="color: #666;">(+{} from child zones)</span>', total, total - direct)
        return format_html('<strong>{}</strong>', total)
    get_total_cleaners.short_description = 'Total (with Children)'
    
    def get_suggested_parent(self, obj):
        """Suggest parent zone based on geographic containment."""
        if not obj.pk:
            return "Save zone first to get suggestions"
        
        suggested = obj.suggest_parent_zone()
        if suggested:
            return format_html(
                '<span style="color: #2e7d32; font-weight: bold;">✓ Suggested: {}</span><br>'
                '<small style="color: #666;">This zone appears to be contained within <strong>{}</strong>. '
                'Consider setting it as parent for automatic cleaner inheritance.</small>',
                suggested.name, suggested.name
            )
        return format_html('<span style="color: #666;">No parent zone detected (this may be a top-level zone)</span>')
    get_suggested_parent.short_description = 'Suggested Parent'
    
    def get_child_zones_display(self, obj):
        """Display child zones."""
        if not obj.pk:
            return "Save zone first"
        
        children = obj.children.filter(is_active=True)
        if not children.exists():
            return format_html('<span style="color: #666;">No child zones</span>')
        
        child_list = ', '.join([f'<strong>{child.name}</strong>' for child in children])
        total_cleaners = sum(child.cleaners.count() for child in children)
        return format_html(
            '{}<br><small style="color: #666;">{} child zones with {} total cleaners</small>',
            child_list, children.count(), total_cleaners
        )
    get_child_zones_display.short_description = 'Child Zones'
    
    def get_interactive_map(self, obj):
        """Interactive Leaflet map for selecting service zone location."""
        lat = float(obj.center_latitude) if obj.center_latitude else 51.5074
        lng = float(obj.center_longitude) if obj.center_longitude else -0.1278
        radius = float(obj.radius_km) if obj.radius_km else 10
        
        boundary_data = ''
        if obj.pk and obj.boundary_data:
            import json
            boundary_data = json.dumps(obj.boundary_data)
        
        return format_html('''
            <div style="margin: 10px 0; padding: 15px; background: #f9f9f9; border: 2px solid #ddd; border-radius: 4px;">
                <label style="font-weight: bold; display: block; margin-bottom: 8px; color: #333;">🔍 Search Location:</label>
                <input type="text" id="map-search" placeholder="Type location (e.g., Cambridge, Manchester, Birmingham)" 
                       style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; box-sizing: border-box; background: white; color: #333;">
                <div id="search-results" style="max-height: 200px; overflow-y: auto; margin-top: 5px; border: 1px solid #e0e0e0; border-radius: 4px; display: none; background: white;"></div>
                <span id="search-status" style="display: block; margin-top: 8px; font-style: italic; color: #333; font-size: 13px;"></span>
            </div>
            <div id="zone-map" style="width: 100%; height: 450px; margin: 10px 0; border: 2px solid #ddd; border-radius: 4px;"></div>
            <div style="margin: 10px 0; padding: 15px; background: #e3f2fd; border-left: 4px solid #2196F3; border-radius: 4px;">
                <strong style="color: #1565c0; font-size: 14px;">📍 How to use:</strong>
                <ul style="margin: 8px 0 0 20px; color: #333; line-height: 1.6;">
                    <li>Type a location name in the search box above and select from results</li>
                    <li>The system will automatically fetch and display the actual city/county boundary</li>
                    <li>The map shows the boundary area - use search only to change location</li>
                </ul>
            </div>
            <script>
            (function() {{
                if (typeof L === 'undefined') {{
                    setTimeout(arguments.callee, 100);
                    return;
                }}
                
                var map = L.map('zone-map').setView([{lat}, {lng}], 11);
                
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© OpenStreetMap contributors',
                    maxZoom: 18
                }}).addTo(map);
                
                // Center marker (non-draggable, just shows center point)
                var marker = L.marker([{lat}, {lng}]).addTo(map);
                marker.bindPopup('<b>{name}</b><br>Center Point').openPopup();
                
                // Load existing boundary if available
                var existingBoundaryData = document.getElementById('id_boundary_data').value;
                if (existingBoundaryData && existingBoundaryData.trim()) {{
                    try {{
                        var boundaryGeoJSON = JSON.parse(existingBoundaryData);
                        window.boundaryLayer = L.geoJSON(boundaryGeoJSON, {{
                            style: {{
                                color: '#4CAF50',
                                weight: 3,
                                fillOpacity: 0.1
                            }}
                        }}).addTo(map);
                        map.fitBounds(window.boundaryLayer.getBounds());
                    }} catch(e) {{
                        console.error('Error loading existing boundary:', e);
                    }}
                }}
                
                // Map interactions disabled - use search only to select locations
                
                // Autocomplete search
                var searchInput = document.getElementById('map-search');
                var searchResults = document.getElementById('search-results');
                var searchStatus = document.getElementById('search-status');
                var searchTimeout;
                
                searchInput.addEventListener('input', function() {{
                    clearTimeout(searchTimeout);
                    var query = this.value.trim();
                    
                    if (query.length < 2) {{
                        searchResults.style.display = 'none';
                        searchStatus.textContent = '';
                        return;
                    }}
                    
                    searchStatus.textContent = 'Searching...';
                    
                    searchTimeout = setTimeout(function() {{
                        fetch('https://nominatim.openstreetmap.org/search?format=json&q=' + encodeURIComponent(query) + '&countrycodes=gb&limit=5&polygon_geojson=1')
                            .then(r => r.json())
                            .then(data => {{
                                searchResults.innerHTML = '';
                                
                                if (data && data.length > 0) {{
                                    searchStatus.textContent = '';
                                    searchResults.style.display = 'block';
                                    
                                    data.forEach(function(item) {{
                                        var resultItem = document.createElement('div');
                                        resultItem.style.cssText = 'padding: 10px; cursor: pointer; border-bottom: 1px solid #f0f0f0; transition: background 0.2s;';
                                        resultItem.innerHTML = '<strong>' + item.name + '</strong><br><small style="color: #666;">' + item.display_name + '</small>';
                                        
                                        resultItem.addEventListener('mouseenter', function() {{
                                            this.style.background = '#f5f5f5';
                                        }});
                                        resultItem.addEventListener('mouseleave', function() {{
                                            this.style.background = 'white';
                                        }});
                                        
                                        resultItem.addEventListener('click', function() {{
                                            var lat = parseFloat(item.lat);
                                            var lng = parseFloat(item.lon);
                                            
                                            searchInput.value = item.display_name;
                                            searchResults.style.display = 'none';
                                            
                                            // Store boundary data if available
                                            if (item.geojson) {{
                                                // Update coordinates
                                                document.getElementById('id_center_latitude').value = lat.toFixed(6);
                                                document.getElementById('id_center_longitude').value = lng.toFixed(6);
                                                
                                                // Store boundary
                                                document.getElementById('id_boundary_data').value = JSON.stringify(item.geojson);
                                                searchStatus.innerHTML = '<span style="color: #2e7d32; font-weight: bold;">✓ Using actual boundary of ' + item.name + '</span>';
                                                
                                                // Draw boundary on map
                                                if (window.boundaryLayer) {{
                                                    map.removeLayer(window.boundaryLayer);
                                                }}
                                                window.boundaryLayer = L.geoJSON(item.geojson, {{
                                                    style: {{
                                                        color: '#4CAF50',
                                                        weight: 3,
                                                        fillOpacity: 0.1
                                                    }}
                                                }}).addTo(map);
                                                map.fitBounds(window.boundaryLayer.getBounds());
                                                
                                                // Update marker position
                                                marker.setLatLng([lat, lng]);
                                                marker.setPopupContent('<b>' + item.name + '</b><br>Center Point');
                                            }} else {{
                                                // No boundary available - don't allow selection
                                                searchStatus.innerHTML = '<span style="color: #d32f2f; font-weight: bold;">✗ Boundary not available for this location. Please select a different location.</span>';
                                                return;
                                            }}
                                            
                                            // Store OSM reference
                                            if (item.osm_type && item.osm_id) {{
                                                document.getElementById('id_osm_type').value = item.osm_type;
                                                document.getElementById('id_osm_id').value = item.osm_id;
                                            }}
                                        }});
                                        
                                        searchResults.appendChild(resultItem);
                                    }});
                                }} else {{
                                    searchStatus.textContent = 'No results found';
                                    searchStatus.style.color = '#999';
                                    searchResults.style.display = 'none';
                                }}
                            }})
                            .catch(err => {{
                                searchStatus.textContent = 'Search failed';
                                searchStatus.style.color = 'red';
                                searchResults.style.display = 'none';
                            }});
                    }}, 500);
                }});
                
                // Close results when clicking outside
                document.addEventListener('click', function(e) {{
                    if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {{
                        searchResults.style.display = 'none';
                    }}
                }});
            }})();
            </script>
        ''', 
        lat=lat, lng=lng, radius=radius, 
        name=obj.name if obj.pk else 'New Service Zone',
        boundary_data=boundary_data
        )
    get_interactive_map.short_description = 'Interactive Map'
    
    def get_map_preview(self, obj):
        """Embed a Google Maps preview showing the service zone."""
        if obj.center_latitude and obj.center_longitude:
            map_url = (
                f"https://maps.google.com/maps?q={obj.center_latitude},{obj.center_longitude}"
                f"&t=&z=13&ie=UTF8&iwloc=&output=embed"
            )
            return format_html(
                '<iframe width="100%" height="400" frameborder="0" scrolling="no" '
                'marginheight="0" marginwidth="0" src="{}"></iframe>'
                '<p><a href="https://www.google.com/maps?q={},{}" target="_blank">'
                'Open in Google Maps</a></p>',
                map_url, obj.center_latitude, obj.center_longitude
            )
        return "Save the zone to see map preview"
    get_map_preview.short_description = 'Map Preview'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "active", "created_at", "updated_at")
    list_filter = ("active",)
    search_fields = ("name", "description")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "min_hourly_rate", "min_hours_required", "active", "updated_at")
    list_filter = ("active", "category")
    search_fields = ("name", "description")
