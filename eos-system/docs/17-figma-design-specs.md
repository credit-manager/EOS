# EOS — Figma Design Specs
## مواصفات التصميم لـ Figma

> الإصدار: 1.0 | التاريخ: 2026-08-19
> الهدف: مواصفات دقيقة لتصميم Figma

---

## 1. Design Tokens

### Colors

#### Primary Colors
| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `primary-50` | #e6f7ff | 230, 247, 255 | Light backgrounds |
| `primary-100` | #bae7ff | 186, 231, 255 | Hover states |
| `primary-200` | #91d5ff | 145, 213, 255 | Active states |
| `primary-300` | #69c0ff | 105, 192, 255 | Disabled |
| `primary-400` | #40a9ff | 64, 169, 255 | Links |
| `primary-500` | #1890ff | 24, 144, 255 | **Main Primary** |
| `primary-600` | #096dd9 | 9, 109, 217 | Hover |
| `primary-700` | #0050b3 | 0, 80, 179 | Active |
| `primary-800` | #003a8c | 0, 58, 140 | Dark |
| `primary-900` | #002766 | 0, 39, 102 | Darkest |

#### Neutral Colors
| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `neutral-50` | #fafafa | 250, 250, 250 | Background |
| `neutral-100` | #f5f5f5 | 245, 245, 245 | Card background |
| `neutral-200` | #e8e8e8 | 232, 232, 232 | Borders |
| `neutral-300` | #d9d9d9 | 217, 217, 217 | Dividers |
| `neutral-400` | #bfbfbf | 191, 191, 191 | Disabled text |
| `neutral-500` | #8c8c8c | 140, 140, 140 | Secondary text |
| `neutral-600` | #595959 | 89, 89, 89 | Text |
| `neutral-700` | #434343 | 67, 67, 67 | Text |
| `neutral-800` | #262626 | 38, 38, 38 | Primary text |
| `neutral-900` | #141414 | 20, 20, 20 | Darkest |

### Typography

#### Font Families
```css
--font-primary: 'Cairo', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'Fira Code', 'Monaco', monospace;
```

#### Font Sizes
| Token | Size | Line Height | Usage |
|-------|------|-------------|-------|
| `text-xs` | 12px | 16px | Captions |
| `text-sm` | 14px | 22px | Body small |
| `text-base` | 16px | 24px | Body |
| `text-lg` | 18px | 28px | Subheadings |
| `text-xl` | 20px | 32px | Headings |
| `text-2xl` | 24px | 32px | Page titles |
| `text-3xl` | 30px | 38px | Section titles |
| `text-4xl` | 36px | 44px | Hero titles |

### Spacing

| Token | Size | Usage |
|-------|------|-------|
| `spacing-0` | 0 | Reset |
| `spacing-1` | 4px | Tight spacing |
| `spacing-2` | 8px | Small spacing |
| `spacing-3` | 12px | Medium spacing |
| `spacing-4` | 16px | Default spacing |
| `spacing-5` | 20px | Large spacing |
| `spacing-6` | 24px | Section spacing |
| `spacing-8` | 32px | Page spacing |
| `spacing-10` | 40px | Large sections |
| `spacing-12` | 48px | Page margins |
| `spacing-16` | 64px | Hero sections |

### Border Radius

| Token | Size | Usage |
|-------|------|-------|
| `radius-none` | 0 | No radius |
| `radius-sm` | 4px | Small elements |
| `radius-md` | 6px | Buttons, inputs |
| `radius-lg` | 8px | Cards |
| `radius-xl` | 12px | Modals |
| `radius-2xl` | 16px | Large cards |
| `radius-full` | 9999px | Pills, avatars |

---

## 2. Component Specs

### Button

#### Primary Button
```
Width: Auto (min 80px)
Height: 40px
Padding: 0 16px
Font: 14px / 500
Background: #1890ff
Color: #ffffff
Border: none
Border Radius: 6px
```

#### States
| State | Background | Shadow |
|-------|------------|--------|
| Default | #1890ff | none |
| Hover | #40a9ff | 0 2px 4px rgba(24,144,255,0.3) |
| Active | #096dd9 | none |
| Disabled | #d9d9d9 | none |

#### Button Sizes
| Size | Height | Font | Padding |
|------|--------|------|---------|
| Small | 24px | 12px | 0 8px |
| Medium | 40px | 14px | 0 16px |
| Large | 48px | 16px | 0 24px |

### Input

#### Standard Input
```
Width: 100% (or specified)
Height: 40px
Padding: 0 12px
Font: 14px / 400
Background: #ffffff
Border: 1px solid #d9d9d9
Border Radius: 6px
```

