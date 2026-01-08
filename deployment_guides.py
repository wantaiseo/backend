"""
Platform-Specific Deployment Guides

Contains step-by-step HTML instructions for each platform.
These are injected into guide.html during package generation.
"""

PLATFORM_GUIDES = {
    "wordpress": {
        "name": "WordPress",
        "icon": "WP",
        "color": "#21759b",
        "letter": "WP",
        "steps": """
            <!-- WordPress Instructions -->
            <div class="platform-content active" data-platform-content="wordpress">
                <div class="step-card" data-step="wp-1">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">1</div>
                        <div class="step-info">
                            <div class="step-title">Upload robots.txt</div>
                            <div class="step-desc">Allow AI crawlers to access your site</div>
                        </div>
                        <span class="step-badge critical">Critical</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Access your WordPress site via <strong>FTP</strong> or <strong>File Manager</strong> in your hosting panel (cPanel, Plesk, etc.)</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Navigate to the <strong>root directory</strong> (where wp-config.php is located)</p>
                                    <div class="file-path">📁 public_html/ or /var/www/html/</div>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Upload the <span class="file-path">robots.txt</span> file from this package</p>
                                    <p>⚠️ If a robots.txt already exists, <strong>merge the contents</strong> - don't replace entirely!</p>
                                </div>
                            </li>
                        </ol>
                        <div class="tip-box">
                            <strong>💡 Pro Tip:</strong> Use the Yoast SEO plugin? Go to SEO → Tools → File Editor to edit robots.txt directly from WordPress admin.
                        </div>
                    </div>
                </div>

                <div class="step-card" data-step="wp-2">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">2</div>
                        <div class="step-info">
                            <div class="step-title">Upload llms.txt</div>
                            <div class="step-desc">Give AI a summary of your website</div>
                        </div>
                        <span class="step-badge critical">Critical</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>In the same <strong>root directory</strong>, upload <span class="file-path">llms.txt</span></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Verify it's accessible at: <code>https://yourdomain.com/llms.txt</code></p>
                                </div>
                            </li>
                        </ol>
                        <div class="tip-box">
                            <strong>💡 Why this matters:</strong> This is the "robots.txt for AI" - it tells ChatGPT, Claude, and Gemini who you are and what you do.
                        </div>
                    </div>
                </div>

                <div class="step-card" data-step="wp-3">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">3</div>
                        <div class="step-info">
                            <div class="step-title">Add Schema.org Markup</div>
                            <div class="step-desc">Help AI understand your business structure</div>
                        </div>
                        <span class="step-badge important">Important</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Open <span class="file-path">schemas/organization-schema.html</span> from this package</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Copy the entire <code>&lt;script type="application/ld+json"&gt;</code> block</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>In WordPress admin, go to <strong>Appearance → Theme Editor</strong> (or use a plugin like "Insert Headers and Footers")</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Paste the code into your theme's <code>header.php</code> just before the closing <code>&lt;/head&gt;</code> tag</p>
                                </div>
                            </li>
                        </ol>
                        <div class="warning-box">
                            <strong>⚠️ Using a page builder?</strong> Use a plugin like "WPCode" or "Code Snippets" to add the schema without editing theme files.
                        </div>
                    </div>
                </div>

                <div class="step-card" data-step="wp-4">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">4</div>
                        <div class="step-info">
                            <div class="step-title">Upload Remaining Files</div>
                            <div class="step-desc">Deploy mcp.json and sitemap</div>
                        </div>
                        <span class="step-badge optional">Optional</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Upload <span class="file-path">mcp.json</span> to your root directory</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>If you want to use the enhanced sitemap, rename your existing sitemap and upload <span class="file-path">sitemap.xml</span></p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>

                <div class="step-card" data-step="wp-5">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">5</div>
                        <div class="step-info">
                            <div class="step-title">Clear Cache</div>
                            <div class="step-desc">Ensure changes are visible</div>
                        </div>
                        <span class="step-badge important">Important</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>If using a caching plugin (WP Rocket, W3 Total Cache, etc.), <strong>purge all caches</strong></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>If using Cloudflare or another CDN, purge the CDN cache as well</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Test by visiting your URLs in an incognito/private browser window</p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>
            </div>
        """
    },
    
    "shopify": {
        "name": "Shopify",
        "icon": "S",
        "color": "#96bf48",
        "letter": "S",
        "steps": """
            <!-- Shopify Instructions -->
            <div class="platform-content" data-platform-content="shopify">
                <div class="step-card" data-step="shop-1">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">1</div>
                        <div class="step-info">
                            <div class="step-title">Edit robots.txt.liquid</div>
                            <div class="step-desc">Add AI crawler permissions</div>
                        </div>
                        <span class="step-badge critical">Critical</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Go to <strong>Online Store → Themes</strong> in your Shopify admin</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Click <strong>Actions → Edit code</strong></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Find <span class="file-path">robots.txt.liquid</span> in the Templates folder</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Add the AI crawler rules from our robots.txt to the file</p>
                                </div>
                            </li>
                        </ol>
                        <div class="warning-box">
                            <strong>⚠️ Important:</strong> Shopify uses a liquid template for robots.txt. Add our rules but keep Shopify's default rules intact.
                        </div>
                    </div>
                </div>

                <div class="step-card" data-step="shop-2">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">2</div>
                        <div class="step-info">
                            <div class="step-title">Upload llms.txt via Files + URL Redirect</div>
                            <div class="step-desc">The proper way to serve llms.txt on Shopify</div>
                        </div>
                        <span class="step-badge critical">Critical</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Go to <strong>Content → Files</strong> in your Shopify admin</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Click <strong>Upload files</strong> and select <span class="file-path">llms.txt</span></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>After upload, click on the file and <strong>copy the CDN URL</strong></p>
                                    <div class="code-box">https://cdn.shopify.com/s/files/.../llms.txt</div>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Go to <strong>Online Store → Navigation → URL Redirects</strong></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Click <strong>Create URL redirect</strong></p>
                                    <p>• Redirect from: <code>/llms.txt</code></p>
                                    <p>• Redirect to: <em>(paste your CDN URL)</em></p>
                                </div>
                            </li>
                        </ol>
                        <div class="tip-box">
                            <strong>💡 How it works:</strong> Now yourstore.com/llms.txt will redirect to your file on Shopify's CDN!
                        </div>
                    </div>
                </div>

                <div class="step-card" data-step="shop-3">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">3</div>
                        <div class="step-info">
                            <div class="step-title">Add Schema.org Markup</div>
                            <div class="step-desc">Enhance your product and organization data</div>
                        </div>
                        <span class="step-badge important">Important</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>In Theme Editor, open <span class="file-path">theme.liquid</span></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Paste the schema code just before <code>&lt;/head&gt;</code></p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>
            </div>
        """
    },
    
    "wix": {
        "name": "Wix",
        "icon": "W",
        "color": "#0C6EFC",
        "letter": "W",
        "steps": """
            <!-- Wix Instructions -->
            <div class="platform-content" data-platform-content="wix">
                <div class="step-card" data-step="wix-1">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">1</div>
                        <div class="step-info">
                            <div class="step-title">Edit robots.txt</div>
                            <div class="step-desc">Configure in Wix SEO settings</div>
                        </div>
                        <span class="step-badge critical">Critical</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Go to <strong>Site Dashboard → Marketing & SEO → SEO Tools</strong></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Click <strong>robots.txt Editor</strong></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Add the AI crawler rules from our robots.txt file</p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>

                <div class="step-card" data-step="wix-2">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">2</div>
                        <div class="step-info">
                            <div class="step-title">Add Custom Code (Schema)</div>
                            <div class="step-desc">Add structured data via tracking codes</div>
                        </div>
                        <span class="step-badge important">Important</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Go to <strong>Settings → Custom Code</strong> (or Marketing & SEO → SEO Tools → Custom Code)</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Click <strong>+ Add Custom Code</strong></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Paste your Schema.org JSON-LD code</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Set to load in <strong>Head</strong> on <strong>All Pages</strong></p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>

                <div class="step-card" data-step="wix-3">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">3</div>
                        <div class="step-info">
                            <div class="step-title">Create llms.txt page</div>
                            <div class="step-desc">Wix doesn't allow root file uploads</div>
                        </div>
                        <span class="step-badge important">Important</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Create a new page and set its URL to <code>/llms-txt</code></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Add the contents of llms.txt as text content</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Use a URL redirect to point <code>/llms.txt</code> to this page</p>
                                </div>
                            </li>
                        </ol>
                        <div class="warning-box">
                            <strong>⚠️ Limitation:</strong> Wix doesn't support serving files at root URLs. The redirect method is the best workaround.
                        </div>
                    </div>
                </div>
            </div>
        """
    },
    
    "vercel": {
        "name": "Vercel",
        "icon": "V",
        "color": "#000000",
        "letter": "V",
        "steps": """
            <!-- Vercel Instructions -->
            <div class="platform-content" data-platform-content="vercel">
                <div class="step-card" data-step="vercel-1">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">1</div>
                        <div class="step-info">
                            <div class="step-title">Add files to /public</div>
                            <div class="step-desc">Static files are served from public folder</div>
                        </div>
                        <span class="step-badge critical">Critical</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Copy these files to your project's <span class="file-path">/public</span> folder:</p>
                                    <div class="code-box">public/
├── robots.txt
├── llms.txt
├── mcp.json
└── sitemap.xml</div>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Commit and push to trigger a new deployment</p>
                                    <div class="code-box">git add public/
git commit -m "Add AI visibility files"
git push</div>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>

                <div class="step-card" data-step="vercel-2">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">2</div>
                        <div class="step-info">
                            <div class="step-title">Add Schema to _document or layout</div>
                            <div class="step-desc">Next.js specific implementation</div>
                        </div>
                        <span class="step-badge important">Important</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p><strong>For Next.js App Router:</strong> Add to <span class="file-path">app/layout.tsx</span></p>
                                    <div class="code-box">&lt;script
  type="application/ld+json"
  dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaData) }}
/&gt;</div>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p><strong>For Next.js Pages Router:</strong> Add to <span class="file-path">pages/_document.tsx</span></p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>

                <div class="step-card" data-step="vercel-3">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">3</div>
                        <div class="step-info">
                            <div class="step-title">Verify Deployment</div>
                            <div class="step-desc">Check files are accessible</div>
                        </div>
                        <span class="step-badge optional">Optional</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>After deployment, verify at:</p>
                                    <div class="code-box">https://your-domain.com/robots.txt
https://your-domain.com/llms.txt
https://your-domain.com/mcp.json</div>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>
            </div>
        """
    },
    
    "netlify": {
        "name": "Netlify",
        "icon": "N",
        "color": "#00C7B7",
        "letter": "N",
        "steps": """
            <!-- Netlify Instructions -->
            <div class="platform-content" data-platform-content="netlify">
                <div class="step-card" data-step="netlify-1">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">1</div>
                        <div class="step-info">
                            <div class="step-title">Add files to /public or /static</div>
                            <div class="step-desc">Depends on your framework</div>
                        </div>
                        <span class="step-badge critical">Critical</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Copy files to your static folder (usually <span class="file-path">/public</span> or <span class="file-path">/static</span>)</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Commit and push to trigger a new deployment</p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>
            </div>
        """
    },
    
    "cpanel": {
        "name": "cPanel / Traditional Hosting",
        "icon": "CP",
        "color": "#FF6C2C",
        "letter": "CP",
        "steps": """
            <!-- cPanel Instructions -->
            <div class="platform-content" data-platform-content="cpanel">
                <div class="step-card" data-step="cp-1">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">1</div>
                        <div class="step-info">
                            <div class="step-title">Access File Manager</div>
                            <div class="step-desc">Upload files via cPanel</div>
                        </div>
                        <span class="step-badge critical">Critical</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Log in to your <strong>cPanel</strong> or hosting control panel</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Open <strong>File Manager</strong></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Navigate to <span class="file-path">public_html</span> (your website root)</p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>

                <div class="step-card" data-step="cp-2">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">2</div>
                        <div class="step-info">
                            <div class="step-title">Upload All Files</div>
                            <div class="step-desc">robots.txt, llms.txt, mcp.json, sitemap.xml</div>
                        </div>
                        <span class="step-badge critical">Critical</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Click <strong>Upload</strong> in the File Manager toolbar</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Select and upload:</p>
                                    <ul style="margin-left: 20px; margin-top: 8px;">
                                        <li>robots.txt</li>
                                        <li>llms.txt</li>
                                        <li>mcp.json</li>
                                        <li>sitemap.xml</li>
                                    </ul>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Upload the <span class="file-path">schemas/</span> folder for HTML snippets</p>
                                </div>
                            </li>
                        </ol>
                        <div class="tip-box">
                            <strong>💡 Alternative:</strong> You can also use FTP (FileZilla) to upload files if File Manager is slow.
                        </div>
                    </div>
                </div>

                <div class="step-card" data-step="cp-3">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">3</div>
                        <div class="step-info">
                            <div class="step-title">Add Schema to HTML</div>
                            <div class="step-desc">Edit your homepage file</div>
                        </div>
                        <span class="step-badge important">Important</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Find your homepage file (usually <span class="file-path">index.html</span> or <span class="file-path">index.php</span>)</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Open it for editing</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Copy the schema code from <span class="file-path">schemas/organization-schema.html</span></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Paste it just before the <code>&lt;/head&gt;</code> tag</p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>

                <div class="step-card" data-step="cp-4">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">4</div>
                        <div class="step-info">
                            <div class="step-title">Clear Cache (if applicable)</div>
                            <div class="step-desc">Ensure changes are live</div>
                        </div>
                        <span class="step-badge optional">Optional</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>If using Cloudflare or a CDN, purge the cache</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Test your URLs in an incognito browser window</p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>
            </div>
        """
    },
    
    "squarespace": {
        "name": "Squarespace",
        "icon": "◼",
        "color": "#000000",
        "letter": "SQ",
        "steps": """
            <!-- Squarespace Instructions -->
            <div class="platform-content" data-platform-content="squarespace">
                <div class="step-card" data-step="sq-1">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">1</div>
                        <div class="step-info">
                            <div class="step-title">Add Schema via Code Injection (Sitewide)</div>
                            <div class="step-desc">Add structured data to all pages</div>
                        </div>
                        <span class="step-badge critical">Critical</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Go to <strong>Settings → Website Tools → Code Injection</strong></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>In the <strong>Header</strong> field, paste the Organization Schema from <span class="file-path">schemas/organization-schema.html</span></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Click <strong>Save</strong></p>
                                </div>
                            </li>
                        </ol>
                        <div class="tip-box">
                            <strong>💡 Tip:</strong> This adds Schema.org structured data to ALL pages automatically.
                        </div>
                    </div>
                </div>

                <div class="step-card" data-step="sq-2">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">2</div>
                        <div class="step-info">
                            <div class="step-title">Create /llms Content Page</div>
                            <div class="step-desc">Squarespace doesn't allow root file uploads</div>
                        </div>
                        <span class="step-badge important">Important</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Go to <strong>Pages → + → Blank Page</strong></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Name it "llms" (URL becomes /llms)</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Add a <strong>Code Block</strong> and paste the content from <span class="file-path">llms.txt</span></p>
                                </div>
                            </li>
                        </ol>
                        <div class="warning-box">
                            <strong>⚠️ Limitation:</strong> Squarespace doesn't support serving files at root URLs like /llms.txt. The /llms page is the best workaround.
                        </div>
                    </div>
                </div>

                <div class="step-card" data-step="sq-3">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">3</div>
                        <div class="step-info">
                            <div class="step-title">Verify Installation</div>
                            <div class="step-desc">Check your Schema is working</div>
                        </div>
                        <span class="step-badge optional">Optional</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>View your page source and search for "application/ld+json"</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Use <a href="https://validator.schema.org/" target="_blank">Google Rich Results Test</a> on your homepage</p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>
            </div>
        """
    },

    "webflow": {
        "name": "Webflow",
        "icon": "W",
        "color": "#4353FF",
        "letter": "WF",
        "steps": """
            <!-- Webflow Instructions -->
            <div class="platform-content" data-platform-content="webflow">
                <div class="step-card" data-step="wf-1">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">1</div>
                        <div class="step-info">
                            <div class="step-title">Upload llms.txt (Native Support!)</div>
                            <div class="step-desc">Webflow has built-in llms.txt support</div>
                        </div>
                        <span class="step-badge critical">Critical</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Go to <strong>Site Settings → SEO</strong> tab</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Scroll to <strong>LLMs.txt</strong> section</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Click <strong>Upload file</strong> and select <span class="file-path">llms.txt</span> from this package</p>
                                </div>
                            </li>
                        </ol>
                        <div class="tip-box">
                            <strong>💡 Great News:</strong> Webflow natively supports llms.txt - it will automatically be served at yoursite.com/llms.txt!
                        </div>
                    </div>
                </div>

                <div class="step-card" data-step="wf-2">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">2</div>
                        <div class="step-info">
                            <div class="step-title">Customize robots.txt</div>
                            <div class="step-desc">Add AI crawler permissions</div>
                        </div>
                        <span class="step-badge important">Important</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>In Site Settings → <strong>SEO → Indexing</strong></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Find the custom robots.txt field</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Add the AI crawler rules from our <span class="file-path">robots.txt</span> file</p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>

                <div class="step-card" data-step="wf-3">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">3</div>
                        <div class="step-info">
                            <div class="step-title">Add Schema via Custom Code</div>
                            <div class="step-desc">Structured data for AI understanding</div>
                        </div>
                        <span class="step-badge important">Important</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Go to <strong>Project Settings → Custom Code</strong></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>In <strong>Head Code</strong>, paste the schema from <span class="file-path">schemas/organization-schema.html</span></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Click <strong>Save Changes</strong> then <strong>Publish</strong></p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>
            </div>
        """
    },

    "custom": {
        "name": "Custom / Static Site",
        "icon": "?",
        "color": "#6B7280",
        "letter": "?",
        "steps": """
            <!-- Custom Site Instructions -->
            <div class="platform-content" data-platform-content="custom">
                <div class="step-card" data-step="custom-1">
                    <div class="step-header">
                        <div class="step-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="step-num">1</div>
                        <div class="step-info">
                            <div class="step-title">Upload files to root directory</div>
                            <div class="step-desc">Place files where your site is hosted</div>
                        </div>
                        <span class="step-badge critical">Critical</span>
                    </div>
                    <div class="step-content">
                        <ol class="instructions">
                            <li>
                                <div class="instruction-content">
                                    <p>Access your web server via FTP, SSH, or your hosting panel</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Navigate to your website's root directory</p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Upload these files: <span class="file-path">llms.txt</span>, <span class="file-path">robots.txt</span>, <span class="file-path">sitemap.xml</span>, <span class="file-path">mcp.json</span></p>
                                </div>
                            </li>
                            <li>
                                <div class="instruction-content">
                                    <p>Add Schema from <span class="file-path">schemas/</span> folder to your HTML &lt;head&gt;</p>
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>
            </div>
        """
    }
}


def get_platform_guide(platform_id: str) -> dict:
    """
    Get the deployment guide for a specific platform.
    Returns the guide dict or the default (cpanel) if not found.
    """
    return PLATFORM_GUIDES.get(platform_id, PLATFORM_GUIDES["cpanel"])


def get_all_platform_instructions() -> str:
    """
    Get all platform instructions HTML concatenated.
    Used to include all tabs in the guide.html.
    """
    instructions = []
    for platform_id, guide in PLATFORM_GUIDES.items():
        instructions.append(guide["steps"])
    return "\n".join(instructions)
