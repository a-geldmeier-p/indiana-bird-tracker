#!/usr/bin/env bash
set -euo pipefail

site_dir="_site_source"
repo_name="${GITHUB_REPOSITORY:-}"
if [ -z "$repo_name" ]; then
  repo_name="$(basename "$PWD")"
fi
site_baseurl="/${repo_name##*/}"
rm -rf "$site_dir"
mkdir -p "$site_dir"

cat > "$site_dir/_config.yml" <<EOF
title: Indiana Bird Tracker
description: User guide, function documentation, and news for Indiana Bird Tracker.
baseurl: "$site_baseurl"
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
      .site-nav { display: flex; flex-wrap: wrap; gap: .5rem 1.5rem; align-items: center; max-width: 880px; margin: 0 auto; padding: 1rem 1.5rem; }
      .site-nav a { font-weight: 600; text-decoration: none; padding: .3rem .2rem; border-bottom: 3px solid transparent; }
      .site-nav a[aria-current="page"] { border-color: #0d6b46; }
      .site-nav a:focus-visible { outline: 2px solid #0d6b46; outline-offset: 3px; }
      main { max-width: 880px; margin: 0 auto; padding: 2rem 1.5rem 3rem; background: #fff; min-height: 100vh; }
      h1, h2, h3 { color: #164b32; line-height: 1.2; } a { color: #0d6b46; }
      code { background: #edf3ed; color: #183425; padding: .1rem .25rem; border-radius: .2rem; }
      pre { overflow-x: auto; padding: 1rem; background: #102218; color: #f4fff7; }
      pre code, .highlight code { background: transparent; color: inherit; padding: 0; border-radius: 0; }
      .highlight { background: #102218; color: #f4fff7; }
      table { border-collapse: collapse; max-width: 100%; }
      td, th { border-bottom: 1px solid #d8e4da; padding: .5rem; text-align: left; vertical-align: top; }
      img, video { max-width: 100%; height: auto; } blockquote { border-left: 4px solid #78a789; margin-left: 0; padding-left: 1rem; }
    </style>
  </head>
  <body>
    <nav class="site-nav" aria-label="Documentation">
      <a href="{{ '/' | relative_url }}"{% if page.section == 'guide' %} aria-current="page"{% endif %}>User Guide</a>
      <a href="{{ '/reference/' | relative_url }}"{% if page.section == 'reference' %} aria-current="page"{% endif %}>Function documentation</a>
      <a href="{{ '/news/' | relative_url }}"{% if page.section == 'news' %} aria-current="page"{% endif %}>News</a>
    </nav>
    <main>{{ content }}</main>
  </body>
</html>
EOF

cat > "$site_dir/index.md" <<'EOF'
---
layout: default
title: User Guide
section: guide
---
EOF
cat USER_GUIDE.md >> "$site_dir/index.md"

mkdir -p "$site_dir/news"
cat > "$site_dir/news/index.md" <<'EOF'
---
layout: default
title: News
section: news
---
EOF
cat NEWS.md >> "$site_dir/news/index.md"

Rscript scripts/build_reference.R "$site_dir"

if [ -d docs/playwright/artifacts ]; then
  mkdir -p "$site_dir/docs/playwright"
  cp -R docs/playwright/artifacts "$site_dir/docs/playwright/artifacts"
fi
