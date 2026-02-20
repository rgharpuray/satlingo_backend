# Visual Enhancements Research - Duolingo-Style UI

**Prepared by**: PACT Preparer Agent
**Date**: 2026-02-19
**Status**: Research Complete

---

## Executive Summary

This document provides comprehensive research for adding Duolingo-style visual enhancements to Keuvi. The research covers Duolingo's design patterns, icon generation approaches, required data model changes, and mobile optimization best practices.

**Key Findings**:
1. Duolingo's visual appeal stems from bold colors, rounded shapes, animated icons, and a consistent illustrative language using three fundamental shapes (rounded rectangle, circle, rounded triangle)
2. A hybrid approach for icons is recommended: AI-generated icons for batch content, with manual upload capability for special cases
3. Data model changes are straightforward - adding `icon_url` fields to Lesson, Passage, Header, MathSection, and WritingSection models
4. GCS is already configured and can serve icons efficiently; consider adding Cloud CDN for global performance

**Recommendations**:
- Start with static icon support (manual upload + AI generation)
- Use WebP format for optimal compression and quality
- Target 256x256px icons scaled to @1x/@2x/@3x for density
- Consider imgproxy or Cloud Functions for on-the-fly resizing

---

## 1. Duolingo Visual Design Patterns

### 1.1 Core Design Philosophy

Duolingo's visual identity is characterized by:

| Element | Description |
|---------|-------------|
| **Color Palette** | Bold, vibrant colors on white backgrounds |
| **Shape Language** | Three fundamental shapes: rounded rectangle, circle, rounded triangle |
| **Minimalism** | Fewest details needed to communicate - clarity over complexity |
| **Animation** | Animated skill icons increase engagement (users watch longer than static) |
| **Consistency** | Same illustrative style across entire app |

### 1.2 Lesson/Unit Visual Structure

From Duolingo's home screen redesign:

- **Single learning path** with clear progression
- **Skill icons** that transition from greyed-out to full color as completed
- **Animated icons** for active lessons (increases user attention)
- **Milestone markers** replacing the old crown system
- **Units broken into smaller "chunks"** for less intimidation

### 1.3 Icon Design Principles

From Duolingo's art style blog:

1. **Readability first**: Icons must be clear at small sizes
2. **Limited color palette**: 2-3 colors per icon maximum
3. **No thin lines or small text**: These blur at small sizes
4. **Visual intrigue through variation**: Different combinations of base shapes
5. **Brand consistency**: Same style across all icons

### 1.4 Gamification Elements

Key visual gamification patterns:

- Progress indicators (bars, percentages)
- Achievement badges with distinct icons
- Streak visualizations (fire icon)
- Leaderboard elements
- XP/point displays
- Level indicators

---

## 2. Icon Generation Approaches

### 2.1 Option Comparison Matrix

| Approach | Pros | Cons | Cost | Best For |
|----------|------|------|------|----------|
| **AI Generation (DALL-E 3)** | Consistent style, fast, scalable | Requires prompting skill, may need iteration | $0.04-0.08/image | Bulk icon creation |
| **AI Generation (Stable Diffusion)** | Lower cost, highly customizable | Requires more setup | $0.002-0.025/image | Custom fine-tuned style |
| **Manual Upload** | Full control, perfect quality | Slow, requires designer | Designer time | Special/hero icons |
| **Icon Libraries (SVG)** | Free, professional, scalable | Generic, not unique | Free | System icons, fallbacks |
| **Hybrid** | Best of all worlds | More complex system | Varies | **Recommended** |

### 2.2 AI Image Generation APIs

#### DALL-E 3 (OpenAI)
- **API Pricing**: $0.040/image (standard), $0.080/image (HD)
- **Best for**: Clean, consistent icons from simple prompts
- **Output**: PNG, square format
- **Integration**: REST API, Python SDK

#### Stable Diffusion 3.5
- **Self-hosted**: Free (requires GPU)
- **Via API providers**: ~$0.025/image
- **Best for**: Custom fine-tuned models for brand consistency
- **Output**: PNG, configurable dimensions

**Recommended Approach**: Use DALL-E 3 API for initial icon generation with a consistent prompt template:

```
"Minimalist educational icon for [TOPIC], Duolingo-style,
rounded shapes, vibrant colors on white background,
simple 2D vector art, no text, no shadows"
```

### 2.3 Open Source Icon Libraries

For system icons and fallbacks:

| Library | Icons | License | Format |
|---------|-------|---------|--------|
| SVG Repo | 500,000+ | Various (mostly free) | SVG |
| Iconoir | 1,300+ | MIT | SVG, Font, React |
| Tabler Icons | 4,950+ | MIT | SVG |
| Heroicons | 300+ | MIT | SVG, JSX |
| unDraw | Illustrations | MIT | SVG, PNG |

---

## 3. Required Data Model Changes

### 3.1 Current State Analysis

Existing models that need icon support:

