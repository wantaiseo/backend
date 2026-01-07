"""
Platform Detection Module

Detects what platform/CMS a website is built on by analyzing:
- HTTP headers
- HTML meta tags
- JavaScript libraries
- URL patterns
- Known file paths
"""

import re
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class PlatformInfo:
    """Detected platform information"""
    platform: str  # Platform identifier (e.g., 'wordpress', 'shopify')
    platform_name: str  # Human-readable name
    confidence: float  # 0.0 to 1.0
    version: Optional[str] = None
    hosting: Optional[str] = None  # Detected hosting provider
    details: Dict[str, Any] = None


# Platform detection signatures
PLATFORM_SIGNATURES = {
    'wordpress': {
        'name': 'WordPress',
        'meta_generators': [r'WordPress'],
        'html_patterns': [
            r'wp-content/',
            r'wp-includes/',
            r'wp-json',
            r'/xmlrpc\.php',
        ],
        'headers': {
            'x-powered-by': r'WordPress',
            'link': r'<https://[^>]+/wp-json/',
        },
        'scripts': [r'wp-embed\.min\.js', r'jquery-migrate'],
    },
    'woocommerce': {
        'name': 'WooCommerce',
        'html_patterns': [
            r'woocommerce',
            r'wc-ajax',
            r'add_to_cart',
            r'woocommerce-js',
        ],
        'scripts': [r'woocommerce', r'wc-cart'],
        'parent': 'wordpress',  # WooCommerce runs on WordPress
    },
    'shopify': {
        'name': 'Shopify',
        'meta_generators': [r'Shopify'],
        'html_patterns': [
            r'cdn\.shopify\.com',
            r'shopify-section',
            r'Shopify\.theme',
            r'/collections/',
            r'/products/',
        ],
        'headers': {
            'x-shopify-stage': r'.*',
            'x-sorting-hat-shopid': r'.*',
        },
        'scripts': [r'cdn\.shopify\.com'],
    },
    'wix': {
        'name': 'Wix',
        'meta_generators': [r'Wix\.com'],
        'html_patterns': [
            r'static\.wixstatic\.com',
            r'wix-code-sdk',
            r'_wix_browser_sess',
            r'wixsite\.com',
        ],
        'headers': {
            'x-wix-request-id': r'.*',
        },
        'scripts': [r'static\.parastorage\.com', r'wix-code'],
    },
    'squarespace': {
        'name': 'Squarespace',
        'meta_generators': [r'Squarespace'],
        'html_patterns': [
            r'squarespace\.com',
            r'squarespace-cdn\.com',
            r'sqs-cart',
        ],
        'headers': {
            'x-servedby': r'squarespace',
        },
    },
    'webflow': {
        'name': 'Webflow',
        'meta_generators': [r'Webflow'],
        'html_patterns': [
            r'webflow\.com',
            r'assets\.website-files\.com',
            r'w-nav',
            r'w-slider',
        ],
    },
    'ghost': {
        'name': 'Ghost',
        'meta_generators': [r'Ghost'],
        'html_patterns': [
            r'ghost/',
            r'@tryghost',
        ],
        'headers': {
            'x-ghost-cache-status': r'.*',
        },
    },
    'drupal': {
        'name': 'Drupal',
        'meta_generators': [r'Drupal'],
        'html_patterns': [
            r'Drupal\.settings',
            r'drupal\.js',
            r'/sites/default/',
        ],
        'headers': {
            'x-drupal-cache': r'.*',
            'x-generator': r'Drupal',
        },
    },
    'joomla': {
        'name': 'Joomla',
        'meta_generators': [r'Joomla'],
        'html_patterns': [
            r'/media/jui/',
            r'/media/system/',
            r'Joomla!',
        ],
    },
    'magento': {
        'name': 'Magento',
        'html_patterns': [
            r'Magento',
            r'mage/cookies',
            r'/skin/frontend/',
            r'Mage\.Cookies',
        ],
        'headers': {
            'x-magento-vary': r'.*',
        },
    },
    'bigcommerce': {
        'name': 'BigCommerce',
        'html_patterns': [
            r'cdn\.bcapp',
            r'bigcommerce\.com',
            r'/stencil/',
        ],
        'headers': {
            'x-bc-': r'.*',
        },
    },
    'nextjs': {
        'name': 'Next.js',
        'html_patterns': [
            r'__NEXT_DATA__',
            r'/_next/',
            r'next/dist',
        ],
        'headers': {
            'x-nextjs-cache': r'.*',
            'x-powered-by': r'Next\.js',
        },
    },
    'gatsby': {
        'name': 'Gatsby',
        'html_patterns': [
            r'gatsby',
            r'___gatsby',
            r'/page-data/',
        ],
    },
    'nuxt': {
        'name': 'Nuxt.js',
        'html_patterns': [
            r'__NUXT__',
            r'/_nuxt/',
        ],
    },
}

