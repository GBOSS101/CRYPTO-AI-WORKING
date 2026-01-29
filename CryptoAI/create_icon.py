"""
Create CryptoAI application icon
Generates a .ico file for the Windows executable
"""
from PIL import Image, ImageDraw, ImageFont
import os


def create_crypto_icon():
    """Create a professional-looking crypto icon"""
    
    # Icon sizes for .ico file (Windows requires multiple sizes)
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    
    for size in sizes:
        # Create image with transparency
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Calculate dimensions
        padding = size // 8
        center = size // 2
        
        # Draw outer circle (gold gradient effect)
        for i in range(3):
            offset = i * (size // 32 + 1)
            color_val = 255 - (i * 30)
            draw.ellipse(
                [padding + offset, padding + offset, 
                 size - padding - offset, size - padding - offset],
                fill=(color_val, int(color_val * 0.84), 0, 255),
                outline=(184, 134, 11, 255),
                width=max(1, size // 32)
            )
        
        # Draw inner highlight (3D effect)
        highlight_size = size // 3
        draw.ellipse(
            [padding + size // 6, padding + size // 8,
             padding + size // 6 + highlight_size, padding + size // 8 + highlight_size // 2],
            fill=(255, 255, 200, 100)
        )
        
        # Draw Bitcoin-style "₿" or "$" symbol
        try:
            # Try to use a font
            font_size = size // 2
            font = ImageFont.truetype("arial.ttf", font_size)
            symbol = "$"
        except:
            font = ImageFont.load_default()
            symbol = "$"
        
        # Get text size for centering
        bbox = draw.textbbox((0, 0), symbol, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Draw symbol with shadow
        shadow_offset = max(1, size // 32)
        text_x = center - text_width // 2
        text_y = center - text_height // 2 - size // 16
        
        # Shadow
        draw.text((text_x + shadow_offset, text_y + shadow_offset), 
                  symbol, fill=(139, 90, 0, 200), font=font)
        # Main text
        draw.text((text_x, text_y), 
                  symbol, fill=(101, 67, 33, 255), font=font)
        
        # Add "AI" text at bottom for larger sizes
        if size >= 64:
            try:
                ai_font_size = size // 6
                ai_font = ImageFont.truetype("arial.ttf", ai_font_size)
            except:
                ai_font = font
            
            ai_bbox = draw.textbbox((0, 0), "AI", font=ai_font)
            ai_width = ai_bbox[2] - ai_bbox[0]
            ai_x = center - ai_width // 2
            ai_y = size - padding - ai_font_size - size // 16
            
            draw.text((ai_x, ai_y), "AI", fill=(101, 67, 33, 255), font=ai_font)
        
        images.append(img)
    
    # Save as .ico file
    icon_path = os.path.join(os.path.dirname(__file__), 'cryptoai.ico')
    
    # Save the largest image first, then others
    images[-1].save(
        icon_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1]
    )
    
    print(f"✓ Icon created: {icon_path}")
    return icon_path


def create_simple_icon():
    """Fallback: Create a simple icon if PIL features limited"""
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Simple gold circle
    padding = 20
    draw.ellipse([padding, padding, size-padding, size-padding], 
                 fill=(255, 215, 0, 255), 
                 outline=(184, 134, 11, 255), 
                 width=8)
    
    # Simple $ text
    draw.text((size//2 - 40, size//2 - 60), "$", fill=(139, 90, 0, 255))
    
    icon_path = os.path.join(os.path.dirname(__file__), 'cryptoai.ico')
    img.save(icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    
    print(f"✓ Simple icon created: {icon_path}")
    return icon_path


if __name__ == '__main__':
    try:
        create_crypto_icon()
    except Exception as e:
        print(f"⚠️ Advanced icon failed: {e}")
        print("Creating simple icon instead...")
        create_simple_icon()