| Model | Current Visual Fields | Proposed Addition |
|-------|----------------------|-------------------|
| `Lesson` | None | `icon_url`, `icon_color` |
| `Passage` | None | `icon_url`, `icon_color` |
| `Header` | None | `icon_url`, `background_color` |
| `MathSection` | None | `icon_url`, `icon_color` |
| `WritingSection` | None | `icon_url`, `icon_color` |

### 3.2 Proposed Field Additions

```python
# Add to Lesson model
icon_url = models.URLField(
    max_length=500,
    null=True,
    blank=True,
    help_text="URL to lesson icon image (256x256 WebP recommended)"
)
icon_color = models.CharField(
    max_length=7,
    null=True,
    blank=True,
    default='#58CC02',  # Duolingo green
    help_text="Primary icon background/accent color (hex format)"
)

# Add to Header model
icon_url = models.URLField(
    max_length=500,
    null=True,
    blank=True,
    help_text="URL to header/unit icon image"
)
background_color = models.CharField(
    max_length=7,
    null=True,
    blank=True,
    default='#1CB0F6',  # Duolingo blue
    help_text="Header background color (hex format)"
)
```

### 3.3 Suggested Color Palette (Duolingo-Inspired)

```python
ICON_COLOR_CHOICES = [
    ('#58CC02', 'Green - Primary'),      # Main Duolingo green
    ('#1CB0F6', 'Blue - Skills'),        # Skill icons
    ('#FF9600', 'Orange - Practice'),    # Practice/review
    ('#FF4B4B', 'Red - Challenge'),      # Hard/challenge
    ('#CE82FF', 'Purple - Special'),     # Premium/special
    ('#FFD900', 'Yellow - Achievement'), # Achievements/XP
]
```

### 3.4 Migration Strategy

1. Add nullable fields first (no downtime)
2. Backfill with default icons for existing content
3. Add admin UI for icon upload/generation
4. Update API serializers to include new fields

---

## 4. Mobile App Optimization

### 4.1 Image Sizing Requirements

| Platform | Density | Icon Size | Display Size |
|----------|---------|-----------|--------------|
| iOS @1x | 1x | 64x64 | 64pt |
| iOS @2x | 2x | 128x128 | 64pt |
| iOS @3x | 3x | 192x192 | 64pt |
| Android mdpi | 1x | 64x64 | 64dp |
| Android hdpi | 1.5x | 96x96 | 64dp |
| Android xhdpi | 2x | 128x128 | 64dp |
| Android xxhdpi | 3x | 192x192 | 64dp |
| Android xxxhdpi | 4x | 256x256 | 64dp |

**Recommendation**: Store at 256x256 master size, serve scaled versions.

### 4.2 Format Recommendations

| Format | Compression | Transparency | Mobile Support | Recommendation |
|--------|-------------|--------------|----------------|----------------|
| **WebP** | Excellent | Yes | iOS 14+, All Android | **Primary format** |
| PNG | Good | Yes | Universal | Fallback |
| AVIF | Best | Yes | iOS 16+, Android 12+ | Future consideration |
| SVG | Scalable | Yes | WebView only | System icons |

### 4.3 Caching Strategy

**Client-Side (Mobile Apps)**:
```swift
// iOS - URLCache + NSCache for images
// Android - Coil/Glide with disk cache

Cache-Control: public, max-age=31536000  // 1 year for icons
ETag: based on content hash
```

**Server-Side (GCS + CDN)**:
- Enable Cloud CDN for GCS bucket
- Set appropriate cache headers
- Consider on-the-fly resizing

### 4.4 Lazy Loading Considerations

- Icons above the fold: Eager load
- Icons below the fold: Lazy load
- Placeholder: Use `icon_color` as solid background while loading
- Error state: Fall back to category-based default icon

---

## 5. Storage and Serving Architecture

### 5.1 Current GCS Setup

From `storage_backend.py`, Keuvi already has:
- GCS client with credential management
- Upload function returning public URLs
- Delete function for cleanup
- Abstraction layer supporting both S3 and GCS

### 5.2 Recommended Icon Storage Structure

```
keuvi-app/                          # Existing GCS bucket
  icons/
    lessons/
      {lesson_id}/
        icon.webp                   # Master 256x256
        icon@2x.webp                # 128x128
        icon@1x.webp                # 64x64
    passages/
      {passage_id}/icon.webp
    headers/
      {header_id}/icon.webp
    math_sections/
      {section_id}/icon.webp
    defaults/
      reading.webp                  # Category defaults
      writing.webp
      math.webp
```

### 5.3 On-Demand Image Resizing Options

#### Option A: Pre-generate Sizes (Simple)
- Generate all sizes at upload time
- Store multiple files per icon
- Pros: Simple, fast serving
- Cons: More storage, slower uploads

#### Option B: imgproxy + Cloud Run (Recommended for scale)
```
https://imgproxy.keuvi.app/resize:64:64/icons/lessons/abc/icon.webp
```
- Resize on-the-fly, cache at CDN edge
- Single master file per icon
- Pros: Efficient storage, flexible
- Cons: More infrastructure

