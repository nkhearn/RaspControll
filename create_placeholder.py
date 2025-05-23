from PIL import Image, ImageDraw, ImageFont

def create_placeholder_image(filename="static/images/placeholder_camera.png", width=640, height=480):
    img = Image.new('RGB', (width, height), color = (128, 128, 128)) # Gray background
    d = ImageDraw.Draw(img)
    
    try:
        # Attempt to load a default font, fallback if not found
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()

    text = "Placeholder Pinout Diagram"
    text_bbox = d.textbbox((0,0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (width - text_width) / 2
    y = (height - text_height) / 2
    
    d.text((x, y), text, fill=(255,255,255), font=font) # White text
    img.save(filename)
    print(f"Image {filename} created successfully.")

if __name__ == '__main__':
    # Generate the camera placeholder by default
    # create_placeholder_image() 
    # For this task, generate the pinout placeholder
    create_placeholder_image(filename="static/images/placeholder_pinout.png", width=800, height=600)
