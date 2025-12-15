#!/usr/bin/env python3
"""
Chrome & Safari Web Platform Features Extractor
Extracts and organizes Chrome and Safari compatibility data from the BASELINE file.
"""

import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class BrowserSupport:
    """Browser support information for a feature"""
    version: str
    release_date: str
    supported: bool
    notes: Optional[str] = None

@dataclass
class WebFeature:
    """Web platform feature with Chrome and Safari support info"""
    name: str
    description: str
    availability_status: str
    availability_since: Optional[str]
    chrome_desktop: Optional[BrowserSupport]
    chrome_android: Optional[BrowserSupport]
    safari_desktop: Optional[BrowserSupport]
    safari_ios: Optional[BrowserSupport]
    category: str = ""

class ChromeSafariExtractor:
    """Extracts Chrome and Safari data from web platform features database"""
    
    def __init__(self, baseline_file: str):
        self.baseline_file = baseline_file
        self.features: List[WebFeature] = []
        
    def extract_features(self) -> List[WebFeature]:
        """Extract all features with Chrome and Safari support data"""
        print("🔍 Extracting Chrome and Safari features from BASELINE...")
        
        with open(self.baseline_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split content into feature blocks
        feature_blocks = self._split_into_features(content)
        
        for block in feature_blocks:
            feature = self._parse_feature_block(block)
            if feature and self._has_chrome_or_safari_data(feature):
                self.features.append(feature)
        
        print(f"✅ Extracted {len(self.features)} features with Chrome/Safari data")
        return self.features
    
    def _split_into_features(self, content: str) -> List[str]:
        """Split content into individual feature blocks"""
        # Features typically start with a feature name followed by availability status
        pattern = r'\n([A-Za-z<][^\n]*)\n(Widely available|Limited availability|Newly available|Discouraged)'
        matches = re.finditer(pattern, content)
        
        blocks = []
        positions = [(m.start(), m.group(1)) for m in matches]
        
        for i, (start, name) in enumerate(positions):
            if i < len(positions) - 1:
                end = positions[i + 1][0]
                block = content[start:end]
            else:
                block = content[start:]
            blocks.append(block)
        
        return blocks
    
    def _parse_feature_block(self, block: str) -> Optional[WebFeature]:
        """Parse a single feature block"""
        lines = block.strip().split('\n')
        if len(lines) < 3:
            return None
        
        # Extract feature name
        feature_name = lines[0].strip()
        if not feature_name:
            feature_name = lines[1].strip()
        
        # Extract availability status and since date
        availability_line = None
        for line in lines[:5]:
            if any(status in line for status in ['Widely available', 'Limited availability', 'Newly available', 'Discouraged']):
                availability_line = line
                break
        
        if not availability_line:
            return None
        
        availability_status = self._extract_availability_status(availability_line)
        availability_since = self._extract_availability_since(availability_line)
        
        # Extract description
        description = self._extract_description(lines)
        
        # Extract browser support data
        chrome_desktop = self._extract_browser_support(block, "Chrome")
        chrome_android = self._extract_browser_support(block, "Chrome Android")
        safari_desktop = self._extract_browser_support(block, "Safari")
        safari_ios = self._extract_browser_support(block, "Safari on iOS")
        
        # Determine category
        category = self._categorize_feature(feature_name, description)
        
        return WebFeature(
            name=feature_name,
            description=description,
            availability_status=availability_status,
            availability_since=availability_since,
            chrome_desktop=chrome_desktop,
            chrome_android=chrome_android,
            safari_desktop=safari_desktop,
            safari_ios=safari_ios,
            category=category
        )
    
    def _extract_availability_status(self, line: str) -> str:
        """Extract availability status from line"""
        statuses = ['Widely available', 'Limited availability', 'Newly available', 'Discouraged']
        for status in statuses:
            if status in line:
                return status
        return "Unknown"
    
    def _extract_availability_since(self, line: str) -> Optional[str]:
        """Extract 'since' date from availability line"""
        match = re.search(r'since (\d{4}-\d{2}-\d{2})', line)
        return match.group(1) if match else None
    
    def _extract_description(self, lines: List[str]) -> str:
        """Extract feature description"""
        description_lines = []
        in_description = False
        
        for line in lines:
            line = line.strip()
            if line == "Learn more":
                break
            if in_description:
                if line and not line.startswith(('Chrome', 'Safari', 'Edge', 'Firefox')):
                    description_lines.append(line)
            elif any(status in line for status in ['Widely available', 'Limited availability', 'Newly available', 'Discouraged']):
                in_description = True
        
        return ' '.join(description_lines).strip()
    
    def _extract_browser_support(self, block: str, browser_name: str) -> Optional[BrowserSupport]:
        """Extract browser support information"""
        lines = block.split('\n')
        
        # Find browser name line
        browser_line_idx = None
        for i, line in enumerate(lines):
            if line.strip() == browser_name:
                browser_line_idx = i
                break
        
        if browser_line_idx is None:
            return None
        
        # Get version and release info from next lines
        version = "Unknown"
        release_date = ""
        supported = True
        notes = None
        
        if browser_line_idx + 1 < len(lines):
            version_line = lines[browser_line_idx + 1].strip()
            if version_line == "❌":
                supported = False
                version = "Not supported"
            else:
                version = version_line
        
        if browser_line_idx + 2 < len(lines):
            release_line = lines[browser_line_idx + 2].strip()
            if release_line.startswith("Released on"):
                release_date = release_line.replace("Released on ", "")
            elif release_line.startswith("Vendor position"):
                notes = release_line
        
        return BrowserSupport(
            version=version,
            release_date=release_date,
            supported=supported,
            notes=notes
        )
    
    def _has_chrome_or_safari_data(self, feature: WebFeature) -> bool:
        """Check if feature has Chrome or Safari support data"""
        return any([
            feature.chrome_desktop,
            feature.chrome_android,
            feature.safari_desktop,
            feature.safari_ios
        ])
    
    def _categorize_feature(self, name: str, description: str) -> str:
        """Categorize feature by type"""
        name_lower = name.lower()
        desc_lower = description.lower()
        
        if name.startswith('<') and name.endswith('>'):
            return "HTML Elements"
        elif 'css' in desc_lower or any(css_term in name_lower for css_term in ['color', 'font', 'border', 'margin', 'padding', 'flex', 'grid']):
            return "CSS Features"
        elif any(js_term in desc_lower for js_term in ['javascript', 'api', 'method', 'object', 'function']):
            return "JavaScript APIs"
        elif any(web_term in desc_lower for web_term in ['http', 'fetch', 'request', 'response']):
            return "Web APIs"
        elif any(security_term in desc_lower for security_term in ['security', 'cors', 'csp', 'permission']):
            return "Security Features"
        else:
            return "Other"
    
    def generate_compatibility_matrix(self) -> Dict[str, Any]:
        """Generate compatibility matrix for analysis"""
        matrix = {
            "summary": {
                "total_features": len(self.features),
                "by_category": {},
                "by_availability": {},
                "chrome_vs_safari": {
                    "chrome_only": 0,
                    "safari_only": 0,
                    "both_supported": 0,
                    "neither_supported": 0
                }
            },
            "features": []
        }
        
        for feature in self.features:
            # Category count
            if feature.category not in matrix["summary"]["by_category"]:
                matrix["summary"]["by_category"][feature.category] = 0
            matrix["summary"]["by_category"][feature.category] += 1
            
            # Availability count
            if feature.availability_status not in matrix["summary"]["by_availability"]:
                matrix["summary"]["by_availability"][feature.availability_status] = 0
            matrix["summary"]["by_availability"][feature.availability_status] += 1
            
            # Chrome vs Safari comparison
            chrome_supported = any([
                feature.chrome_desktop and feature.chrome_desktop.supported,
                feature.chrome_android and feature.chrome_android.supported
            ])
            safari_supported = any([
                feature.safari_desktop and feature.safari_desktop.supported,
                feature.safari_ios and feature.safari_ios.supported
            ])
            
            if chrome_supported and safari_supported:
                matrix["summary"]["chrome_vs_safari"]["both_supported"] += 1
            elif chrome_supported and not safari_supported:
                matrix["summary"]["chrome_vs_safari"]["chrome_only"] += 1
            elif not chrome_supported and safari_supported:
                matrix["summary"]["chrome_vs_safari"]["safari_only"] += 1
            else:
                matrix["summary"]["chrome_vs_safari"]["neither_supported"] += 1
            
            # Add feature to matrix
            matrix["features"].append(asdict(feature))
        
        return matrix
    
    def save_results(self, output_file: str = "chrome_safari_compatibility.json"):
        """Save extracted data to JSON file"""
        matrix = self.generate_compatibility_matrix()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(matrix, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to {output_file}")
        return matrix

def main():
    """Main execution function"""
    print("🚀 Chrome & Safari Web Platform Features Extractor")
    print("=" * 50)
    
    extractor = ChromeSafariExtractor("BASELINE")
    
    # Extract features
    features = extractor.extract_features()
    
    # Generate and save results
    matrix = extractor.save_results()
    
    # Print summary
    print("\n📊 EXTRACTION SUMMARY")
    print("=" * 50)
    print(f"Total Features: {matrix['summary']['total_features']}")
    print(f"Categories: {len(matrix['summary']['by_category'])}")
    print(f"Both Chrome & Safari: {matrix['summary']['chrome_vs_safari']['both_supported']}")
    print(f"Chrome Only: {matrix['summary']['chrome_vs_safari']['chrome_only']}")
    print(f"Safari Only: {matrix['summary']['chrome_vs_safari']['safari_only']}")
    print("\n✅ Extraction complete! Check chrome_safari_compatibility.json for full results.")

if __name__ == "__main__":
    main() 