#!/usr/bin/env bash
set -euo pipefail

site_dir="_site_source"
rm -rf "$site_dir"
mkdir -p "$site_dir"

cat > "$site_dir/_config.yml" <<'EOF'
title: Indiana Bird Tracker
description: User guide for the local-first Indiana Bird Tracker.
markdown: kramdown
kramdown:
  input: GFM
EOF

mkdir -p "$site_dir/_layouts"
cat > "$site_dir/_layouts/default.html" <<'EOF'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ page.title }} | {{ site.title }}</title>
    <style>
      body { font: 17px/1.6 system-ui, sans-serif; color: #18251d; margin: 0; background: #f7faf7; }
      main { max-width: 880px; margin: 0 auto; padding: 3rem 1.5rem; background: #fff; min-height: 100vh; }
      h1, h2, h3 { color: #164b32; line-height: 1.2; } a { color: #0d6b46; }
      code { background: #edf3ed; color: #183425; padding: .1rem .25rem; border-radius: .2rem; }
      pre { overflow-x: auto; padding: 1rem; background: #102218; color: #f4fff7; }
      pre code, .highlight code { background: transparent; color: inherit; padding: 0; border-radius: 0; }
      .highlight { background: #102218; color: #f4fff7; }
      img, video { max-width: 100%; height: auto; } blockquote { border-left: 4px solid #78a789; margin-left: 0; padding-left: 1rem; }
    </style>
  </head>
  <body><main>{{ content }}</main></body>
</html>
EOF

cat > "$site_dir/index.md" <<'EOF'
---
layout: default
title: User Guide
---
EOF
cat USER_GUIDE.md >> "$site_dir/index.md"

if [ -d docs/playwright/artifacts ]; then
  mkdir -p "$site_dir/docs/playwright"
  cp -R docs/playwright/artifacts "$site_dir/docs/playwright/artifacts"
fi
