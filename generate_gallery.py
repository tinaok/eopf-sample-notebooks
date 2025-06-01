#!/usr/bin/env python3
"""
Auto-generate MyST gallery pages with categorized notebook cards
Supports both explicit tags in notebook metadata and automatic content analysis
"""

import json
import re
import argparse
from pathlib import Path
from collections import Counter, defaultdict
import nbformat

def extract_notebook_metadata_and_content(notebook_path):
    """Extract explicit tags and metadata from Jupyter notebook frontmatter only"""
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        content = []
        imports = []
        explicit_tags = []
        explicit_title = None
        explicit_description = None
        explicit_subtitle = None
        explicit_authors = []
        explicit_keywords = None
        
        # Process cells - only look for YAML frontmatter in first markdown cell
        for cell in nb.cells:
            if cell.cell_type == 'markdown':
                source = cell.source
                content.append(source)
                
                # Check for YAML frontmatter in first markdown cell only
                if source.strip().startswith('---'):
                    try:
                        import yaml
                        # Extract YAML frontmatter
                        lines = source.split('\n')
                        yaml_end = -1
                        for i, line in enumerate(lines[1:], 1):
                            if line.strip() == '---':
                                yaml_end = i
                                break
                        
                        if yaml_end > 0:
                            yaml_content = '\n'.join(lines[1:yaml_end])
                            frontmatter = yaml.safe_load(yaml_content)
                            
                            # Extract metadata from frontmatter
                            if 'title' in frontmatter:
                                explicit_title = frontmatter['title']
                            if 'subtitle' in frontmatter:
                                explicit_subtitle = frontmatter['subtitle']
                            if 'keywords' in frontmatter:
                                if isinstance(frontmatter['keywords'], str):
                                    explicit_keywords = frontmatter['keywords']
                                elif isinstance(frontmatter['keywords'], list):
                                    explicit_keywords = ', '.join(frontmatter['keywords'])
                            if 'authors' in frontmatter:
                                explicit_authors = frontmatter['authors']
                            
                            # Look for tags in frontmatter
                            if 'tags' in frontmatter:
                                if isinstance(frontmatter['tags'], list):
                                    explicit_tags.extend(frontmatter['tags'])
                                elif isinstance(frontmatter['tags'], str):
                                    explicit_tags.extend([tag.strip() for tag in frontmatter['tags'].split(',')])
                            
                            # Auto-generate tags from keywords if no explicit tags
                            if not explicit_tags and explicit_keywords:
                                # Convert keywords to potential tags
                                keyword_tags = keywords_to_tags(explicit_keywords)
                                explicit_tags.extend(keyword_tags)
                    
                    except ImportError:
                        print("    ⚠️  PyYAML not available for frontmatter parsing")
                    except Exception as e:
                        print(f"    ⚠️  Error parsing frontmatter: {e}")
                
                # Break after first markdown cell (frontmatter should be first)
                break
                
            elif cell.cell_type == 'code':
                source = cell.source
                content.append(source)
                
                # Extract imports
                for line in source.split('\n'):
                    line = line.strip()
                    if line.startswith(('import ', 'from ')) and not line.startswith('#'):
                        imports.append(line)
        
        # Generate description from subtitle if not explicitly set
        if not explicit_description and explicit_subtitle:
            explicit_description = explicit_subtitle
        
        return {
            'content': ' '.join(content),
            'imports': imports,
            'explicit_tags': list(set(explicit_tags)),  # Remove duplicates
            'explicit_title': explicit_title,
            'explicit_description': explicit_description,
            'explicit_subtitle': explicit_subtitle,
            'explicit_authors': explicit_authors,
            'explicit_keywords': explicit_keywords
        }
        
    except Exception as e:
        print(f"Error reading {notebook_path}: {e}")
        return {
            'content': "",
            'imports': [],
            'explicit_tags': [],
            'explicit_title': None,
            'explicit_description': None,
            'explicit_subtitle': None,
            'explicit_authors': [],
            'explicit_keywords': None
        }

