#!/usr/bin/env python3
"""
Auto-generate MyST gallery pages with categorized notebook cards
Supports both explicit tags in notebook metadata and automatic content analysis
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict
import nbformat

def extract_notebook_metadata_and_content(notebook_path):
    """Extract explicit tags and metadata from Jupyter notebook"""
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
        
        # Check notebook-level metadata first
        if 'tags' in nb.metadata:
            explicit_tags.extend(nb.metadata['tags'])
        
        if 'gallery' in nb.metadata:
            gallery_meta = nb.metadata['gallery']
            explicit_title = gallery_meta.get('title')
            explicit_description = gallery_meta.get('description')
            if 'tags' in gallery_meta:
                explicit_tags.extend(gallery_meta['tags'])
        
        # Process cells
        for cell in nb.cells:
            if cell.cell_type == 'markdown':
                source = cell.source
                content.append(source)
                
                # Check for YAML frontmatter in first cell
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
                            
                            # Look for tags in keywords or custom tags field
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
                
                # Look for gallery comments in markdown cells (backup method)
                if 'tags' in cell.metadata and 'gallery-info' in cell.metadata['tags']:
                    lines = source.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('<!-- GALLERY_TAGS:'):
                            tags_str = line.replace('<!-- GALLERY_TAGS:', '').replace('-->', '').strip()
                            explicit_tags.extend([tag.strip() for tag in tags_str.split(',')])
                        elif line.startswith('<!-- GALLERY_TITLE:'):
                            if not explicit_title:  # Don't override frontmatter
                                explicit_title = line.replace('<!-- GALLERY_TITLE:', '').replace('-->', '').strip()
                        elif line.startswith('<!-- GALLERY_DESCRIPTION:'):
                            if not explicit_description:  # Don't override frontmatter
                                explicit_description = line.replace('<!-- GALLERY_DESCRIPTION:', '').replace('-->', '').strip()
                
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
        'zarr': ['zarr'],
        'gdal': ['gdal'],
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
    if any(term in content_lower for term in ['xcube']) or any('xcube' in imp for imp in imports):
        tags.add('xcube')
    if any(term in content_lower for term in ['gdal', 'osgeo']) or any('gdal' in imp or 'osgeo' in imp for imp in imports):
        tags.add('gdal')
    if any(term in content_lower for term in ['snap', 'snappy']):
        tags.add('snap')
    if any(term in content_lower for term in ['zarr']) or any('zarr' in imp for imp in imports):
        tags.add('zarr')
    
    # Data processing types
    if any(term in content_lower for term in ['l1c', 'level 1', 'raw data']):
        tags.add('level-1')
    if any(term in content_lower for term in ['l2a', 'level 2', 'surface reflectance']):
        tags.add('level-2')
    
    return list(tags)

def enhanced_tag_detection(notebook_data, filename):
    """Enhanced tag detection with explicit tag priority"""
    
    # Start with explicit tags if they exist
    if notebook_data['explicit_tags']:
        print(f"    ✅ Found explicit tags: {notebook_data['explicit_tags']}")
        return notebook_data['explicit_tags']
    
    # Fall back to automatic detection
    print(f"    🔍 No explicit tags found, using automatic detection...")
    return smart_tag_detection(notebook_data['content'], notebook_data['imports'], filename)

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
    """Enhanced title extraction with explicit title priority"""
    
    # Use explicit title if available
    if notebook_data['explicit_title']:
        return notebook_data['explicit_title']
    
    # Fall back to existing extraction logic
    return extract_notebook_title(notebook_path)

def generate_gallery_pages(notebook_tags, output_dir='notebooks'):
    """Generate MyST gallery pages with cards"""
    
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
                'Xarray': ['xarray'],
                'Xarray EOPF Plugin': ['xarray-eopf'],
                'XCube': ['xcube'], 
                'GDAL': ['gdal'],
                'SNAP': ['snap'],
                'STAC': ['stac'],
                'Zarr': ['zarr']
            },
            'file': f'{output_dir}/gallery-tools.md'
        }
    }
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)
    
    # Generate main gallery index
    with open(f'{output_dir}/gallery.md', 'w') as f:
        f.write("""# Notebook Gallery

Welcome to our comprehensive collection of Earth Observation Processing Framework (EOPF) sample notebooks. Browse by category to find notebooks that match your interests and use cases.

::::{grid} 1 1 2 3

:::{card} 🛰️ Sentinel Data
:link: gallery-sentinel

Explore notebooks for Sentinel-1, Sentinel-2, and Sentinel-3 missions
:::

:::{card} 🌍 Application Topics
:link: gallery-topics

Discover notebooks by application domain: land, marine, climate, emergency response
:::

:::{card} 🔧 Tools & Libraries
:link: gallery-tools

Learn different processing tools: XArray, GDAL, XCube, Zarr, and more
:::

::::

## All Notebooks

::::{grid} 1 1 2 3

