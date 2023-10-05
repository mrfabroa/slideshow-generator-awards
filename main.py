import csv
import pathlib
import textwrap

from PIL import Image, ImageDraw, ImageFont

# Visual settings
WIDTH = 1920
HEIGHT = 1080
# BG_COLOR = "#212121"
BG_COLOR = "#000000"
PRIMARY_COLOR = "#ffffff"    # for student name
SECONDARY_COLOR = "#adadad"  # for achievements
PRIMARY_FONT_PATH = "fonts/Cambo-Regular.ttf"
SECONDARY_FONT_PATH = "fonts/ArialTh.ttf"

# Data
TSV_FILE_PATH = "data/STAGING - Master Grad List  - DATA - FINAL.tsv"
TABLE_FIELDS = "status student_id full_name first_name last_name ont_scholar honour_roll awards awards_prep certificat_prep not_ossd".split()

# Image paths
PHOTOS_BASE_DIR = pathlib.Path("images")
SCHOOL_LOGO_PATH = PHOTOS_BASE_DIR / "school_logo.png"

# The subdirectories in your photos base dir
# The topmost directories have the higher priority
PHOTO_DIRECTORIES = [
    "RETAKES",
    "ORIGINALS",
]

OUTPUT_PDF_FILENAME = "slideshow.pdf"


LEFT_MIDPOINT = int(WIDTH * 0.29)
RIGHT_MIDPOINT = int(WIDTH * (1-0.23))

def main():
    # READ TSV
    
    with open(TSV_FILE_PATH, "r") as f:
        read_tsv = csv.reader(f, delimiter="\t")
        data = list(read_tsv)[1:]
    
    students = []
    for row in data:
        if row[1] == "":
            print(f"ISSUE: Student ({row[2]}) has no student number.")
            continue

        student = {}
        for key, value in zip(TABLE_FIELDS, row):
            student[key] = value
        
        student["awards"] = [a.strip() for a in student["awards"].split(";") if a != ""]
        if student["ont_scholar"]:
            student["awards"] = ["Ontario Scholar"] + student["awards"]
        if student["honour_roll"]:
            student["awards"] = ["Honour Roll"] + student["awards"]
        students.append(student)
    
    # MATCH STUDENTS WITH PHOTOS
    students_by_id = dict((s["student_id"], s) for s in students)

    for subdir in PHOTO_DIRECTORIES:
        for file in pathlib.Path(PHOTOS_BASE_DIR / subdir).iterdir():
            if file.suffix.lower() == ".jpg":
                student_id = file.stem
                image_key_name = "image_file"
                try:
                    if image_key_name not in students_by_id[student_id].keys():
                        students_by_id[student_id][image_key_name] = file
                except KeyError:
                    print(f"ISSUE: The image '{file.as_posix()}' cannot be found in the student list.")

    for s in students:
        if "image_file" not in s.keys():
            print(f"ISSUE: Missing photo for {s['full_name']} ({s['student_id']}).")


    # CREATE SLIDES
    base_template = draw_base()

    ## CREATE NEW SLIDE
    slides = []
    # for s in (s for s in students if len(s["awards"]) > 0):  # awards only
    for s in students:
        new_slide = base_template.copy()
        name = f"{s['first_name']} {s['last_name']}"
        add_name(name, new_slide, has_awards=len(s["awards"]) > 0)
        add_achievements(s["awards"], new_slide)
        if "image_file" in s.keys():
            add_image(s["image_file"], new_slide)

        # new_slide.save('pil_img.png')
        slides.append(new_slide)

    slides[0].save(OUTPUT_PDF_FILENAME, save_all=True, append_images=slides[1:])


def draw_base():
    bg = Image.new("RGB", (WIDTH, HEIGHT), color=BG_COLOR)
    logo = Image.open(SCHOOL_LOGO_PATH)
    logo_side = logo.resize((int(logo.width*0.6), int(logo.height*0.6)))

    # SMALL LOGO
    small_logo = logo.resize((int(logo.width * 0.20), int(logo.height * 0.20)))
    left = LEFT_MIDPOINT - small_logo.width // 2
    top = 60
    right = left + small_logo.width
    bottom = top + small_logo.height
    bg.paste(small_logo, (left, top, right, bottom))

    # LOGO
    left = RIGHT_MIDPOINT - logo_side.width//2
    top = HEIGHT // 2 - logo_side.height // 2
    right = left + logo_side.width
    bottom = top + logo_side.height
    bg.paste(logo_side, (left, top, right, bottom))
    return bg


def add_image(image_file, slide: Image):
    image = Image.open(image_file)  # 0.2 ms

    # check for cache folder
    cache_path = pathlib.Path("images/cache")
    try:
        pathlib.Path.mkdir(cache_path)
    except FileExistsError:
        # already exists, move on
        pass
    
    # look for cached version of student photo, if not found create
    try:
        image = Image.open(cache_path / image_file.name)  
    except FileNotFoundError:
        # resize and save to cache
        h = int(HEIGHT * 0.9)
        ratio = h / image.height
        w = int(image.width * ratio)
        image = image.resize((w, h))  # 75 ms
        image.save(cache_path / image_file.name)

    # Place image
    left = RIGHT_MIDPOINT - image.width//2
    top = HEIGHT // 2 - image.height // 2
    right = left + image.width
    bottom = top + image.height
    slide.paste(image, (left, top, right, bottom))


def add_name(name_text, image, has_awards=False):
    draw = ImageDraw.Draw(image)
    name_text_height = int(HEIGHT * 0.13)

    while True:
        name_font = ImageFont.truetype(PRIMARY_FONT_PATH, name_text_height)
        w, h = draw.textsize(name_text, name_font)
        if w < WIDTH * 0.5:
            break
        name_text_height -= 1
            
    x = LEFT_MIDPOINT - (w//2)
    y = int(HEIGHT * 0.45 - (h//2))
    if has_awards:
        y = int(HEIGHT * 0.30 - (h//2))
    draw.text((x, y), name_text, font=name_font, fill=PRIMARY_COLOR)


def add_achievements(awards, image):
    if len(awards) == 0: return
    draw = ImageDraw.Draw(image)
    award_text_height = int(HEIGHT * 0.10)
    if len(awards) > 5:
        award_text_height = int(HEIGHT * 0.05)
        awards = ["\n".join(textwrap.wrap(text, width=60)) for text in awards]
        award_text = "\n".join(awards)
    else:
        awards = ["\n".join(textwrap.wrap(text, width=40)) for text in awards]
        award_text = "\n".join(awards)

    while True:
        award_font= ImageFont.truetype(SECONDARY_FONT_PATH, award_text_height)
        w, h = draw.textsize(award_text, award_font)
        if w < WIDTH * 0.45:
            break
        award_text_height -= 1
        
    x = LEFT_MIDPOINT - (w//2)
    y = int(HEIGHT * 0.6) - (h//2)
    draw.text((x, y), award_text, font=award_font, fill=SECONDARY_COLOR, spacing=HEIGHT * 0.03, align="center")


if __name__ == "__main__":
    main()