def keywords_to_tags(keywords_str):
    """Convert keywords string to relevant tags"""
    tags = []
    keywords_lower = keywords_str.lower()
    
    # Map keywords to our tag system
    keyword_mappings = {
        'sentinel': ['sentinel-1', 'sentinel-2', 'sentinel-3'],
        'earth observation': ['earth-observation'],
        'remote sensing': ['remote-sensing'],
        'forest': ['land'],
        'deforestation': ['land'],
        'agriculture': ['land'],
        'ocean': ['marine'],
        'climate': ['climate-change'],
        'emergency': ['emergency'],
        'xarray': ['xarray'],
        'eopf': ['xarray-eopf'],
        'zarr': ['zarr'],
        'gdal': ['gdal'],
        'stac': ['stac'],
        'pystac': ['stac'],
        'processing': ['data-processing']
    }
    
    for keyword, tag_list in keyword_mappings.items():
        if keyword in keywords_lower:
            tags.extend(tag_list)
    
    return list(set(tags))

def smart_tag_detection(content, imports, filename):
    """Intelligently detect tags based on content analysis"""
    tags = set()
    content_lower = content.lower()
    
    # Sentinel mission detection
    if any(term in content_lower for term in ['sentinel-1', 'sentinel1', 's1']):
        tags.add('sentinel-1')
    if any(term in content_lower for term in ['sentinel-2', 'sentinel2', 's2']):
        tags.add('sentinel-2')
    if any(term in content_lower for term in ['sentinel-3', 'sentinel3', 's3']):
        tags.add('sentinel-3')
    
    # Application topics
    if any(term in content_lower for term in ['deforestation', 'forest', 'land cover', 'agriculture', 'vegetation', 'ndvi']):
        tags.add('land')
    if any(term in content_lower for term in ['flood', 'emergency', 'disaster', 'landslide', 'fire']):
        tags.add('emergency')
    if any(term in content_lower for term in ['climate', 'temperature', 'precipitation', 'weather']):
        tags.add('climate-change')
    if any(term in content_lower for term in ['ocean', 'sea', 'marine', 'water', 'coastal']):
        tags.add('marine')
    if any(term in content_lower for term in ['security', 'monitoring', 'surveillance']):
        tags.add('security')
    
    # Tools and libraries
    if any(term in content_lower for term in ['xarray', 'xr.']) or any('xarray' in imp for imp in imports):
        tags.add('xarray')
    if any(term in content_lower for term in ['xarray_eopf', 'xarray-eopf', 'eopf']) or any('xarray_eopf' in imp for imp in imports):
        tags.add('xarray-eopf')
    if any(term in content_lower for term in ['xcube']) or any('xcube' in imp for imp in imports):
        tags.add('xcube')
    if any(term in content_lower for term in ['gdal', 'osgeo']) or any('gdal' in imp or 'osgeo' in imp for imp in imports):
        tags.add('gdal')
    if any(term in content_lower for term in ['snap', 'snappy']):
        tags.add('snap')
    if any(term in content_lower for term in ['stac', 'pystac']) or any('stac' in imp or 'pystac' in imp for imp in imports):
        tags.add('stac')
    if any(term in content_lower for term in ['zarr']) or any('zarr' in imp for imp in imports):
        tags.add('zarr')
    
    # Data processing types
    if any(term in content_lower for term in ['l1c', 'level 1', 'raw data']):
        tags.add('level-1')
    if any(term in content_lower for term in ['l2a', 'level 2', 'surface reflectance']):
        tags.add('level-2')
    
    return list(tags)

def enhanced_tag_detection(notebook_data, filename):
    """Extract tags from frontmatter only"""
    
    # Only use frontmatter tags
    if notebook_data['explicit_tags']:
        print(f"    ✅ Found frontmatter tags: {notebook_data['explicit_tags']}")
        return notebook_data['explicit_tags']
    
    # No fallback - frontmatter only
    print(f"    ⚠️  No frontmatter tags found")
    return []

def find_all_notebooks(root_dir):
    """Find all notebooks in directory structure"""
    notebook_files = []
    root_path = Path(root_dir)
    
    for notebook_file in root_path.rglob('*.ipynb'):
        # Skip hidden files and checkpoint files
        if not any(part.startswith('.') for part in notebook_file.parts):
            notebook_files.append(notebook_file)
    
    return notebook_files