""")
        
        # Add all notebooks as cards
        for notebook_path, meta in sorted(notebook_tags.items()):
            tags_str = ', '.join(meta['tags'][:3])
            if len(meta['tags']) > 3:
                tags_str += '...'
            
            f.write(f":::" + "{card} " + meta['title'] + "\n")
            f.write(f":link: {notebook_path}\n\n")
            if meta.get('description'):
                f.write(f"{meta['description']}\n\n")
            f.write(f"**Tags:** {tags_str}\n")
            # Add indicator for explicit vs automatic tags
            if meta.get('has_explicit_tags'):
                f.write(f" 🏷️\n")
            f.write(":::\n\n")
        
        f.write("::::\n")
    
    # Generate Sentinel category page
    with open(categories['sentinel']['file'], 'w') as f:
        f.write(f"# {categories['sentinel']['title']}\n\n")
        f.write(f"{categories['sentinel']['description']}\n\n")
        
        # Create tabs for each Sentinel mission
        sentinel_missions = {'sentinel-1': 'Sentinel-1', 'sentinel-2': 'Sentinel-2', 'sentinel-3': 'Sentinel-3'}
        
        for tag, mission_name in sentinel_missions.items():
            notebooks = [nb for nb in notebook_tags.items() if tag in nb[1]['tags']]
            if notebooks:
                f.write(f"## {mission_name}\n\n")
                f.write("::::{grid} 1 1 2 3\n")
                
                for notebook_path, meta in notebooks:
                    f.write(f":::" + "{card} " + meta['title'] + "\n")
                    f.write(f":link: {notebook_path}\n\n")
                    if meta.get('description'):
                        f.write(f"{meta['description']}\n\n")
                    f.write(f"**Tags:** {', '.join(meta['tags'])}\n")
                    if meta.get('has_explicit_tags'):
                        f.write(f" 🏷️\n")
                    f.write(":::\n\n")
                f.write("::::\n\n")
    
    # Generate Topics category page
    with open(categories['topics']['file'], 'w') as f:
        f.write(f"# {categories['topics']['title']}\n\n")
        f.write(f"{categories['topics']['description']}\n\n")
        
        for subcat_name, subcat_tags in categories['topics']['subcategories'].items():
            notebooks = []
            for notebook_path, meta in notebook_tags.items():
                if any(tag in meta['tags'] for tag in subcat_tags):
                    notebooks.append((notebook_path, meta))
            
            if notebooks:
                f.write(f"## {subcat_name}\n\n")
                f.write("::::{grid} 1 1 2 3\n")
                
                for notebook_path, meta in notebooks:
                    f.write(f":::" + "{card} " + meta['title'] + "\n")
                    f.write(f":link: {notebook_path}\n\n")
                    if meta.get('description'):
                        f.write(f"{meta['description']}\n\n")
                    f.write(f"**Tags:** {', '.join(meta['tags'])}\n")
                    if meta.get('has_explicit_tags'):
                        f.write(f" 🏷️\n")
                    f.write(":::\n\n")
                f.write("::::\n\n")
    
    # Generate Tools category page
    with open(categories['tools']['file'], 'w') as f:
        f.write(f"# {categories['tools']['title']}\n\n")
        f.write(f"{categories['tools']['description']}\n\n")
        
        for subcat_name, subcat_tags in categories['tools']['subcategories'].items():
            notebooks = []
            for notebook_path, meta in notebook_tags.items():
                if any(tag in meta['tags'] for tag in subcat_tags):
                    notebooks.append((notebook_path, meta))
            
            if notebooks:
                f.write(f"## {subcat_name}\n\n")
                f.write("::::{grid} 1 1 2 3\n")
                
                for notebook_path, meta in notebooks:
                    f.write(f":::" + "{card} " + meta['title'] + "\n")
                    f.write(f":link: {notebook_path}\n\n")
                    if meta.get('description'):
                        f.write(f"{meta['description']}\n\n")
                    f.write(f"**Tags:** {', '.join(meta['tags'])}\n")
                    if meta.get('has_explicit_tags'):
                        f.write(f" 🏷️\n")
                    f.write(":::\n\n")
                f.write("::::\n\n")

def analyze_notebook_content(notebook_tags):
    """Provide analysis of what was found"""
    tag_counts = Counter()
    explicit_count = 0
    automatic_count = 0
    
    for path, meta in notebook_tags.items():
        for tag in meta['tags']:
            tag_counts[tag] += 1
        
        if meta.get('has_explicit_tags'):
            explicit_count += 1
        else:
            automatic_count += 1
    
    print("\n📊 Content Analysis Summary:")
    print("=" * 50)
    
    print(f"\n📓 Total notebooks analyzed: {len(notebook_tags)}")
    print(f"🏷️  Notebooks with explicit tags: {explicit_count}")
    print(f"🤖 Notebooks with automatic tags: {automatic_count}")
    
    print(f"\n🏷️  Most common tags:")
    for tag, count in tag_counts.most_common(10):
        print(f"  {tag}: {count} notebooks")
    
    print(f"\n📂 Notebooks by folder:")
    folder_counts = Counter(meta['folder'] for meta in notebook_tags.values())
    for folder, count in folder_counts.items():
        print(f"  {folder}: {count} notebooks")

def analyze_notebooks(root_dir='notebooks'):
    """Analyze all notebooks and extract tags (explicit + automatic), titles, and metadata"""
    print(f"🔍 Analyzing notebooks in {root_dir} for gallery generation...")
    
    notebook_files = find_all_notebooks(root_dir)
    
    print(f"📓 Found {len(notebook_files)} Jupyter notebooks")
    
    notebook_tags = {}
    
    for file_path in notebook_files:
        print(f"  🔎 Analyzing: {file_path.name}")
        
        # Extract notebook metadata and content
        notebook_data = extract_notebook_metadata_and_content(file_path)
        
        relative_path = str(file_path.relative_to(root_dir)).replace('\\', '/')
        if relative_path.endswith('.ipynb'):
            relative_path = relative_path[:-6]  # Remove .ipynb extension
        
        # Get tags (explicit first, then automatic)
        tags = enhanced_tag_detection(notebook_data, file_path.name)
        
        # Get title (explicit first, then automatic)
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
            print(f"    ⚠️  No tags detected for {file_path.name}")
    
    return notebook_tags

def generate_toc_entries(notebook_tags):
    """Generate MyST TOC entries for all notebooks"""
    print("\n📋 MyST TOC entries for myst.yml:")
    print("Add these to your 'toc:' section:")
    print("\n```yaml")
    
    for notebook_path in sorted(notebook_tags.keys()):
        print(f"        - file: notebooks/{notebook_path}")
    
    print("```")

def print_tag_examples():
    """Print examples of how to add explicit tags to notebooks"""
    print("\n📝 How to add explicit tags to your notebooks:")
    print("=" * 60)
    
    print("\n🟢 Method 1: YAML Frontmatter (Recommended)")
    print("Add this to the first markdown cell:")
    print("""