# Hosting provider detection
HOSTING_SIGNATURES = {
    'vercel': {
        'name': 'Vercel',
        'headers': {
            'x-vercel-id': r'.*',
            'server': r'Vercel',
        },
        'cname': [r'\.vercel\.app', r'\.now\.sh'],
    },
    'netlify': {
        'name': 'Netlify',
        'headers': {
            'x-nf-request-id': r'.*',
            'server': r'Netlify',
        },
        'cname': [r'\.netlify\.app', r'\.netlify\.com'],
    },
    'aws': {
        'name': 'AWS',
        'headers': {
            'x-amz-': r'.*',
            'x-amz-cf-id': r'.*',
            'server': r'AmazonS3',
        },
        'cname': [r'\.amazonaws\.com', r'\.cloudfront\.net', r'\.s3\.'],
    },
    'cloudflare': {
        'name': 'Cloudflare',
        'headers': {
            'cf-ray': r'.*',
            'server': r'cloudflare',
        },
    },
    'github_pages': {
        'name': 'GitHub Pages',
        'headers': {
            'server': r'GitHub\.com',
        },
        'cname': [r'\.github\.io'],
    },
    'heroku': {
        'name': 'Heroku',
        'headers': {
            'via': r'heroku',
        },
        'cname': [r'\.herokuapp\.com'],
    },
    'digitalocean': {
        'name': 'DigitalOcean',
        'headers': {
            'server': r'nginx',  # Often uses nginx
        },
        'cname': [r'\.ondigitalocean\.app'],
    },
    'cpanel': {
        'name': 'cPanel',
        'headers': {
            'server': r'cpsrvd',
            'x-powered-by': r'cpanel',
        },
        'html_patterns': [r'/cgi-sys/', r'cpanel'],
    },
    'plesk': {
        'name': 'Plesk',
        'headers': {
            'x-powered-by': r'plesk',
        },
    },
    'wpengine': {
        'name': 'WP Engine',
        'headers': {
            'x-powered-by': r'WP Engine',
            'x-wpe-': r'.*',
        },
        'cname': [r'\.wpengine\.com', r'\.wpenginepowered\.com'],
    },
    'bluehost': {
        'name': 'Bluehost',
        'cname': [r'\.bluehost\.com'],
    },
    'godaddy': {
        'name': 'GoDaddy',
        'cname': [r'\.godaddysites\.com', r'\.secureserver\.net'],
    },
}