def extract_notebook_title(notebook_path):
    """Extract title from notebook metadata or first heading"""
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        # Check notebook metadata first
        if 'title' in nb.metadata:
            return nb.metadata['title']
        
        # Look for first markdown heading
        for cell in nb.cells:
            if cell.cell_type == 'markdown':
                lines = cell.source.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('# '):
                        return line[2:].strip()
        
        # Fallback to filename
        return notebook_path.stem.replace('-', ' ').replace('_', ' ').title()
        
    except Exception:
        return notebook_path.stem.replace('-', ' ').replace('_', ' ').title()

def enhanced_title_extraction(notebook_path, notebook_data):
    """Enhanced title extraction with frontmatter priority"""
    
    # Use frontmatter title if available
    if notebook_data['explicit_title']:
        return notebook_data['explicit_title']
    
    # Fall back to existing extraction logic
    return extract_notebook_title(notebook_path)

def render_tags_html(tags, has_explicit_tags=False, max_visible=3):
    """Render tags as styled HTML elements"""
    if not tags:
        return ""
    
    visible_tags = tags[:max_visible]
    remaining_count = len(tags) - max_visible
    
    tag_html = '<div class="gallery-tags">'
    
    # Render visible tags
    for tag in visible_tags:
        # Normalize tag name for CSS class
        css_class = tag.replace('-', '-').replace('_', '-')
        tag_html += f'<span class="tag {css_class}">{tag}</span>'
    
    # Add "more" indicator if there are additional tags
    if remaining_count > 0:
        tag_html += f'<span class="tag-more">+{remaining_count} more</span>'
    
    # Add explicit/automatic indicator
    if has_explicit_tags:
        tag_html += '<span class="tag-indicator explicit" title="Explicit tags">🏷️</span>'
    else:
        tag_html += '<span class="tag-indicator automatic" title="Automatic tags">🤖</span>'
    
    tag_html += '</div>'
    return tag_html

def render_simple_tags(tags, has_explicit_tags=False, max_visible=3):
    """Render tags as simple text (MyST-compatible)"""
    if not tags:
        return ""
    
    visible_tags = tags[:max_visible]
    remaining_count = len(tags) - max_visible
    
    # Create simple tag display
    tag_text = "**Tags:** " + ", ".join(visible_tags)
    
    if remaining_count > 0:
        tag_text += f", +{remaining_count} more"
    
    # Add indicator for explicit vs automatic tags
    if has_explicit_tags:
        tag_text += " 🏷️"
    else:
        tag_text += " 🤖"
    
    return tag_text

