#!/usr/bin/env python3
"""
Auto-generate MyST gallery pages with categorized notebook cards
Analyzes notebook content and creates tagged gallery pages
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict
import nbformat

def extract_notebook_content(notebook_path):
    """Extract content from Jupyter notebook for analysis"""
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        content = []
        imports = []
        
        for cell in nb.cells:
            if cell.cell_type == 'markdown':
                content.append(cell.source)
            elif cell.cell_type == 'code':
                source = cell.source
                content.append(source)
                
                # Extract imports
                for line in source.split('\n'):
                    line = line.strip()
                    if line.startswith(('import ', 'from ')) and not line.startswith('#'):
                        imports.append(line)
        
        return ' '.join(content), imports
        
    except Exception as e:
        print(f"Error reading {notebook_path}: {e}")
        return "", []

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
            f.write(f"**Tags:** {tags_str}\n")
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
                    description = meta.get('description', '')
                    if description:
                        f.write(f"{description}\n\n")
                    f.write(f"**Tags:** {', '.join(meta['tags'])}\n")
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
                    description = meta.get('description', '')
                    if description:
                        f.write(f"{description}\n\n")
                    f.write(f"**Tags:** {', '.join(meta['tags'])}\n")
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
                    description = meta.get('description', '')
                    if description:
                        f.write(f"{description}\n\n")
                    f.write(f"**Tags:** {', '.join(meta['tags'])}\n")
                    f.write(":::\n\n")
                f.write("::::\n\n")

def analyze_notebook_content(notebook_tags):
    """Provide analysis of what was found"""
    tag_counts = Counter()
    
    for path, meta in notebook_tags.items():
        for tag in meta['tags']:
            tag_counts[tag] += 1
    
    print("\n📊 Content Analysis Summary:")
    print("=" * 50)
    
    print(f"\n📓 Total notebooks analyzed: {len(notebook_tags)}")
    print(f"\n🏷️  Most common tags:")
    for tag, count in tag_counts.most_common(10):
        print(f"  {tag}: {count} notebooks")
    
    print(f"\n📂 Notebooks by folder:")
    folder_counts = Counter(meta['folder'] for meta in notebook_tags.values())
    for folder, count in folder_counts.items():
        print(f"  {folder}: {count} notebooks")

def generate_auto_tags(root_dir='notebooks'):
    """Generate tags with smart content analysis"""
    print(f"🔍 Analyzing content in {root_dir} and all subfolders...")
    
    notebook_files = find_all_notebooks(root_dir)
    
    print(f"📓 Found {len(notebook_files)} Jupyter notebooks")
    
    notebook_tags = {}
    
    for file_path in notebook_files:
        print(f"  🔎 Analyzing: {file_path.name}")
        
        content, imports = extract_notebook_content(file_path)
        relative_path = str(file_path.relative_to(root_dir)).replace('\\', '/')
        if relative_path.endswith('.ipynb'):
            relative_path = relative_path[:-6]  # Remove .ipynb extension
        
        tags = smart_tag_detection(content, imports, file_path.name)
        title = extract_notebook_title(file_path)
        
        if tags:  # Only include if we found tags
            notebook_tags[relative_path] = {
                'title': title,
                'tags': tags,
                'full_path': str(file_path),
                'folder': str(file_path.parent.relative_to(root_dir)) if file_path.parent != Path(root_dir) else 'root',
                'imports': imports[:5]  # Keep first 5 imports for reference
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

if __name__ == '__main__':
    ROOT_DIR = 'notebooks'  # Change this to your notebooks directory
    
    # Clean up existing gallery files first
    gallery_files = ['notebooks/gallery.md', 'notebooks/gallery-sentinel.md', 'notebooks/gallery-topics.md', 'notebooks/gallery-tools.md']
    for file_path in gallery_files:
        if Path(file_path).exists():
            Path(file_path).unlink()
            print(f"🗑️  Removed old {file_path}")
    
    print("🧠 Smart content analysis starting...")
    notebook_tags = generate_auto_tags(ROOT_DIR)
    
    if notebook_tags:
        analyze_notebook_content(notebook_tags)
        
        print(f"\n📋 Tagged notebooks:")
        for path, meta in sorted(notebook_tags.items()):
            print(f"  📓 {path}")
            print(f"     📂 {meta['folder']}")
            print(f"     🏷️  {', '.join(meta['tags'])}")
            if meta['imports']:
                print(f"     📦 Imports: {', '.join(meta['imports'][:3])}")
            print()
        
        # Generate gallery pages
        print("\n📝 Generating gallery pages...")
        generate_gallery_pages(notebook_tags, ROOT_DIR)
        
        # Generate TOC entries
        generate_toc_entries(notebook_tags)
        
        print("✅ Done! Gallery generation complete.")
        print(f"✅ Generated gallery files:")
        print(f"  - {ROOT_DIR}/gallery.md (main gallery)")
        print(f"  - {ROOT_DIR}/gallery-sentinel.md")
        print(f"  - {ROOT_DIR}/gallery-topics.md") 
        print(f"  - {ROOT_DIR}/gallery-tools.md")
    else:
        print("❌ No notebooks found with detectable content. Check your notebook directory.")
