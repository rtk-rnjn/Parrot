from PIL import Image, ImageDraw


def create_ludo_board(cell_size=40):
    # Standard Ludo board is a 15x15 grid
    grid_size = 15
    width = grid_size * cell_size
    height = grid_size * cell_size

    # Create a white canvas
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Colors
    RED = "#FF3333"
    GREEN = "#33FF33"
    YELLOW = "#FFFF33"
    BLUE = "#3366FF"
    BLACK = "#000000"
    WHITE = "#FFFFFF"
    GRAY = "#D3D3D3"

    # Helper function to draw a cell
    def draw_cell(r, c, fill_color=WHITE):
        x0, y0 = c * cell_size, r * cell_size
        x1, y1 = x0 + cell_size, y0 + cell_size
        draw.rectangle([x0, y0, x1, y1], fill=fill_color, outline=BLACK)

    # 1. Draw the basic cross path (3x6 rectangles on 4 sides)
    for r in range(15):
        for c in range(15):
            # Left and Right arms
            if 6 <= r <= 8 and (c < 6 or c > 8):
                draw_cell(r, c)
            # Top and Bottom arms
            elif 6 <= c <= 8 and (r < 6 or r > 8):
                draw_cell(r, c)

    # 2. Color Home Runs and Safe Zones
    # Red Path (Left)
    for c in range(1, 6):
        draw_cell(7, c, RED)
    draw_cell(6, 1, RED)  # Red Start
    draw_cell(8, 2, GRAY)  # Safe square

    # Green Path (Top)
    for r in range(1, 6):
        draw_cell(r, 7, GREEN)
    draw_cell(1, 8, GREEN)  # Green Start
    draw_cell(2, 6, GRAY)  # Safe square

    # Yellow Path (Right)
    for c in range(9, 14):
        draw_cell(7, c, YELLOW)
    draw_cell(8, 13, YELLOW)  # Yellow Start
    draw_cell(6, 12, GRAY)  # Safe square

    # Blue Path (Bottom)
    for r in range(9, 14):
        draw_cell(r, 7, BLUE)
    draw_cell(13, 6, BLUE)  # Blue Start
    draw_cell(12, 8, GRAY)  # Safe square

    # 3. Draw the 4 Home Bases
    def draw_home(start_r, start_c, color):
        # Main big box
        x0 = start_c * cell_size
        y0 = start_r * cell_size
        x1 = x0 + (6 * cell_size)
        y1 = y0 + (6 * cell_size)
        draw.rectangle([x0, y0, x1, y1], fill=color, outline=BLACK, width=2)

        # Inner white box
        ix0, iy0 = x0 + cell_size, y0 + cell_size
        ix1, iy1 = x1 - cell_size, y1 - cell_size
        draw.rectangle([ix0, iy0, ix1, iy1], fill=WHITE, outline=BLACK)

        # Draw 4 token spaces (circles)
        positions = [
            (ix0 + 0.5 * cell_size, iy0 + 0.5 * cell_size),
            (ix1 - 1.5 * cell_size, iy0 + 0.5 * cell_size),
            (ix0 + 0.5 * cell_size, iy1 - 1.5 * cell_size),
            (ix1 - 1.5 * cell_size, iy1 - 1.5 * cell_size),
        ]

        for px, py in positions:
            draw.ellipse([px, py, px + cell_size, py + cell_size], fill=color, outline=BLACK)

    draw_home(0, 0, RED)  # Top-Left
    draw_home(0, 9, GREEN)  # Top-Right
    draw_home(9, 9, YELLOW)  # Bottom-Right
    draw_home(9, 0, BLUE)  # Bottom-Left

    # 4. Draw the Center Home Triangles
    cx, cy = 7.5 * cell_size, 7.5 * cell_size

    # Coordinates for the center 3x3 square corners
    tl = (6 * cell_size, 6 * cell_size)
    tr = (9 * cell_size, 6 * cell_size)
    bl = (6 * cell_size, 9 * cell_size)
    br = (9 * cell_size, 9 * cell_size)

    # Red triangle (Left)
    draw.polygon([tl, (cx, cy), bl], fill=RED, outline=BLACK)
    # Green triangle (Top)
    draw.polygon([tl, (cx, cy), tr], fill=GREEN, outline=BLACK)
    # Yellow triangle (Right)
    draw.polygon([tr, (cx, cy), br], fill=YELLOW, outline=BLACK)
    # Blue triangle (Bottom)
    draw.polygon([bl, (cx, cy), br], fill=BLUE, outline=BLACK)

    # Save and show the image
    img.save("ludo_board.png")
    img.show()


if __name__ == "__main__":
    create_ludo_board(cell_size=40)