def generate_gallery_pages(notebook_tags, output_dir='notebooks'):
    """Generate MyST gallery pages with enhanced styling"""
    
    categories = {
        'sentinel': {
            'title': 'Sentinel Data',
            'description': 'Notebooks showcasing Sentinel mission data processing and analysis',
            'tags': ['sentinel-1', 'sentinel-2', 'sentinel-3'],
            'file': f'{output_dir}/gallery-sentinel.md'
        },
        'topics': {
            'title': 'Application Topics',
            'description': 'Notebooks organized by Earth observation application domains',
            'subcategories': {
                'Land Applications': ['land'],
                'Emergency Response': ['emergency'], 
                'Climate Monitoring': ['climate-change'],
                'Marine Applications': ['marine'],
                'Security Applications': ['security']
            },
            'file': f'{output_dir}/gallery-topics.md'
        },
        'tools': {
            'title': 'Tools & Libraries',
            'description': 'Notebooks demonstrating different software tools and libraries',
            'subcategories': {
                'XArray': ['xarray'],
                'XCube': ['xcube'], 
                'GDAL': ['gdal'],
                'SNAP': ['snap'],
                'Zarr': ['zarr']
            },
            'file': f'{output_dir}/gallery-tools.md'
        }
    }
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)
    
    # Generate main gallery index
    with open(f'{output_dir}/gallery.md', 'w') as f:
        f.write("""---
title: Notebook Gallery
---

# Notebook Gallery

Welcome to our comprehensive collection of Earth Observation Processing Framework (EOPF) sample notebooks. Browse by category to find notebooks that match your interests and use cases.

```{gallery-categories}
```

## All Notebooks

```{gallery-grid}
:category: all
:columns: 1 1 2 3
```

""")
        
        f.write("<!-- Generated by gallery plugin -->\n")
    
    # Generate Sentinel category page
    with open(categories['sentinel']['file'], 'w') as f:
        f.write(f"""---
title: {categories['sentinel']['title']}
---

# {categories['sentinel']['title']}

{categories['sentinel']['description']}

## Sentinel-1

```{{gallery-grid}}
:category: sentinel-1
:columns: 1 1 2 3
```

## Sentinel-2

```{{gallery-grid}}
:category: sentinel-2
:columns: 1 1 2 3
```

## Sentinel-3

```{{gallery-grid}}
:category: sentinel-3
:columns: 1 1 2 3
```

""")
    
    # Generate Topics category page
    with open(categories['topics']['file'], 'w') as f:
        f.write(f"""---
title: {categories['topics']['title']}
---

# {categories['topics']['title']}

{categories['topics']['description']}

## Land Applications

```{{gallery-grid}}
:category: land
:columns: 1 1 2 3
```

## Emergency Response

```{{gallery-grid}}
:category: emergency
:columns: 1 1 2 3
```

## Climate Monitoring

```{{gallery-grid}}
:category: climate-change
:columns: 1 1 2 3
```

## Marine Applications

```{{gallery-grid}}
:category: marine
:columns: 1 1 2 3
```

## Security Applications

```{{gallery-grid}}
:category: security
:columns: 1 1 2 3
```

""")
    
    # Generate Tools category page
    with open(categories['tools']['file'], 'w') as f:
        f.write(f"""---
title: {categories['tools']['title']}
---

# {categories['tools']['title']}

{categories['tools']['description']}

## Xarray

```{{gallery-grid}}
:category: xarray
:columns: 1 1 2 3
```

## Xarray-eopf Plugin

```{{gallery-grid}}
:category: xarray-eopf
:columns: 1 1 2 3
```

## XCube

```{{gallery-grid}}
:category: xcube
:columns: 1 1 2 3
```

## GDAL

```{{gallery-grid}}
:category: gdal
:columns: 1 1 2 3
```

## SNAP

```{{gallery-grid}}
:category: snap
:columns: 1 1 2 3
```

## STAC

```{{gallery-grid}}
:category: stac
:columns: 1 1 2 3
```

## Zarr

```{{gallery-grid}}
:category: zarr
:columns: 1 1 2 3
```

""")

def analyze_notebook_content(notebook_tags):
    """Provide analysis of what was found"""
    tag_counts = Counter()
    
    for path, meta in notebook_tags.items():
        for tag in meta['tags']:
            tag_counts[tag] += 1
    
    print("\n📊 Content Analysis Summary:")
    print("=" * 50)
    
    print(f"\n📓 Total notebooks with frontmatter tags: {len(notebook_tags)}")
    
    print(f"\n🏷️  Most common tags:")
    for tag, count in tag_counts.most_common(10):
        print(f"  {tag}: {count} notebooks")
    
    print(f"\n📂 Notebooks by folder:")
    folder_counts = Counter(meta['folder'] for meta in notebook_tags.values())
    for folder, count in folder_counts.items():
        print(f"  {folder}: {count} notebooks")

def analyze_notebooks(root_dir='notebooks'):
    """Analyze all notebooks and extract tags from frontmatter"""
    print(f"🔍 Analyzing notebooks in {root_dir} for frontmatter tags...")
    
    notebook_files = find_all_notebooks(root_dir)
    
    print(f"📓 Found {len(notebook_files)} Jupyter notebooks")
    
    notebook_tags = {}
    skipped_count = 0
    
    for file_path in notebook_files:
        print(f"  🔎 Analyzing: {file_path.name}")
        
        # Extract notebook metadata and content
        notebook_data = extract_notebook_metadata_and_content(file_path)
        
        relative_path = str(file_path.relative_to(root_dir)).replace('\\', '/')
        if relative_path.endswith('.ipynb'):
            relative_path = relative_path[:-6]  # Remove .ipynb extension
        
        # Get tags from frontmatter only
        tags = enhanced_tag_detection(notebook_data, file_path.name)
        
        # Get title (frontmatter first, then automatic)
        title = enhanced_title_extraction(file_path, notebook_data)
        
        if tags:  # Only include if we found tags
            notebook_tags[relative_path] = {
                'title': title,
                'description': notebook_data['explicit_description'] or '',
                'tags': tags,
                'full_path': str(file_path),
                'folder': str(file_path.parent.relative_to(root_dir)) if file_path.parent != Path(root_dir) else 'root',
                'imports': notebook_data['imports'][:5],
                'has_explicit_tags': bool(notebook_data['explicit_tags'])
            }
        else:
            print(f"    ❌ Skipped: No frontmatter tags found for {file_path.name}")
            skipped_count += 1
    
    if skipped_count > 0:
        print(f"\n⚠️  Skipped {skipped_count} notebooks without frontmatter tags")
        print("💡 Add YAML frontmatter with tags to include these notebooks")
    
    return notebook_tags

