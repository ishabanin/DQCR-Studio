# Icons System

## Overview
Scalable icon system with fallback to emoji. Icons are loaded from SVG files, with automatic fallback to emoji if the file is not found.

## Icon Types
| Type | Description | Default Emoji | SVG File |
|------|-------------|--------------|----------|
| `folder` | Closed folder node | 📁 | `folder.svg` |
| `folder_open` | Open folder node | 📂 | `folder_open.svg` |
| `sql` | SQL query file | 📄 | `sql.svg` |
| `config` | Configuration file | ⚙️ | `config.svg` |
| `parameter` | Parameter file | 📋 | `parameter.svg` |
| `context` | Context file | 🎯 | `context.svg` |
| `model` | Model file | 📦 | `model.svg` |
| `graph` | Workflow graph | 📊 | `graph.svg` |
| `target` | Target table | 🎯 | `target.svg` |

## Custom Icons
To use custom icons:

1. Create SVG files in `public/icons/` folder
2. Name format: `{type}.svg` for default icons
3. Or use `{type}_{name}.svg` for named variants

### Examples
```
public/icons/
├── folder.svg              # Default closed folder icon
├── folder_open.svg         # Open folder icon
├── folder_models.svg       # Custom icon for "models" folder
├── sql.svg                 # Default SQL icon
├── parameter.svg           # Default parameter icon
├── context.svg             # Default context icon
```

## SVG Guidelines
- Use 24x24 viewBox for consistency
- Use stroke-based icons (outline style)
- Match colors to your theme using CSS variables or fixed colors:
  - folder: `#dcb67a`
  - sql: `#9cdcfe`
  - config: `#c586c0`
  - parameter: `#4fc1ff`
  - context: `#4ec9b0`
  - model: `#569cd6`
  - graph: `#4ec9b0`