#### States
| State | Border | Background |
|-------|--------|------------|
| Default | #d9d9d9 | #ffffff |
| Hover | #40a9ff | #ffffff |
| Focus | #1890ff | #ffffff |
| Error | #ff4d4f | #ffffff |
| Disabled | #d9d9d9 | #f5f5f5 |

### Card

#### Standard Card
```
Width: 100% (or specified)
Padding: 24px
Background: #ffffff
Border: 1px solid #f0f0f0
Border Radius: 8px
Shadow: 0 1px 2px rgba(0,0,0,0.06)
```

#### Card with Header
```
Header Height: 56px
Header Padding: 0 24px
Header Border: 1px solid #f0f0f0
Body Padding: 24px
```

### Table

#### Standard Table
```
Header Height: 54px
Header Background: #fafafa
Header Font: 14px / 600
Row Height: 54px
Row Border: 1px solid #f0f0f0
Cell Padding: 16px
```

#### Table States
| State | Background |
|-------|------------|
| Default | #ffffff |
| Hover | #fafafa |
| Selected | #e6f7ff |
| Striped | #fafafa (odd rows) |

### Modal

#### Standard Modal
```
Width: 520px (small) / 720px (medium) / 960px (large)
Padding: 24px
Background: #ffffff
Border Radius: 12px
Shadow: 0 20px 25px rgba(0,0,0,0.1)
```

#### Modal Header
```
Height: 56px
Padding: 16px 24px
Border Bottom: 1px solid #f0f0f0
Font: 16px / 600
```

### Menu (Sidebar)

#### Standard Menu
```
Width: 200px (expanded) / 80px (collapsed)
Background: #001529
Item Height: 40px
Item Padding: 0 24px
Item Font: 14px / 400
Item Color: rgba(255,255,255,0.65)
```

#### Menu States
| State | Background | Color |
|-------|------------|-------|
| Default | transparent | rgba(255,255,255,0.65) |
| Hover | rgba(255,255,255,0.08) | #ffffff |
| Active | #1890ff | #ffffff |

---

## 3. Layout Specs

### Page Layout
```
┌─────────────────────────────────────────────────────┐
│ Header (64px)                                       │
├──────────┬──────────────────────────────────────────┤
│          │                                          │
│ Sidebar  │ Content Area                             │
│ (200px)  │ (calc(100% - 200px))                    │
│          │                                          │
│          │ ┌──────────────────────────────────────┐ │
│          │ │ Page Header (optional)               │ │
│          │ ├──────────────────────────────────────┤ │
│          │ │ Page Content                         │ │
│          │ │ (margin: 24px)                       │ │
│          │ └──────────────────────────────────────┘ │
│          │                                          │
└──────────┴──────────────────────────────────────────┘
```

### Grid System
```
12 Column Grid
Gutter: 16px
Margin: 24px (mobile) / 24px (desktop)

Breakpoints:
- xs: 0-575px (1 column)
- sm: 576-767px (2 columns)
- md: 768-991px (2-4 columns)
- lg: 992-1199px (4-6 columns)
- xl: 1200-1599px (6-12 columns)
- 2xl: 1600px+ (12 columns)
```

---

## 4. Icon Specs

### Icon Sizes
| Size | Usage |
|------|-------|
| 12px | Inline icons |
| 14px | Small buttons |
| 16px | Default icons |
| 18px | Menu icons |
| 20px | Large icons |
| 24px | Feature icons |
| 32px | Hero icons |

### Icon Library
- **Ant Design Icons** (Primary)
- **Custom SVG Icons** (Brand-specific)

---

## 5. Figma File Structure

```
EOS Design System
├── 🎨 Foundations
│   ├── Colors
│   ├── Typography
│   ├── Spacing
│   ├── Shadows
│   └── Icons
│
├── 🧩 Components
│   ├── Buttons
│   ├── Inputs
│   ├── Cards
│   ├── Tables
│   ├── Modals
│   ├── Menus
│   ├── Forms
│   └── Data Display
│
├── 📄 Templates
│   ├── Login
│   ├── Dashboard
│   ├── List Views
│   ├── Form Views
│   └── Detail Views
│
├── 📱 Responsive
│   ├── Mobile
│   ├── Tablet
│   └── Desktop
│
└── 📋 Documentation
    ├── Usage Guidelines
    ├── Component API
    └── Changelog
```

---

## 6. Download Links

| Resource | Link |
|----------|------|
| Figma File | [figma.com/file/eos-design-system] |
| Design Tokens | `frontend/src/styles/tokens.json` |
| Icon Library | [icons.eos-system.com] |
| Font Files | [fonts.eos-system.com] |

---

*EOS Design System — Figma Specs v1.0*