def create_gallery_css(output_dir='notebooks'):
    """Create the enhanced gallery CSS file"""
    css_content = """/* Enhanced Gallery CSS with Stylish Tags */

/* Main gallery grid styling */
.gallery-grid .sd-card,
.notebook-grid .sd-card {
  transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
  border: 1px solid #e1e5e9;
  border-radius: 12px;
  overflow: hidden;
  height: 100%;
  background: #ffffff;
}

.gallery-grid .sd-card:hover,
.notebook-grid .sd-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
  border-color: #007bff;
}

/* Card headers */
.sd-card-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white !important;
  font-weight: 600;
  padding: 1rem;
  border-radius: 12px 12px 0 0;
}

.sd-card-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* Enhanced Tag Styling */
.gallery-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 1rem;
  align-items: center;
}

.gallery-tag {
  display: inline-flex;
  align-items: center;
  padding: 0.375rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-decoration: none;
  color: white;
  background: #6c757d;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  white-space: nowrap;
}

.gallery-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  text-decoration: none;
  color: white;
}

/* Tag Categories with Color Coding */

/* Sentinel Mission Tags */
.gallery-tag.tag-sentinel-1 {
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.gallery-tag.tag-sentinel-2 {
  background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.gallery-tag.tag-sentinel-3 {
  background: linear-gradient(135deg, #45b7d1 0%, #2980b9 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

/* Application Topic Tags */
.gallery-tag.tag-land {
  background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.gallery-tag.tag-emergency {
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.gallery-tag.tag-climate-change {
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.gallery-tag.tag-marine {
  background: linear-gradient(135deg, #1abc9c 0%, #16a085 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.gallery-tag.tag-security {
  background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

/* Tool/Library Tags */
.gallery-tag.tag-xarray {
  background: linear-gradient(135deg, #f39c12 0%, #d68910 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.gallery-tag.tag-xarray-eopf {
  background: linear-gradient(135deg, #e67e22 0%, #ca6f1e 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.gallery-tag.tag-xcube {
  background: linear-gradient(135deg, #e67e22 0%, #d35400 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.gallery-tag.tag-gdal {
  background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.gallery-tag.tag-snap {
  background: linear-gradient(135deg, #8e44ad 0%, #7d3c98 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.gallery-tag.tag-stac {
  background: linear-gradient(135deg, #2c3e50 0%, #1b2631 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.gallery-tag.tag-zarr {
  background: linear-gradient(135deg, #16a085 0%, #138d75 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

/* Data Level Tags */
.tag.level-1 {
  background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.tag.level-2 {
  background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

/* Special Tags */
.tag.deforestation {
  background: linear-gradient(135deg, #c0392b 0%, #a93226 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.tag.earth-observation {
  background: linear-gradient(135deg, #3498db 0%, #2874a6 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

.tag.remote-sensing {
  background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
  border-color: rgba(255, 255, 255, 0.3);
}

/* Tag Icons */
.tag::before {
  content: "🏷️";
  margin-right: 0.375rem;
  font-size: 0.7rem;
}

.tag.sentinel-1::before { content: "🛰️"; }
.tag.sentinel-2::before { content: "🛰️"; }
.tag.sentinel-3::before { content: "🛰️"; }
.tag.land::before { content: "🌱"; }
.tag.emergency::before { content: "🚨"; }
.tag.climate-change::before { content: "🌡️"; }
.tag.marine::before { content: "🌊"; }
.tag.security::before { content: "🔒"; }
.tag.xarray::before { content: "📊"; }
.tag.xarray-eopf::before { content: "🔌"; }
.tag.gdal::before { content: "🗺️"; }
.tag.stac::before { content: "📋"; }
.tag.zarr::before { content: "📦"; }

/* Tag counter indicator */
.gallery-tag-more {
  background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  padding: 0.375rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
}

/* Explicit vs Automatic tag indicators */
.tag-indicator {
  display: inline-flex;
  align-items: center;
  margin-left: 0.5rem;
  font-size: 1rem;
  opacity: 0.7;
}

.tag-indicator.explicit {
  color: #2ecc71;
}

.tag-indicator.automatic {
  color: #f39c12;
}

/* Card description styling */
.card-description {
  color: #6c757d;
  font-size: 0.9rem;
  line-height: 1.4;
  margin-bottom: 1rem;
  flex-grow: 1;
}

/* Responsive design */
@media (max-width: 768px) {
  .gallery-grid,
  .notebook-grid {
    grid-template-columns: 1fr !important;
  }
  
  .tag {
    font-size: 0.7rem;
    padding: 0.3rem 0.6rem;
  }
  
  .sd-card-body {
    padding: 1rem;
  }
}

/* Category section styling */
.category-section {
  margin-bottom: 3rem;
}

.category-section h2 {
  color: #2c3e50;
  border-bottom: 3px solid #3498db;
  padding-bottom: 0.5rem;
  margin-bottom: 1.5rem;
  font-weight: 700;
}

/* Main gallery overview cards */
.gallery-overview .sd-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border: 2px solid #dee2e6;
}

.gallery-overview .sd-card:hover {
  background: linear-gradient(135deg, #e9ecef 0%, #dee2e6 100%);
  border-color: #007bff;
}

/* Loading animation */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.sd-card {
  animation: fadeInUp 0.5s ease-out;
}
"""
    
    # Create static directory if it doesn't exist
    static_dir = Path(output_dir) / 'static'
    static_dir.mkdir(exist_ok=True)
    
    # Write CSS file
    css_file = static_dir / 'gallery.css'
    with open(css_file, 'w') as f:
        f.write(css_content)
    
    print(f"✅ Created enhanced CSS: {css_file}")