class PlatformDetector:
    """Detects website platform and hosting provider"""
    
    def __init__(self, html: str = "", headers: Dict[str, str] = None, url: str = ""):
        self.html = html.lower() if html else ""
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.url = url.lower()
        self.detected_platforms = []
        self.detected_hosting = []
    
    def detect(self) -> PlatformInfo:
        """Run all detection methods and return best match"""
        # Detect platforms
        for platform_id, signatures in PLATFORM_SIGNATURES.items():
            confidence = self._check_signatures(signatures)
            if confidence > 0.2:  # Threshold
                self.detected_platforms.append({
                    'id': platform_id,
                    'name': signatures['name'],
                    'confidence': confidence,
                    'parent': signatures.get('parent'),
                })
        
        # Detect hosting
        for hosting_id, signatures in HOSTING_SIGNATURES.items():
            confidence = self._check_hosting_signatures(signatures)
            if confidence > 0.3:
                self.detected_hosting.append({
                    'id': hosting_id,
                    'name': signatures['name'],
                    'confidence': confidence,
                })
        
        # Sort by confidence
        self.detected_platforms.sort(key=lambda x: x['confidence'], reverse=True)
        self.detected_hosting.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Build result
        primary_platform = self.detected_platforms[0] if self.detected_platforms else None
        primary_hosting = self.detected_hosting[0] if self.detected_hosting else None
        
        if primary_platform:
            return PlatformInfo(
                platform=primary_platform['id'],
                platform_name=primary_platform['name'],
                confidence=primary_platform['confidence'],
                hosting=primary_hosting['name'] if primary_hosting else None,
                details={
                    'all_platforms': [p['id'] for p in self.detected_platforms],
                    'all_hosting': [h['id'] for h in self.detected_hosting],
                }
            )
        else:
            return PlatformInfo(
                platform='custom',
                platform_name='Custom/Static',
                confidence=0.5,
                hosting=primary_hosting['name'] if primary_hosting else None,
                details={
                    'all_hosting': [h['id'] for h in self.detected_hosting],
                }
            )
    
    def _check_signatures(self, signatures: Dict) -> float:
        """Check platform signatures and return confidence score"""
        matches = 0
        total_checks = 0
        
        # Check meta generator
        if 'meta_generators' in signatures:
            total_checks += 1
            for pattern in signatures['meta_generators']:
                if re.search(f'<meta[^>]+generator[^>]+{pattern}', self.html, re.I):
                    matches += 1
                    break
        
        # Check HTML patterns
        if 'html_patterns' in signatures:
            pattern_matches = 0
            for pattern in signatures['html_patterns']:
                if re.search(pattern, self.html, re.I):
                    pattern_matches += 1
            if pattern_matches > 0:
                matches += min(pattern_matches / len(signatures['html_patterns']), 1.0)
            total_checks += 1
        
        # Check headers
        if 'headers' in signatures:
            header_matches = 0
            for header_name, pattern in signatures['headers'].items():
                if header_name in self.headers:
                    if re.search(pattern, self.headers[header_name], re.I):
                        header_matches += 1
            if header_matches > 0:
                matches += min(header_matches / len(signatures['headers']), 1.0)
            total_checks += 1
        
        # Check scripts
        if 'scripts' in signatures:
            script_matches = 0
            for pattern in signatures['scripts']:
                if re.search(f'<script[^>]+{pattern}', self.html, re.I):
                    script_matches += 1
            if script_matches > 0:
                matches += min(script_matches / len(signatures['scripts']), 1.0)
            total_checks += 1
        
        if total_checks == 0:
            return 0.0
        
        return matches / total_checks
    
    def _check_hosting_signatures(self, signatures: Dict) -> float:
        """Check hosting provider signatures"""
        matches = 0
        total_checks = 0
        
        # Check headers
        if 'headers' in signatures:
            for header_name, pattern in signatures['headers'].items():
                total_checks += 1
                if header_name in self.headers:
                    if re.search(pattern, self.headers[header_name], re.I):
                        matches += 1
        
        # Check CNAME patterns in URL
        if 'cname' in signatures:
            total_checks += 1
            for pattern in signatures['cname']:
                if re.search(pattern, self.url, re.I):
                    matches += 1
                    break
        
        # Check HTML patterns
        if 'html_patterns' in signatures:
            for pattern in signatures['html_patterns']:
                total_checks += 1
                if re.search(pattern, self.html, re.I):
                    matches += 1
        
        if total_checks == 0:
            return 0.0
        
        return matches / total_checks


def detect_platform(html: str, headers: Dict[str, str] = None, url: str = "") -> PlatformInfo:
    """
    Convenience function to detect platform from HTML content.
    
    Args:
        html: The HTML content of the page
        headers: HTTP response headers (optional)
        url: The URL of the website (optional)
    
    Returns:
        PlatformInfo with detected platform and hosting details
    """
    detector = PlatformDetector(html=html, headers=headers, url=url)
    return detector.detect()


# Platform-specific deployment guides
DEPLOYMENT_GUIDES = {
    'wordpress': 'wordpress',
    'woocommerce': 'wordpress',  # Same as WordPress
    'shopify': 'shopify',
    'wix': 'wix',
    'squarespace': 'squarespace',
    'webflow': 'webflow',
    'ghost': 'ghost',
    'drupal': 'drupal',
    'joomla': 'joomla',
    'magento': 'magento',
    'bigcommerce': 'bigcommerce',
    'nextjs': 'vercel',  # Next.js typically deploys to Vercel
    'gatsby': 'netlify',  # Gatsby often deploys to Netlify
    'nuxt': 'vercel',
    'custom': 'cpanel',  # Default fallback
}


def get_deployment_guide_id(platform_info: PlatformInfo) -> str:
    """
    Get the deployment guide ID for a detected platform.
    
    Returns a guide identifier that can be used to select the right
    deployment instructions in the generated package.
    """
    # First check hosting (more specific)
    if platform_info.hosting:
        hosting_lower = platform_info.hosting.lower().replace(' ', '_')
        if hosting_lower in ['vercel', 'netlify', 'aws', 'github_pages', 'heroku', 'cpanel']:
            return hosting_lower
    
    # Then check platform
    return DEPLOYMENT_GUIDES.get(platform_info.platform, 'cpanel')