#### Option C: Cloud Functions Resizer
- Triggered on upload
- Generates all sizes automatically
- Good middle ground

**Recommendation**: Start with Option A (pre-generate), migrate to Option B as content grows.

### 5.4 CDN Configuration

For optimal global performance:

1. Enable Cloud CDN on GCS bucket
2. Configure cache headers:
   ```
   Cache-Control: public, max-age=31536000, immutable
   ```
3. Use versioned URLs (include hash or timestamp) for cache busting

---

## 6. Implementation Recommendations

### 6.1 Phase 1: Foundation

1. **Database Migration**
   - Add `icon_url` and `icon_color` to Lesson, Passage, Header, MathSection
   - Create default icon set for each category

2. **Admin Interface**
   - Add icon upload widget to admin forms
   - Add color picker for `icon_color`
   - Preview functionality

3. **API Updates**
   - Update serializers to include `icon_url` and `icon_color`
   - Add default icon URL logic for items without custom icons

### 6.2 Phase 2: Icon Generation

1. **AI Generation Pipeline**
   - Create management command: `python manage.py generate_icons`
   - Integrate DALL-E 3 API
   - Use lesson/passage titles as prompts

2. **Batch Processing**
   - Generate icons for all existing content
   - Store in GCS with proper structure

### 6.3 Phase 3: Mobile Integration

1. **iOS Updates**
   - Add AsyncImage for icon loading
   - Implement caching layer
   - Handle loading/error states

2. **Android Updates**
   - Add Coil/Glide for icon loading
   - Configure disk cache
   - Handle density variants

### 6.4 Phase 4: Optimization

1. **Performance**
   - Enable Cloud CDN
   - Monitor cache hit rates
   - Implement lazy loading

2. **Analytics**
   - Track icon load times
   - A/B test with/without icons

---

## 7. Extensibility Considerations

### 7.1 Future Content Platform

If Keuvi evolves into a content distribution platform:

- **Icon API**: Allow content creators to upload custom icons
- **Style Guide Enforcement**: Validate icons meet visual standards
- **Icon Templates**: Provide base templates for consistency
- **Automated Moderation**: Check icons for appropriateness

### 7.2 Animation Support (Future)

Duolingo uses animated icons. Future considerations:

| Format | Support | File Size | Use Case |
|--------|---------|-----------|----------|
| Lottie | iOS + Android | Small | Complex animations |
| APNG | Limited | Medium | Simple animations |
| WebP animated | Good | Small | Simple animations |
| GIF | Universal | Large | Avoid |

### 7.3 Theming/Personalization

- Dark mode icon variants
- User-selectable color themes
- Seasonal icon variations (like Duolingo's seasonal app icons)

---

## 8. Security Considerations

### 8.1 Upload Validation

- Validate file types (only allow PNG, JPEG, WebP)
- Check file size limits (max 2MB per icon)
- Scan for malicious content
- Sanitize filenames

### 8.2 Access Control

- Icons should be publicly readable (no signed URLs needed)
- Upload restricted to admin/staff
- Consider rate limiting on upload endpoints

### 8.3 Content Moderation

If allowing user-generated icons:
- Implement image moderation (Google Vision API, AWS Rekognition)
- Manual review queue
- Report/flag functionality

---

## 9. Cost Estimates

### 9.1 AI Icon Generation

| Item | Cost | Quantity | Total |
|------|------|----------|-------|
| DALL-E 3 icons | $0.04/icon | ~200 lessons | $8 |
| DALL-E 3 icons | $0.04/icon | ~100 passages | $4 |
| DALL-E 3 icons | $0.04/icon | ~50 headers | $2 |
| Buffer for iterations | | | $10 |
| **Total Initial** | | | **~$25** |

### 9.2 Storage (GCS)

| Item | Size | Cost/GB/mo | Monthly |
|------|------|------------|---------|
| Icons (256x256 WebP, ~20KB each) | ~10MB | $0.02 | <$1 |
| Scaled variants | ~20MB | $0.02 | <$1 |

### 9.3 CDN (if enabled)

- Egress: ~$0.08-0.12/GB
- Expected usage: Minimal for icons (<$10/mo)

---

## 10. Handoff Summary

**1. Produced**: `docs/preparation/visual-enhancements-prep.md`

**2. Key context**:
- Duolingo uses bold colors, rounded shapes, and consistent illustration style
- Hybrid icon approach recommended (AI generation + manual upload)
- Data model changes: add `icon_url` and `icon_color` to content models
- GCS already configured; icons should be stored at 256x256 WebP

**3. Areas of uncertainty**:
- Exact DALL-E prompt tuning may require iteration
- Whether to implement on-the-fly resizing now or later
- Scope of mobile app changes (depends on current implementation)

**4. Open questions**:
- Should we auto-generate icons for all existing content immediately?
- What default icons to use for content without custom icons?
- Priority order for model updates (Lesson first? All at once?)

---

*Research complete. Ready for handoff to Architect phase.*