def export_metadata_for_plugin(notebook_tags, output_dir='notebooks'):
    """Export notebook metadata for MyST plugin"""
    metadata_file = Path(output_dir) / '.gallery-metadata.json'
    
    # Convert metadata to plugin-friendly format
    plugin_metadata = {}
    for path, meta in notebook_tags.items():
        plugin_metadata[path] = {
            'title': meta['title'],
            'description': meta.get('description', ''),
            'tags': meta['tags'],
            'has_explicit_tags': meta.get('has_explicit_tags', False),
            'folder': meta['folder']
        }
    
    with open(metadata_file, 'w') as f:
        json.dump(plugin_metadata, f, indent=2)
    
    print(f"✅ Exported metadata: {metadata_file}")

def generate_toc_entries(notebook_tags):
    """Generate MyST TOC entries for all notebooks"""
    print("\n📋 MyST TOC entries for myst.yml:")
    print("Add these to your 'toc:' section:")
    print("\n```yaml")
    
    for notebook_path in sorted(notebook_tags.keys()):
        print(f"        - file: notebooks/{notebook_path}")
    
    print("```")
    """Generate MyST TOC entries for all notebooks"""
    print("\n📋 MyST TOC entries for myst.yml:")
    print("Add these to your 'toc:' section:")
    print("\n```yaml")
    
    for notebook_path in sorted(notebook_tags.keys()):
        print(f"        - file: notebooks/{notebook_path}")
    
    print("```")

