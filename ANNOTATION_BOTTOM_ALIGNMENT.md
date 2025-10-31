# Annotation Bottom Alignment Feature

## Overview

This document describes the annotation positioning logic change implemented to make annotations point downward at defect locations.

## Change Summary

**Previous Behavior**: Annotations were positioned with their CENTER aligned to the defect location.

**New Behavior**: Annotations are positioned with their BOTTOM edge aligned to the defect location, making the annotation appear to "point down" at the defect.

## Implementation Details

### Modified Method

**File**: `ortho_annotation_system_v7.py`  
**Method**: `save_individual_annotated_images()` (lines ~3836-3865)

### Key Changes

1. **Renamed Y coordinate variable for clarity**:
   ```python
   # Before:
   y = annotation["y"] + top_offset
   
   # After:
   defect_y = annotation["y"] + top_offset  # Clear intent: this is the defect position
   ```

2. **Added annotation height estimation**:
   ```python
   # Estimate the height of the annotation before drawing
   base_icon = self.load_annotation_icon(defect_type)
   if base_icon is not None:
       # Calculate icon height using same logic as draw_annotation_icon_on_image
       # ... (height calculation logic)
       estimated_height = max(1, int(round(icon_h * scale)))
   else:
       # For shapes without icons, use shape-specific height
       if shape in ["cross", "arrow", "rectangle"]:
           estimated_height = max(6, int(round(20 * overall_scale))) * 2
       elif shape == "circle":
           estimated_height = max(6, int(round(25 * overall_scale))) * 2
   ```

3. **Adjusted annotation Y position**:
   ```python
   # Calculate the Y position so the annotation's BOTTOM aligns with the defect
   annotation_y = defect_y - estimated_height / 2
   ```
   
   This shifts the annotation upward by half its height, so:
   - The annotation's bottom edge is at `defect_y`
   - The annotation's center is at `defect_y - estimated_height / 2`
   - The annotation's top is at `defect_y - estimated_height`

4. **Updated drawing calls**:
   ```python
   # Use annotation_y instead of y for all drawing operations
   self.draw_annotation_icon_on_image(..., annotation_y, ...)
   self._draw_id_label_on_image(..., annotation_y, ...)
   ```

## Visual Effect

### Before Change
```
        ┌─────┐
        │ ID1 │
        └──┬──┘
           │
     ──────●────── (defect position - annotation center)
           │
           │
```

### After Change
```
        ┌─────┐
        │ ID1 │
        └──┬──┘
           │
           │
           ▼
     ──────●────── (defect position - annotation bottom/tip)
```

## Height Estimation Logic

The implementation estimates annotation height differently for icons vs shapes:

### For Icons (SVG-based)
Uses the same calculation as `draw_annotation_icon_on_image()`:
1. Get base icon size
2. Calculate target edge size based on image dimensions and scale
3. Apply scaling to get final height
4. Ensures minimum size of 1 pixel

### For Shapes (Primitive Geometry)
Uses shape-specific formulas:
- **Cross**: `size * 2` where size = `max(6, int(round(20 * scale)))`
- **Arrow**: `size * 2` where size = `max(6, int(round(20 * scale)))`
- **Circle**: `radius * 2` where radius = `max(6, int(round(25 * scale)))`
- **Rectangle**: `size * 2` where size = `max(6, int(round(20 * scale)))`

## Interaction with Image Extension Feature

This feature works seamlessly with the image extension feature:

1. Image is extended with white background (top and bottom)
2. `defect_y` is calculated with `top_offset` included
3. `annotation_y` is calculated relative to `defect_y`
4. Result: Annotation bottom aligns perfectly with defect position in the extended image

## Testing

### Test Script

Run `test_annotation_bottom_alignment.py` to generate test images:

```bash
python3 test_annotation_bottom_alignment.py
```

This creates three test images with reference markers at different positions:
1. **Center Position**: Tests normal case
2. **Top Position**: Tests with image extension
3. **Bottom Position**: Tests lower boundary

### Manual Verification Steps

1. Load test images into the application
2. Add annotations at the red cross markers
3. Save the project
4. Check generated images in `全体図位置フォルダ`
5. Verify:
   - Annotation bottom edge aligns with red cross
   - Annotation appears to point downward
   - Annotation top is clearly above the defect position

### Verification Output

The test script verifies implementation by checking for:
- ✓ `defect_y` variable usage
- ✓ Height estimation logic
- ✓ Bottom alignment calculation
- ✓ Updated drawing calls with `annotation_y`

## Code Quality

### Advantages of This Implementation

1. **Maintains backward compatibility**: Only affects individual overview images
2. **Self-contained**: All logic in one method
3. **Reuses existing code**: Uses same height calculation as drawing methods
4. **Clear variable names**: `defect_y` vs `annotation_y` clarifies intent
5. **Well-commented**: Explains the purpose of each calculation

### Future Enhancements

Potential improvements (not currently implemented):
1. Add configuration option to choose alignment mode (center vs bottom)
2. Apply same logic to main canvas display
3. Support other alignment options (top, left, right)
4. Add visual indicator showing the exact defect point

## Related Features

This feature builds upon and works with:
1. **Individual Overview Image Generation**: Base functionality
2. **Image Extension Feature**: Prevents clipping of repositioned annotations
3. **RGBA to RGB Conversion**: Ensures JPEG compatibility
4. **Annotation Scaling**: Respects user-defined scale settings

## User Impact

### What Users Will Notice

- Annotations now "point at" the defect location
- The tip/top of the annotation indicates the exact defect position
- More intuitive visual representation of defect locations
- Better alignment when defects are at specific coordinates

### When This Applies

This positioning change applies ONLY to:
- Individual overview images generated in `全体図位置フォルダ`
- Saved during project save operation

This does NOT affect:
- Canvas display in the main application window
- Main annotated overview image (`全体図アノテーション.jpg`)
- Thermal/visible images

## Implementation Date

**Date**: 2025-10-31  
**Version**: ortho_annotation_system_v7.py

## Author Notes

This change was requested to improve the visual clarity of defect locations in individual overview images. The previous center-aligned positioning was ambiguous about the exact defect location, especially for large annotations or when multiple defects were nearby.

The bottom-aligned positioning makes it immediately clear where the defect is located, as the annotation's lowest point (or arrow tip) directly indicates the coordinate of interest.
