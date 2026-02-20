# Keuvi Mobile UI Sync Specification

**Document Version**: 1.0
**Date**: 2025-02-19
**Purpose**: Design specifications for iOS and Android apps to match the Duolingo-style web redesign exactly.

---

## Executive Summary

This document provides exact design specifications extracted from the Keuvi web app for mobile implementation. The design follows Duolingo's visual language: 3D button effects, circular skill icons with progress rings, vibrant colors, and playful animations. All values are provided in exact measurements for pixel-perfect mobile implementation.

Key characteristics:
- **3D Depth**: All interactive elements use box-shadow "floors" to create 3D depth
- **Rounded Corners**: Liberal use of border-radius (12px-20px) for friendly feel
- **Vibrant Colors**: Duolingo-inspired palette with greens, blues, oranges, purples
- **Micro-animations**: Bounce effects, gentle float animations, and responsive press states

---

## Table of Contents

1. [Color Tokens](#1-color-tokens)
2. [Typography](#2-typography)
3. [Button Specifications](#3-button-specifications)
4. [Card Components](#4-card-components)
5. [Skill Grid System](#5-skill-grid-system)
6. [Landing/Onboarding](#6-landingonboarding)
7. [Dark Mode](#7-dark-mode)
8. [Animations](#8-animations)
9. [Spacing System](#9-spacing-system)
10. [Mobile Adaptations](#10-mobile-adaptations)

---

## 1. Color Tokens

### 1.1 Brand Colors (Primary Palette)

| Token Name | Hex Value | RGB | Usage |
|------------|-----------|-----|-------|
| `keuvi-green` | `#58CC02` | 88, 204, 2 | Primary CTA buttons, success states |
| `keuvi-green-dark` | `#46a302` | 70, 163, 2 | Button shadow/floor (3D effect) |
| `keuvi-green-hover` | `#61df00` | 97, 223, 0 | Hover/press highlight state |
| `keuvi-blue` | `#1CB0F6` | 28, 176, 246 | Secondary buttons, links, accents |
| `keuvi-blue-dark` | `#1899d6` | 24, 153, 214 | Blue button shadow/floor |
| `keuvi-blue-hover` | `#3dc0fc` | 61, 192, 252 | Blue hover state |
| `keuvi-orange` | `#FF9600` | 255, 150, 0 | Math category, tertiary actions |
| `keuvi-orange-dark` | `#e68600` | 230, 134, 0 | Orange shadow/floor |
| `keuvi-purple` | `#CE82FF` | 206, 130, 255 | Writing category, premium/special |
| `keuvi-purple-dark` | `#A855F7` | 168, 85, 247 | Purple gradient end |
| `keuvi-red` | `#FF4B4B` | 255, 75, 75 | Errors, challenges |
| `keuvi-red-dark` | `#E63939` | 230, 57, 57 | Red shadow |
| `keuvi-pink` | `#FF86D0` | 255, 134, 208 | Decorative accent |
| `keuvi-yellow` | `#FFC800` / `#FFD700` | 255, 200, 0 / 255, 215, 0 | Achievements, gold badges |
| `keuvi-teal` | `#20B2AA` | 32, 178, 170 | Alternative skill color |
| `keuvi-teal-dark` | `#178F89` | 23, 143, 137 | Teal shadow |

### 1.2 Category Colors (from API constants)

| Category | Primary | Dark/Shadow | Usage |
|----------|---------|-------------|-------|
| Reading | `#1CB0F6` (Blue) | `#1899d6` | Reading section, skill icons |
| Writing | `#CE82FF` (Purple) | `#A855F7` | Writing section, skill icons |
| Math | `#FF9600` (Orange) | `#e68600` | Math section, skill icons |

### 1.3 UI Colors - Light Mode

| Token | Hex | Usage |
|-------|-----|-------|
| `bg-primary` | `#f5f5f5` | Page background |
| `bg-secondary` | `#ffffff` | Card backgrounds, content areas |
| `bg-tertiary` | `#e0e0e0` | Inactive states, dividers |
| `text-primary` | `#000000` | Main text, headings |
| `text-secondary` | `#666666` | Subtext, labels, placeholders |
| `border-color` | `#e0e0e0` | Card borders, dividers |
| `border-light` | `#E5E5E5` | Lighter borders (buttons, cards) |
| `accent-color` | `#3498DB` | Links, highlights (non-brand) |
| `accent-hover` | `#2980B9` | Accent hover state |
| `shadow-default` | `#d1d1d1` | Button floor shadows |

### 1.4 Semantic Colors

| State | Hex | Usage |
|-------|-----|-------|
| `success` | `#27ae60` / `#28a745` | Correct answers, success states |
| `success-bg` | `#d4edda` | Success background |
| `error` | `#dc3545` / `#e74c3c` | Incorrect answers, errors |
| `error-bg` | `#f8d7da` | Error background |
| `warning` | `#ffc107` | Rules, cautions |
| `warning-bg` | `#fff3cd` | Warning background |
| `info` | `#3498DB` | Information, tips |
| `info-bg` | `#f0f8ff` | Info background |

### 1.5 Premium/Brand

| Token | Hex | Usage |
|-------|-----|-------|
| `navy` | `#083242` | Premium sections background |
| `navy-alt` | `#1B2A4A` | Alternative navy |
| `gold` | `#FFD700` | Premium badges, crowns |
| `gold-gradient-end` | `#FFA500` | Lock badge gradient |
| `hero-gray` | `#3C3C3C` | Hero title text |
| `tagline-gray` | `#6B7280` | Tagline/subtitle text |
| `feature-gray` | `#4B5563` | Feature item text |

---

## 2. Typography

### 2.1 Font Family Stack

```
Primary: 'DIN Round Pro', 'Nunito', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
```

**Mobile Implementation**:
- **iOS**: Use system font (`-apple-system`) or bundle Nunito
- **Android**: Use `Roboto` or bundle Nunito

**For SAT content (passages)**:
```
Serif: 'Minion Pro', 'Minion', 'Times New Roman', 'Times', serif
Sans: 'Myriad Pro', 'Myriad', 'Arial', sans-serif (questions)
```

### 2.2 Font Weights

| Weight Name | Value | Usage |
|-------------|-------|-------|
| Regular | 400 | Body text |
| Medium | 500 | Form labels, navigation |
| Semibold | 600 | Subheadings, emphasis |
| Bold | 700 | Buttons, card titles |
| Extra Bold | 800 | Hero titles, logo text |

### 2.3 Font Sizes (Desktop -> Mobile)

| Element | Desktop | Mobile (768px) | Mobile (480px) |
|---------|---------|----------------|----------------|
| Hero Title | 42px | 28px | 24px |
| Hero Title Highlight | 48px | 32px | 26px |
| Hero Tagline | 20px | 16px | 14px |
| Section Header (h2) | 24px | 26px | 20px |
| Card Title (h3) | 18px | 18px | 16px |
| Button Text | 14-15px | 14-15px | 12-14px |
| Body Text | 14-16px | 14px | 14px |
| Small/Caption | 11-13px | 11-12px | 10-12px |
| Skill Title | 12px | 11px | 10px |
| Skill Icon Letter | 32px | 28px | 24px |
| Score Display | 32px | 32px | 32px |
| Premium Price | 48px | 36px | 36px |

### 2.4 Letter Spacing

| Usage | Value |
|-------|-------|
| Buttons (uppercase) | 0.5px - 1px |
| Logo | -0.5px |
| Labels | 0.5px |

### 2.5 Line Heights

| Element | Value |
|---------|-------|
| Hero Title | 1.15 |
| Body Text | 1.45 - 1.7 |
| Taglines | 1.5 |
| Card Descriptions | 1.6 |

---

## 3. Button Specifications

### 3.1 Primary Button (Green CTA)

```
Background: #58CC02
Text Color: #FFFFFF
Font Weight: 700
Font Size: 14-15px
Text Transform: UPPERCASE
Letter Spacing: 0.5-1px
Border Radius: 12px
Padding: 12px 20px

3D Effect:
  - Box Shadow: 0 4px 0 #46a302

Hover State:
  - Background: #61df00
  - Transform: translateY(-1px)
  - Box Shadow: 0 5px 0 #46a302

Active/Pressed State:
  - Transform: translateY(2px)
  - Box Shadow: 0 2px 0 #46a302
```

### 3.2 Secondary Button (Blue)

```
Background: #1CB0F6
Text Color: #FFFFFF
Border Radius: 12px
Padding: 12px 20px

3D Effect:
  - Box Shadow: 0 4px 0 #1899d6

Hover:
  - Background: #3dc0fc
  - Transform: translateY(-1px)
  - Box Shadow: 0 5px 0 #1899d6

Active:
  - Transform: translateY(2px)
  - Box Shadow: 0 2px 0 #1899d6
```

### 3.3 Ghost/Outline Button

```
Background: transparent or var(--bg-secondary)
Text Color: #1CB0F6
Border: 2px solid #E5E5E5
Border Radius: 12px
Box Shadow: 0 4px 0 #d1d1d1

Hover:
  - Background: rgba(28, 176, 246, 0.1)
  - Border Color: #1CB0F6
  - Transform: translateY(-1px)
  - Box Shadow: 0 5px 0 #d1d1d1

Active:
  - Transform: translateY(2px)
  - Box Shadow: 0 2px 0 #d1d1d1
```

### 3.4 Large CTA Buttons (Hero Section)

```
Primary Large:
  - Padding: 16px 80px
  - Font Size: 15px
  - Border Radius: 16px
  - Min Width: 280px
  - Box Shadow: 0 5px 0 #46a302

  Hover:
    - Transform: translateY(-2px)
    - Box Shadow: 0 7px 0 #46a302

  Active:
    - Transform: translateY(3px)
    - Box Shadow: 0 2px 0 #46a302

Secondary Large:
  - Same structure but with blue colors
  - Box Shadow: 0 5px 0 #1899d6
```

### 3.5 Category Picker Buttons

```
Default:
  - Background: var(--bg-secondary)
  - Text Color: var(--text-secondary)
  - Border: 2px solid #E5E5E5
  - Border Radius: 12px
  - Padding: 14px 20px
  - Box Shadow: 0 4px 0 #d1d1d1

Active/Selected:
  - Background: #1CB0F6
  - Text Color: white
  - Border Color: #1CB0F6
  - Box Shadow: 0 4px 0 #1899d6
```

### 3.6 Mobile Touch Targets

```
Minimum Height: 44px (iOS HIG requirement)
Minimum Touch Area: 44x44 points
Button Padding Mobile: 12-14px vertical
```

---

## 4. Card Components

### 4.1 Passage Card

```
Background: var(--bg-secondary)
Border: 2px solid #E5E5E5
Border Radius: 16px
Padding: 20px
Margin Bottom: 12px
Box Shadow: 0 2px 0 #d1d1d1

Title:
  - Font Size: 18px
  - Font Weight: 700
  - Color: var(--text-primary)

Description:
  - Font Size: 14px
  - Color: var(--text-secondary)

Hover:
  - Border Color: #58CC02
  - Transform: translateY(-2px)
  - Box Shadow: 0 4px 0 rgba(88, 204, 2, 0.3)

Active:
  - Transform: translateY(1px)
  - Box Shadow: 0 1px 0 #d1d1d1

Premium Indicator:
  - Border Left: 4px solid #CE82FF
```

### 4.2 Feature Highlight Card

```
Background: var(--bg-secondary)
Border: 2px solid #E5E5E5
Border Radius: 16px
Padding: 28px 24px 24px
Box Shadow: 0 2px 0 #E5E5E5
Text Align: center

Icon Container:
  - Width/Height: 72px
  - Border Radius: 50% (circle)
  - Box Shadow: 0 4px 0 [darker shade]
  - Colors per position:
    - 1st: Green (#58CC02, shadow #46a302)
    - 2nd: Blue (#1CB0F6, shadow #1899d6)
    - 3rd: Orange (#FF9600, shadow #e68600)

Title:
  - Font Size: 18px
  - Font Weight: 700

Description:
  - Font Size: 14px
  - Color: var(--text-secondary)

Hover:
  - Transform: translateY(-4px)
  - Border Color: #58CC02
  - Box Shadow: 0 6px 0 rgba(88, 204, 2, 0.3)
```

### 4.3 Question Card

```
Border: 1px solid var(--border-color)
Border Radius: 8px
Padding: 20px
Margin Bottom: 20px
Background: var(--bg-secondary)

Question Title (h4):
  - Font Size: 18px (desktop), 16px (mobile)
  - Font Weight: 600
```

### 4.4 Option/Answer Choice

```
Default:
  - Border: 2px solid var(--border-color)
  - Border Radius: 6px
  - Padding: 12px (desktop), 16px (mobile)
  - Background: var(--bg-secondary)
  - Margin Bottom: 10-12px

Selected:
  - Border Color: var(--accent-color)
  - Background: var(--bg-primary)

Correct:
  - Border Color: #27ae60
  - Background: #d4edda

Incorrect:
  - Border Color: #e74c3c
  - Background: #f8d7da
```

### 4.5 Explanation Box

```
Background: #f0f8ff (light), rgba(52, 152, 219, 0.15) (dark)
Border Left: 4px solid #3498DB
Border Radius: 4px
Padding: 15px (mobile: 20px horizontal)
Font Size: 14px
Line Height: 1.6
```

---

## 5. Skill Grid System

### 5.1 Grid Container

```
Display: flex wrap
Justify Content: center
Gap: 24px (desktop), 16px (tablet), 12px (small mobile)
Padding: 20px 10px
Max Width: 600px
Margin: 0 auto
```

### 5.2 Skill Node

```
Width: 100px (desktop), 85px (tablet), 75px (small)
Display: flex column
Align Items: center
Gap: 8px

Hover:
  - Transform: scale(1.08)

Active:
  - Transform: scale(0.98)

Locked State:
  - Opacity: 0.5
  - Cursor: not-allowed
  - No transform on hover
```

### 5.3 Skill Icon (Circle)

```
Size: 80px x 80px (desktop), 70px (tablet), 60px (small)
Border Radius: 50%
Box Shadow: 0 4px 12px rgba(0, 0, 0, 0.15)
Overflow: visible (for progress ring)

Gradient Backgrounds by Color:
  - Green: linear-gradient(135deg, #58CC02 0%, #46A302 100%)
  - Purple: linear-gradient(135deg, #CE82FF 0%, #A855F7 100%)
  - Blue: linear-gradient(135deg, #00BFFF 0%, #0095CC 100%)
  - Orange: linear-gradient(135deg, #FF9500 0%, #E68600 100%)
  - Red: linear-gradient(135deg, #FF4B4B 0%, #E63939 100%)
  - Yellow: linear-gradient(135deg, #FFCC00 0%, #E6B800 100%)
  - Teal: linear-gradient(135deg, #20B2AA 0%, #178F89 100%)
  - Pink: linear-gradient(135deg, #FF69B4 0%, #E65FA3 100%)

Hover:
  - Box Shadow: 0 6px 20px rgba(0, 0, 0, 0.25)

Inner Image:
  - Size: 50px (desktop), 42px (tablet), 36px (small)
  - Border Radius: 8px

Letter Fallback:
  - Font Size: 32px (desktop), 28px (tablet), 24px (small)
  - Font Weight: 700
  - Color: white
  - Text Shadow: 0 2px 4px rgba(0, 0, 0, 0.2)
```

### 5.4 Progress Ring

```
Container:
  - Position: absolute
  - Inset: -6px (desktop), -5px (mobile)

SVG:
  - Width/Height: 100%
  - Transform: rotate(-90deg)

Background Track:
  - Fill: none
  - Stroke: var(--bg-tertiary)
  - Stroke Width: 4 (desktop), 3 (mobile)

Progress Fill:
  - Fill: none
  - Stroke Width: 4 (desktop), 3 (mobile)
  - Stroke Linecap: round
  - Stroke Color: [category color]
  - Transition: stroke-dashoffset 0.3s ease

Calculation:
  - Circumference = 2 * PI * radius
  - dashoffset = circumference * (1 - progress)
```

### 5.5 Completion Crown Badge

```
Position: absolute top -12px right -8px
Font Size: 20px
Filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3))
Animation: crown-bounce 2s ease-in-out infinite
```

### 5.6 Premium Lock Badge

```
Position: absolute bottom -4px right -4px
Size: 24px x 24px
Background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%)
Border Radius: 50%
Border: 2px solid var(--bg-secondary)
Font Size: 12px (lock emoji)
Box Shadow: 0 2px 6px rgba(0, 0, 0, 0.3)
```

### 5.7 Skill Title

```
Font Size: 12px (desktop), 11px (tablet), 10px (small)
Font Weight: 600
Color: var(--text-primary)
Text Align: center
Max Width: 90px (desktop), 80px (tablet), 70px (small)
Line Clamp: 2 lines
Line Height: 1.2
```

---

## 6. Landing/Onboarding

### 6.1 Hero Section

```
Background: #FFFFFF (light), var(--bg-secondary) (dark)
Border: 2px solid #E5E5E5
Border Radius: 20px (desktop), 16px (tablet), 12px (small)
Padding: 40px 48px (desktop), 32px 24px (tablet), 24px 16px (small)
Text Align: center
Max Width: 100%
Margin Bottom: 32px

Pattern Overlay:
  - SVG dot pattern (4px radius circles)
  - Opacity: 0.02 (light), 0.03 (dark)
```

### 6.2 Hero Mascot Logo

```
Height: 380px (desktop), 280px (tablet), 220px (small)
Animation: gentleBounce 4s ease-in-out infinite
Filter: drop-shadow(0 8px 16px rgba(0, 0, 0, 0.15))

Dark Mode:
  - Filter: drop-shadow(0 8px 20px rgba(255, 255, 255, 0.2))
```

### 6.3 Hero Title

```
Font Size: 42px (desktop), 28px (tablet), 24px (small)
Font Weight: 800
Color: #3C3C3C
Line Height: 1.15
Margin Bottom: 16px

Highlight Text (accent line):
  - Display: block
  - Color: #58CC02
  - Font Size: 48px (desktop), 32px (tablet), 26px (small)
  - Margin Top: 4px
```

### 6.4 Hero Tagline

```
Font Size: 20px (desktop), 16px (tablet), 14px (small)
Color: #6B7280
Font Weight: 500
Line Height: 1.5
Margin Bottom: 32px (desktop), 24px (mobile)
```

### 6.5 Feature Checkmarks Row

```
Container:
  - Display: flex wrap
  - Justify Content: center
  - Gap: 24px (desktop), 12px (mobile)

Item:
  - Display: flex row
  - Align Items: center
  - Gap: 8px
  - Font Size: 15px (desktop), 13px (tablet), 12px (small)
  - Color: #4B5563
  - Font Weight: 600

Checkmark Icon:
  - Size: 24px
  - Background: #58CC02
  - Border Radius: 50%
  - Display: flex center
  - Font Size: 12px (white checkmark)
```

### 6.6 Floating Decorative Shapes

```
Shape 1 (Green):
  - Size: 200px
  - Position: top -50px, left -50px
  - Color: #58CC02
  - Opacity: 0.08

Shape 2 (Blue):
  - Size: 150px
  - Position: top 60%, right -40px
  - Color: #1CB0F6
  - Animation Delay: 2s

Shape 3 (Yellow):
  - Size: 100px
  - Position: bottom -30px, left 20%
  - Color: #FFC800
  - Animation Delay: 4s

Shape 4 (Purple):
  - Size: 80px
  - Position: top 20%, right 15%
  - Color: #CE82FF
  - Animation Delay: 1s

Animation: floatSlow 8s ease-in-out infinite

Note: Hidden on mobile (display: none under 768px)
```

### 6.7 Social Proof Strip

```
Container:
  - Display: flex wrap
  - Justify Content: center
  - Gap: 48px (desktop), 24px (mobile)
  - Margin Top: 48px (desktop), 32px (mobile)
  - Padding Top: 32px (desktop), 24px (mobile)
  - Border Top: 1px solid #E5E5E5

Item:
  - Display: flex column
  - Align Items: center
  - Gap: 4px
  - Color: #6B7280
  - Font Size: 13px (desktop), 11px (mobile)
  - Font Weight: 600
  - Text Transform: uppercase
  - Letter Spacing: 0.5px

Number:
  - Font Size: 24px (desktop), 20px (mobile)
  - Font Weight: 800
  - Color: #3C3C3C

Icon:
  - Font Size: 28px (desktop), 24px (mobile)
  - Margin Bottom: 4px
```

### 6.8 Premium Promo Section

```
Background: #083242 (navy)
Border Radius: 16px
Padding: 48px 32px (desktop), 36px 24px (mobile)
Text Align: center

Pattern Overlay:
  - Diamond SVG pattern
  - Fill opacity: 0.05

Badge:
  - Background: rgba(255, 255, 255, 0.2)
  - Padding: 6px 16px
  - Border Radius: 20px
  - Font Size: 12px
  - Letter Spacing: 1px

Title:
  - Font Size: 28px (desktop), 22px (mobile)
  - Font Weight: 800
  - Color: white

Description:
  - Font Size: 16px (desktop), 14px (mobile)
  - Color: rgba(255, 255, 255, 0.9)
  - Max Width: 400px

Price:
  - Amount: 48px (desktop), 36px (mobile), weight 800
  - Period: 18px, rgba(255, 255, 255, 0.8)

Premium Button:
  - Background: white
  - Color: #083242
  - Box Shadow: 0 5px 0 rgba(0, 0, 0, 0.2)
  - Same hover/active as other 3D buttons
```

---

## 7. Dark Mode

### 7.1 Color Mappings

| Token | Light Mode | Dark Mode |
|-------|------------|-----------|
| `bg-primary` | `#f5f5f5` | `#1a1a1a` |
| `bg-secondary` | `#ffffff` | `#2d2d2d` |
| `bg-tertiary` | `#e0e0e0` | `#3d3d3d` |
| `text-primary` | `#000000` | `#ffffff` |
| `text-secondary` | `#666666` | `#b0b0b0` |
| `border-color` | `#e0e0e0` | `#404040` |
| `accent-color` | `#3498DB` | `#5dade2` |
| `accent-hover` | `#2980B9` | `#3498DB` |
| `shadow` | `rgba(0,0,0,0.08)` | `rgba(0,0,0,0.3)` |
| `modal-overlay` | `rgba(0,0,0,0.5)` | `rgba(0,0,0,0.7)` |

### 7.2 Semantic Background Mappings

| Light Mode | Dark Mode |
|------------|-----------|
| `#f0f8ff` (info blue) | `rgba(52, 152, 219, 0.15)` |
| `#f0fff0` (success green) | `rgba(40, 167, 69, 0.15)` |
| `#fff0f0` (error red) | `rgba(220, 53, 69, 0.15)` |
| `#fff9e6` / `#fffacd` (warning yellow) | `rgba(255, 193, 7, 0.15)` |
| `#f9f9f9` (neutral) | `var(--bg-secondary)` |

### 7.3 Component Adjustments

- Button floor shadows use `var(--border-color)` instead of `#d1d1d1`
- Card borders use `var(--border-color)` instead of `#E5E5E5`
- Hero mascot gets different drop-shadow: `0 8px 20px rgba(255, 255, 255, 0.2)`
- Logo text color follows `var(--text-primary)` instead of fixed `#083242`

### 7.4 Transition

All theme-sensitive properties use: `transition: 0.3s ease`

---

## 8. Animations

### 8.1 Crown Bounce (Completion Badge)

```
Name: crown-bounce
Duration: 2s
Timing: ease-in-out
Iteration: infinite

Keyframes:
  0%, 100%: translateY(0)
  50%: translateY(-2px)
```

### 8.2 Flame Flicker (Streak)

```
Name: flame-flicker
Duration: 0.8s
Timing: ease-in-out
Iteration: infinite
Direction: alternate

Keyframes:
  from: scale(1)
  to: scale(1.1)
```

### 8.3 Gentle Bounce (Hero Mascot)

```
Name: gentleBounce
Duration: 4s
Timing: ease-in-out
Iteration: infinite

Keyframes:
  0%, 100%: translateY(0)
  50%: translateY(-12px)
```

### 8.4 Float Slow (Decorative Shapes)

```
Name: floatSlow
Duration: 8s
Timing: ease-in-out
Iteration: infinite

Keyframes:
  0%, 100%: translateY(0) scale(1)
  50%: translateY(-15px) scale(1.02)
```

### 8.5 Fade In (Page Transitions)

```
Name: fadeIn
Duration: 0.5s
Timing: ease-out

Keyframes:
  from: opacity(0) translateY(8px)
  to: opacity(1) translateY(0)
```

### 8.6 Button Press Animation

For mobile tap feedback, implement:
```
Press Down:
  - Duration: 0.15s (instant feel)
  - Transform: translateY(2-3px)
  - Shadow reduction: 4px -> 2px

Release:
  - Duration: 0.15s
  - Transform: translateY(0)
  - Shadow restore: 2px -> 4px
```

### 8.7 Scale Hover (Skill Nodes)

```
Hover/Focus: scale(1.08)
Active/Press: scale(0.98)
Duration: 0.2s ease
```

---

## 9. Spacing System

### 9.1 Base Units

```
4px  - micro spacing (icon margins, inline gaps)
8px  - small spacing (between related elements)
12px - medium spacing (card padding mobile)
16px - standard spacing (section margins)
20px - comfortable spacing (card padding)
24px - generous spacing (section gaps)
32px - large spacing (hero elements)
48px - extra large (major sections)
```

### 9.2 Component Spacing

| Element | Value |
|---------|-------|
| Card Padding | 20px (desktop), 16-20px (mobile) |
| Card Margin Bottom | 12-16px |
| Button Padding | 12px 20px |
| Button Padding Large | 16px 80px (desktop), 14px 32px (mobile) |
| Section Margin | 48px (desktop), 32px (mobile) |
| Grid Gap | 24px (desktop), 16px (tablet), 12px (mobile) |
| Container Max Width | 1400px |
| Content Max Width | 1200px (landing), 720px (hero content) |
| Sidebar Width | 300px (desktop), 100% (mobile) |
| Container Padding | 24px (desktop), 16px (tablet), 12px (mobile) |

### 9.3 Border Radius Scale

| Use Case | Value |
|----------|-------|
| Small (badges, tags) | 4px |
| Medium (inputs, options) | 6px |
| Standard (buttons) | 12px |
| Large (cards, sections) | 16px |
| Extra Large (hero) | 20px |
| Circle (icons, avatars) | 50% |

---

## 10. Mobile Adaptations

### 10.1 Breakpoints

| Name | Width | Notes |
|------|-------|-------|
| Large Desktop | > 1024px | Full experience |
| Desktop | > 768px | Standard desktop |
| Tablet | <= 768px | Single column, adjusted sizing |
| Mobile | <= 480px | Compact layout |

### 10.2 Layout Changes

**768px and below:**
- Grid becomes single column
- Sidebar moves below content
- Feature highlights stack vertically
- Hero shapes hidden
- Hero CTA buttons become full-width
- Category picker remains horizontal but with smaller padding

**480px and below:**
- Further size reductions
- Increased touch targets
- More compact spacing

### 10.3 Touch-Specific Considerations

1. **Hover States** -> Convert to tap states
   - Web hover: `translateY(-2px)` -> Mobile: No hover state
   - Web active: `translateY(2px)` -> Mobile: Same active press state

2. **Touch Targets**: Minimum 44x44 points

3. **Tap Feedback**: Use native platform haptics if available

4. **Scroll Behavior**:
   - Skills grid can scroll horizontally on small screens
   - Sidebar becomes scrollable section

### 10.4 Platform-Specific Notes

**iOS:**
- Use SF Pro or system font as fallback
- Support for `env(safe-area-inset-*)` for notched devices
- Consider iOS-specific haptic feedback (UIImpactFeedbackGenerator)

**Android:**
- Use Roboto as fallback
- Material Design ripple effects can complement 3D buttons
- Support edge-to-edge display insets

---

## Appendix A: CSS Variables Quick Reference

```css
:root {
  /* Backgrounds */
  --bg-primary: #f5f5f5;
  --bg-secondary: #ffffff;
  --bg-tertiary: #e0e0e0;

  /* Text */
  --text-primary: #000000;
  --text-secondary: #666666;

  /* Borders */
  --border-color: #e0e0e0;

  /* Accents */
  --accent-color: #3498DB;
  --accent-hover: #2980B9;

  /* Shadow */
  --shadow: rgba(0,0,0,0.08);

  /* Brand */
  --keuvi-green: #58CC02;
  --keuvi-green-dark: #46a302;
  --keuvi-blue: #1CB0F6;
  --keuvi-blue-dark: #1899d6;
  --keuvi-orange: #FF9600;
  --keuvi-purple: #CE82FF;
  --keuvi-pink: #FF86D0;
  --keuvi-red: #FF4B4B;
  --navy: #083242;
  --gold: #FFC800;
}

.dark-mode {
  --bg-primary: #1a1a1a;
  --bg-secondary: #2d2d2d;
  --bg-tertiary: #3d3d3d;
  --text-primary: #ffffff;
  --text-secondary: #b0b0b0;
  --border-color: #404040;
  --accent-color: #5dade2;
  --accent-hover: #3498DB;
  --shadow: rgba(0,0,0,0.3);
}
```

---

## Appendix B: 3D Button Implementation Pattern

The signature Duolingo-style 3D button effect follows this pattern:

```
Structure:
  1. Main button face (background color)
  2. "Floor" shadow (box-shadow with solid color, offset Y)
  3. Press animation (translateY to simulate depth)

Implementation Steps:
  1. Set box-shadow: 0 [depth]px 0 [darker-shade]
  2. On press: translateY([depth - 2]px), reduce shadow to 0 2px 0
  3. On release: return to default

Common Depths:
  - Standard buttons: 4px
  - Large buttons: 5px
  - Card hover shadows: 6px
  - Active/pressed: 2px
```

---

## Document Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-02-19 | Initial specification extracted from web app |

---

**End of Document**
