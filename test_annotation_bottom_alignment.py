#!/usr/bin/env python3
"""
Test script for annotation bottom alignment feature.

This script tests that annotations are positioned with their BOTTOM edge
aligned to the defect location, rather than their CENTER.
"""

from PIL import Image, ImageDraw
import os
import sys

def create_test_image_with_marker(width, height, defect_x, defect_y, marker_color='red'):
    """Create a test image with a marker at the defect position."""
    # Create white background
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Draw a small red cross at the exact defect position to verify alignment
    marker_size = 5
    draw.line([(defect_x - marker_size, defect_y), (defect_x + marker_size, defect_y)], 
              fill=marker_color, width=2)
    draw.line([(defect_x, defect_y - marker_size), (defect_x, defect_y + marker_size)], 
              fill=marker_color, width=2)
    
    # Draw a horizontal reference line through the defect position
    draw.line([(0, defect_y), (width, defect_y)], fill='lightgray', width=1)
    
    # Add coordinate text
    draw.text((10, 10), f"Defect position: ({defect_x}, {defect_y})", fill='black')
    draw.text((10, 30), "Red cross marks defect location", fill='red')
    draw.text((10, 50), "Gray line shows Y coordinate", fill='gray')
    draw.text((10, 70), "Annotation BOTTOM should align with red cross", fill='blue')
    
    return image

def test_annotation_positioning():
    """Test the annotation bottom alignment feature."""
    print("=" * 80)
    print("Testing Annotation Bottom Alignment Feature")
    print("=" * 80)
    
    # Test configuration
    test_cases = [
        {
            "name": "Center Position",
            "image_size": (800, 600),
            "defect_pos": (400, 300),
            "description": "Annotation in the center of the image"
        },
        {
            "name": "Top Position",
            "image_size": (800, 600),
            "defect_pos": (400, 150),
            "description": "Annotation near the top (tests extension feature)"
        },
        {
            "name": "Bottom Position",
            "image_size": (800, 600),
            "defect_pos": (400, 500),
            "description": "Annotation near the bottom"
        },
    ]
    
    output_dir = "test_output_bottom_alignment"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nCreating test images in: {output_dir}/")
    print("-" * 80)
    
    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        size = test_case["image_size"]
        pos = test_case["defect_pos"]
        desc = test_case["description"]
        
        print(f"\nTest Case {i}: {name}")
        print(f"  Description: {desc}")
        print(f"  Image Size: {size[0]}x{size[1]}")
        print(f"  Defect Position: ({pos[0]}, {pos[1]})")
        
        # Create test image
        image = create_test_image_with_marker(size[0], size[1], pos[0], pos[1])
        
        # Save test image
        filename = f"test_{i}_{name.lower().replace(' ', '_')}_reference.png"
        output_path = os.path.join(output_dir, filename)
        image.save(output_path)
        print(f"  ✓ Saved reference image: {filename}")
    
    print("\n" + "=" * 80)
    print("Test Image Generation Complete")
    print("=" * 80)
    print("\nInstructions:")
    print("1. Open the ortho_annotation_system_v7.py application")
    print("2. Load each test image from the test_output_bottom_alignment folder")
    print("3. Add an annotation at the red cross marker position")
    print("4. Save the project to generate individual overview images")
    print("5. Check the generated images in '全体図位置フォルダ'")
    print("6. Verify that:")
    print("   - The annotation's BOTTOM edge aligns with the red cross marker")
    print("   - The annotation appears to 'point down' at the defect location")
    print("   - The annotation's tip/top is clearly above the defect position")
    print("\n" + "=" * 80)

def verify_implementation():
    """Verify that the implementation changes are present in the code."""
    print("\n" + "=" * 80)
    print("Verifying Implementation Changes")
    print("=" * 80)
    
    code_file = "ortho_annotation_system_v7.py"
    
    if not os.path.exists(code_file):
        print(f"❌ ERROR: {code_file} not found!")
        return False
    
    with open(code_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for key implementation markers
    checks = [
        ("defect_y variable", "defect_y = annotation[\"y\"] + top_offset"),
        ("Height estimation logic", "# アノテーションの高さを事前計算"),
        ("Bottom alignment calculation", "annotation_y = defect_y - estimated_height / 2"),
        ("Updated draw call", "annotation_y,\n                    defect_type,"),
    ]
    
    all_passed = True
    for check_name, check_string in checks:
        if check_string in content:
            print(f"✓ Found: {check_name}")
        else:
            print(f"❌ Missing: {check_name}")
            all_passed = False
    
    print("=" * 80)
    if all_passed:
        print("✓ All implementation changes verified successfully!")
    else:
        print("❌ Some implementation changes are missing!")
    
    return all_passed

if __name__ == "__main__":
    # Verify implementation first
    implementation_ok = verify_implementation()
    
    if not implementation_ok:
        print("\n⚠️  WARNING: Implementation verification failed!")
        print("The test will continue, but results may not be as expected.\n")
        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("Test cancelled.")
            sys.exit(1)
    
    # Run the test
    test_annotation_positioning()
    
    print("\nTest script completed successfully!")
