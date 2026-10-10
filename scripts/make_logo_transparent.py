import os
from PIL import Image

src_path = r'd:\SIGE\frontend\img\logo-sige.jpg'
dest_path = r'd:\SIGE\frontend\img\logo-sige.png'

if os.path.exists(src_path):
    img = Image.open(src_path).convert('RGBA')
    datas = img.getdata()
    
    # Flood-fill or corner-based transparency so white details inside the book aren't lost
    # We want outer corners and background to be transparent
    # Let's inspect: book pages are white, but they are inside the dark blue squircle!
    # A simple flood fill from (0,0) or outer boundary transparent:
    from collections import deque
    
    w, h = img.size
    pixels = img.load()
    
    visited = set()
    queue = deque([(0, 0), (w-1, 0), (0, h-1), (w-1, h-1)])
    
    # Outer white background flood-fill
    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        visited.add((x, y)
        )
        r, g, b, a = pixels[x, y]
        # If it is light / background (r > 240, g > 240, b > 240)
        if r > 235 and g > 235 and b > 235:
            pixels[x, y] = (255, 255, 255, 0)
            for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    queue.append((nx, ny))
                    
    img.save(dest_path, 'PNG')
    print('Transparent logo-sige.png created successfully! Outer white background removed while preserving white book inside the squircle.')