def print_tag_examples():
    """Print examples of how to add frontmatter tags to notebooks"""
    print("\n📝 How to add frontmatter tags to your notebooks:")
    print("=" * 60)
    
    print("\n🟢 YAML Frontmatter (Recommended)")
    print("Add this to the FIRST markdown cell of your notebook:")
    print("""
---
title: Your Notebook Title
subtitle: Descriptive subtitle for gallery
tags: ["sentinel-2", "land", "xarray", "deforestation"]
keywords: ["earth observation", "remote sensing", "forest monitoring"]
authors:
  - name: Your Name
    orcid: 0000-0000-0000-0000
    github: yourusername
    affiliations:
      - id: Your Institution
        institution: Your Institution Name
        ror: your-ror-id
date: 2025-03-04
---

# Your Notebook Content Starts Here
...
""")
    
    print("\n📝 Available tag categories:")
    print("  Sentinel: sentinel-1, sentinel-2, sentinel-3")
    print("  Topics: land, emergency, climate-change, marine, security")
    print("  Tools: xarray, xarray-eopf, xcube, gdal, snap, stac, zarr")
    print("  Levels: level-1, level-2")
    print("\n💡 Tags from frontmatter take priority over automatic detection")
    print("💡 If no tags are found, keywords will be converted to tags automatically")
    print("\n🚫 To disable auto-tagging: python generate_gallery.py --no-auto-tag")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Generate MyST gallery pages from Jupyter notebooks with frontmatter tags',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_gallery.py                    # Generate gallery from notebooks/
  python generate_gallery.py --dir my_notebooks # Custom directory
  python generate_gallery.py --verbose          # Verbose output
        """
    )
    
    parser.add_argument(
        '--dir', '--directory',
        default='notebooks',
        help='Directory containing notebooks (default: notebooks)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()

if __name__ == '__main__':
    # Parse command line arguments
    args = parse_arguments()
    
    ROOT_DIR = args.dir
    
    # Clean up existing gallery files first
    gallery_files = [f'{ROOT_DIR}/gallery.md', f'{ROOT_DIR}/gallery-sentinel.md', 
                     f'{ROOT_DIR}/gallery-topics.md', f'{ROOT_DIR}/gallery-tools.md']
    for file_path in gallery_files:
        if Path(file_path).exists():
            Path(file_path).unlink()
            if args.verbose:
                print(f"🗑️  Removed old {file_path}")
    
    # Display configuration
    print("🧠 Notebook Gallery Generator")
    print("=" * 40)
    print(f"📁 Directory: {ROOT_DIR}")
    print("🏷️  Only notebooks with YAML frontmatter tags will be included")
    print()
    
    print("🔍 Starting notebook analysis...")
    notebook_tags = analyze_notebooks(ROOT_DIR)
    
    if notebook_tags:
        analyze_notebook_content(notebook_tags)
        
        if args.verbose:
            print(f"\n📋 Tagged notebooks:")
            for path, meta in sorted(notebook_tags.items()):
                frontmatter_indicator = " 🏷️" if meta.get('has_explicit_tags') else " 🤖"
                print(f"  📓 {path}{frontmatter_indicator}")
                print(f"     📂 {meta['folder']}")
                print(f"     🏷️  {', '.join(meta['tags'])}")
                if meta.get('description'):
                    print(f"     📝 {meta['description'][:50]}...")
                if meta['imports']:
                    print(f"     📦 Imports: {', '.join(meta['imports'][:3])}")
                print()
        
        # Generate gallery pages
        print("\n📝 Generating gallery pages...")
        generate_gallery_pages(notebook_tags, ROOT_DIR)
        
        # Export metadata for MyST plugin
        print("📄 Exporting metadata for MyST plugin...")
        export_metadata_for_plugin(notebook_tags, ROOT_DIR)
        
        # Generate TOC entries
        generate_toc_entries(notebook_tags)
        
        # Show tagging examples if few notebooks found
        if len(notebook_tags) < 3:
            print_tag_examples()
        
        print("\n✅ Gallery generation complete!")
        print(f"✅ Generated gallery files:")
        print(f"  - {ROOT_DIR}/gallery.md (main gallery)")
        print(f"  - {ROOT_DIR}/gallery-sentinel.md")
        print(f"  - {ROOT_DIR}/gallery-topics.md") 
        print(f"  - {ROOT_DIR}/gallery-tools.md")
        
        print(f"\n💡 All notebooks use YAML frontmatter tags")
    else:
        print("❌ No notebooks found with tags.")
        if not enable_auto_tagging:
            print("💡 Try removing --no-auto-tag to enable automatic tag detection")
        else:
            print("💡 Add frontmatter tags to your notebooks or check your notebook directory")
        print_tag_examples()