---
title: Your Notebook Title
subtitle: Descriptive subtitle for gallery
tags: ["sentinel-2", "land", "xarray", "deforestation"]
keywords: ["earth observation", "remote sensing", "forest monitoring"]
authors:
  - name: Your Name
    orcid: 0000-0000-0000-0000
date: 2025-03-04
---
""")
    
    print("\n🟡 Method 2: Notebook Metadata")
    print("In JupyterLab, edit notebook metadata to include:")
    print("""
{
  "metadata": {
    "tags": ["sentinel-2", "land", "xarray"],
    "gallery": {
      "title": "Custom Gallery Title",
      "description": "Custom description for gallery card"
    }
  }
}
""")
    
    print("\n🟠 Method 3: Markdown Cell Comments (Legacy)")
    print("Add these comments to any markdown cell:")
    print("""
<!-- GALLERY_TAGS: sentinel-2, land, xarray -->
<!-- GALLERY_TITLE: Custom Gallery Title -->
<!-- GALLERY_DESCRIPTION: Custom description for gallery card -->
""")
    
    print("\n📝 Available tag categories:")
    print("  Sentinel: sentinel-1, sentinel-2, sentinel-3")
    print("  Topics: land, emergency, climate-change, marine, security")
    print("  Tools: xarray, xcube, gdal, snap, zarr")
    print("  Levels: level-1, level-2")
    print("\n💡 Priority: Frontmatter > Notebook Metadata > Cell Comments > Auto-detection")

if __name__ == '__main__':
    ROOT_DIR = 'notebooks'  # Change this to your notebooks directory
    
    # Clean up existing gallery files first
    gallery_files = ['notebooks/gallery.md', 'notebooks/gallery-sentinel.md', 'notebooks/gallery-topics.md', 'notebooks/gallery-tools.md']
    for file_path in gallery_files:
        if Path(file_path).exists():
            Path(file_path).unlink()
            print(f"🗑️  Removed old {file_path}")
    
    print("🧠 Notebook analysis starting...")
    print("✨ Supports both explicit tags (in metadata) and automatic detection!")
    
    notebook_tags = analyze_notebooks(ROOT_DIR)
    
    if notebook_tags:
        analyze_notebook_content(notebook_tags)
        
        print(f"\n📋 Tagged notebooks:")
        for path, meta in sorted(notebook_tags.items()):
            explicit_indicator = " 🏷️" if meta.get('has_explicit_tags') else " 🤖"
            print(f"  📓 {path}{explicit_indicator}")
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
        
        # Generate TOC entries
        generate_toc_entries(notebook_tags)
        
        # Show tagging examples
        print_tag_examples()
        
        print("✅ Done! Enhanced gallery generation complete.")
        print(f"✅ Generated gallery files:")
        print(f"  - {ROOT_DIR}/gallery.md (main gallery)")
        print(f"  - {ROOT_DIR}/gallery-sentinel.md")
        print(f"  - {ROOT_DIR}/gallery-topics.md") 
        print(f"  - {ROOT_DIR}/gallery-tools.md")
        
        print(f"\n💡 Legend: 🏷️ = explicit tags, 🤖 = automatic detection")
    else:
        print("❌ No notebooks found with detectable content. Check your notebook directory.")
