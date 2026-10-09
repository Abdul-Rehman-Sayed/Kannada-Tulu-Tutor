import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_DIR = os.path.join(BASE, "data", "images")
CREDITS = os.path.join(IMAGE_DIR, "CREDITS.csv")

API = "https://commons.wikimedia.org/w/api.php"
UA = ("KannadaTuluTutor/1.0 "
      "(https://github.com/Abdul-Rehman-Sayed/Major-Project-Attempt-2) python-urllib")

CARD_W, CARD_H = 640, 480
SOURCE_WIDTH = 1280
REQUEST_PAUSE = 0.5

PHOTOS = {
    "W001.jpg": "File:Mother and Child at Village of West Bengal,India.jpg",
    "W002.jpg": "File:Father and Daughter - Sundarbans District - South of Kolkata - India (12355917333).jpg",
    "W003.jpg": "File:Big brother holding little brother's hand walking home from school, Shiraz, Iran (15515926721).jpg",
    "W004.jpg": "File:Brother sister love.jpg",
    "W005.jpg": "File:Smiling little boy of Laos.jpg",
    "W006.jpg": "File:Smiling little girl Mounica.jpg",
    "W007.jpg": "File:Smiling Baby.jpg",
    "W008.jpg": "File:Grandpa Smile.jpg",
    "W009.jpg": "File:Grandmother and daughter.jpg",
    "W010.jpg": "File:Good Old School Friends (Unsplash).jpg",
    "W011.jpg": "File:Cow near Bhopal India 01.jpg",
    "W012.jpg": "File:Indian pariah dog -'Shanu' in village Ghel, District Fatehgarh Sahib, Punjab.jpg",
    "W013.jpg": "File:Cat August 2010-4.jpg",
    "W014.jpg": "File:Elephas maximus (Bandipur).jpg",
    "W015.jpg": "File:Humayun, Marwari Stallion of Virendra Kankariya.jpg",
    "W016.jpg": "File:Asian water buffalo (Bubalus bubalis) Yala.jpg",
    "W017.jpg": "File:Swaledale Sheep, Lake District, England - June 2009.jpg",
    "W018.jpg": "File:Mouse white background.jpg",
    "W019.jpg": "File:Carassius wild golden fish 2013 G1.jpg",
    "W020.jpg": "File:House sparrow male in Prospect Park (53532).jpg",
    "W021.jpg": "File:Hen with chicks, Raisen district, MP, India.jpg",
    "W022.jpg": "File:Bengal tiger (Panthera tigris tigris) female 3 crop.jpg",
    "W023.jpg": "File:Glass-of-water.jpg",
    "W025.jpg": "File:Flaming wood.JPG",
    "W026.jpg": "File:Mumbai-rains.jpg",
    "W027.jpg": "File:Blue sky and sun.png",
    "W028.jpg": "File:FullMoon2010.jpg",
    "W029.jpg": "File:Night Sky Stars Trees 02.jpg",
    "W030.jpg": "File:Usamljeni jasen - panoramio (cropped).jpg",
    "W031.jpg": "File:(MHNT) Hibiscus moscheutos - Red swamp rose-mallow flower - Les Martels, Giroussens Tarn.jpg",
    "W032.jpg": "File:Lisc lipy.jpg",
    "W033.jpg": "File:Dry Forest SH-80 K Gudi BR Hills Karnataka May24 A7CR 00062.jpg",
    "W034.jpg": "File:Sea Waves of western Coast.jpg",
    "W035.jpg": "File:A bowl of rice.jpg",
    "W036.jpg": "File:Glass of Milk (33657535532).jpg",
    "W038.jpg": "File:A basket of fruits.jpg",
    "W039.jpg": "File:Bananas on black background 02.jpg",
    "W040.jpg": "File:Curd in a traditional Manipuri earthen pot.JPG",
    "W041.jpg": "File:Würfelzucker -- 2018 -- 3564.jpg",
    "W042.jpg": "File:2020-05-08 19 34 28 Chapati being made in a pan in the Franklin Farm section of Oak Hill, Fairfax County, Virginia.jpg",
    "W044.jpg": "File:Close-up photograph of the eye of a baby with reflection of the scene in the pupil.jpg",
    "W045.jpg": "File:Human right ear (cropped).jpg",
    "W048.jpg": "File:Right Hand Palm.png",
    "W049.jpg": "File:People walking on the street in Nairobi, Kenya.jpg",
    "W050.jpg": "File:06-10-06smile.jpg",
    "W067.jpg": "File:Lowry and Denis Piers House, Fontainhas - 19th-20th century (4276312842).jpg",
    "W068.jpg": "File:Goa, India -- Traditional-style wooden door.jpg",
    "W069.jpg": "File:Set of fourteen side chairs MET DP110780.jpg",
    "W070.jpg": "File:An Earthen Lamp (Diya).jpg",
    "W071.jpg": "File:Old Books 01.JPG",
    "W072.jpg": "File:Govt Primary School Ramgarh, Punjab, India.jpg",
    "W073.jpg": "File:Pencils hb.jpg",
    "W074.jpg": "File:Поезд на фоне горы Шатрище. Воронежская область.jpg",
    "W075.jpg": "File:School bus, Indore.jpg",
    "W076.jpg": "File:Air India 787-8 (VT-ANB).jpg",
    "W077.jpg": "File:Mangos - single and halved.jpg",
    "W078.jpg": "File:Red Apple.jpg",
    "W079.jpg": "File:Oranges - whole-halved-segment.jpg",
    "W080.jpg": "File:Green Grape 3.jpg",
    "W081.jpg": "File:Watermelon.jpg",
    "W082.jpg": "File:Russet potato cultivar with sprouts.jpg",
    "W083.jpg": "File:Solanum melongena 24 08 2012 (1).JPG",
    "W084.jpg": "File:Okra Lady`s Finger.jpg",
    "W085.jpg": "File:Masala dosa 01.jpg",
    "W086.jpg": "File:Idli Sambar Food by Ms Ujwala Kasambe DSCN9744 (2).jpg",
    "W087.jpg": "File:Honey dripper load.jpg",
    "W088.jpg": "File:Butter block.JPG",
    "W089.jpg": "File:Bonnet Macaque HD.jpg",
    "W090.jpg": "File:Rose-ringed parakeet (Psittacula krameri borealis) male Jaipur.jpg",
    "W091.jpg": "File:Corvus splendens.jpg",
    "W092.jpg": "File:023 Indian peafowl in Jim Corbett National Park Photo by Giles Laurent.jpg",
    "W093.jpg": "File:Oryctolagus cuniculus Rcdo.jpg",
    "W094.jpg": "File:Funambulus palmarum (Bengaluru).jpg",
    "W095.jpg": "File:A child in India (cropped).jpg",
    "W096.jpg": "File:Girl with long black hair, rear view.jpg",
    "W097.jpg": "File:Index finger = to attention.JPG",
    "W098.jpg": "File:Cumulus clouds in Russia. img 058.jpg",
    "W099.jpg": "File:Kali River 620.JPG",
    "W100.jpg": "File:Cirrus uncinus clouds in the morning sky.jpg",
    "W101.jpg": "File:Five Pebbles.jpg",
    "W102.jpg": "File:Cozy bedroom with a large bed and simple decor in a modern home.jpg",
    "W103.jpg": "File:Fischerkirche (window), Born a. Darß.jpg",
    "W104.jpg": "File:Clock at the Malching S-Bahn station 02.jpg",
    "W105.jpg": "File:Just a soccer ball (34782492153).jpg",
    "W106.jpg": "File:Blue Business Shirt.jpg",
    "W107.jpg": "File:Woman with a Sparkler.jpg",
    "W108.jpg": "File:Audi e-tron (Edit1).jpg",
    "R001.jpg": "File:Namaste a greetngs gesture by a local lady while meeting whom she knew at Okhaldunga Nepal IMG 3068.jpg",
    "S005.jpg": "File:School on a rainy day.jpg",
    "S006.jpg": "File:A child reading a book by Pratham Books - Flickr - Pratham Books (2).jpg",
    "S007.jpg": "File:Sipahh - girl.jpg",
    "S008.jpg": "File:Boy drinks water from glass in a cozy home environment.jpg",
    "S009.jpg": "File:Mahima 2 years old Tamil child eating rice.jpg",
    "S010.jpg": "File:Child playing football.jpg",
    "S011.jpg": "File:School Girls in India.jpg",
    "S014.jpg": "File:Oma beim Vorlesen.jpg",
    "S016.jpg": "File:Spinning tire swing with child.jpg",
    "S017.jpg": "File:Cow milking, rear view, near Mehsana, Gujarat, India.jpg",
    "S018.jpg": "File:Dog guarding the door of his house.jpg",
    "S019.jpg": "File:Cute cats drinking milk.jpg",
    "S020.jpg": "File:Tropical Fish Swimming Underwater (46256605951).jpg",
    "S021.jpg": "File:Juvenile white-tailed tropicbird flying against blue sky (Niue).jpg",
    "S023.jpg": "File:006 Baby rhesus macaque in Jim Corbett National Park Photo by Giles Laurent.jpg",
    "S028.jpg": "File:Mangifera indica var. José.JPG",
}

FOCUS = {}


def _open(url, timeout=60):
    delay = 2.0
    for attempt in range(5):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception:
            if attempt == 4:
                raise
            time.sleep(delay)
            delay *= 2


def _strip_html(s):
    out, depth = [], 0
    for ch in s or "":
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return " ".join("".join(out).split())[:80]


def image_info(titles):
    params = {"action": "query", "titles": "|".join(titles), "prop": "imageinfo",
              "iiprop": "url|extmetadata", "iiurlwidth": SOURCE_WIDTH,
              "format": "json"}
    data = json.loads(_open(API + "?" + urllib.parse.urlencode(params)))
    query = data.get("query") or {}
    found = {}
    for page in query.get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        found[page.get("title")] = {
            "url": info.get("thumburl") or info.get("url"),
            "licence": (meta.get("LicenseShortName") or {}).get("value", ""),
            "author": _strip_html((meta.get("Artist") or {}).get("value", "")),
        }
    for norm in query.get("normalized", []):
        if norm["to"] in found:
            found[norm["from"]] = found[norm["to"]]
    return found


def card(raw, focus=0.45):
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    if img.width / img.height >= 1.15:
        return ImageOps.fit(img, (CARD_W, CARD_H), Image.LANCZOS, centering=(0.5, focus))
    ground = ImageOps.fit(img, (CARD_W, CARD_H), Image.LANCZOS)
    ground = ground.filter(ImageFilter.GaussianBlur(28))
    ground = Image.blend(ground, Image.new("RGB", ground.size, (245, 243, 236)), 0.35)
    img.thumbnail((CARD_W, CARD_H), Image.LANCZOS)
    ground.paste(img, ((CARD_W - img.width) // 2, (CARD_H - img.height) // 2))
    return ground


def load_credits():
    if not os.path.exists(CREDITS):
        return {}
    with open(CREDITS, encoding="utf-8-sig", newline="") as f:
        return {r["image_file"]: r for r in csv.DictReader(f)}


def write_credits(credits):
    with open(CREDITS, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["image_file", "title", "licence",
                                          "author", "source"])
        w.writeheader()
        for name in sorted(credits):
            if name in PHOTOS:
                w.writerow({k: credits[name].get(k, "") for k in w.fieldnames})


def fetch(names, force=False):
    credits = load_credits()
    todo = [n for n in names
            if force or n not in credits or "title" not in credits[n]
            or not os.path.exists(os.path.join(IMAGE_DIR, n))]
    failed = []
    for i in range(0, len(todo), 20):
        batch = todo[i:i + 20]
        info = image_info([PHOTOS[n] for n in batch])
        for name in batch:
            title = PHOTOS[name]
            meta = info.get(title)
            if not meta or not meta["url"]:
                failed.append((name, "not found on Commons"))
                continue
            try:
                dest = os.path.join(IMAGE_DIR, name)
                card(_open(meta["url"]), FOCUS.get(name, 0.45)).save(
                    dest + ".part", "JPEG", quality=85, optimize=True, progressive=True)
                os.replace(dest + ".part", dest)
            except Exception as e:
                failed.append((name, str(e)))
                continue
            credits[name] = {
                "image_file": name, "title": title, "licence": meta["licence"],
                "author": meta["author"] or "unknown",
                "source": "https://commons.wikimedia.org/wiki/"
                          + urllib.parse.quote(title.replace(" ", "_")),
            }
            print(f"  {name:9} {meta['licence']:14} {title[5:70]}")
            time.sleep(REQUEST_PAUSE)
    write_credits(credits)
    return failed


def contact_sheet(names):
    font = ImageFont.load_default()
    for path in (r"C:\Windows\Fonts\arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            font = ImageFont.truetype(path, 15)
            break
    have = [n for n in names if os.path.exists(os.path.join(IMAGE_DIR, n))]
    cols, tw, th, cap, per_page = 6, 240, 180, 22, 42
    for page in range((len(have) + per_page - 1) // per_page):
        chunk = have[page * per_page:(page + 1) * per_page]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * (th + cap)), "white")
        draw = ImageDraw.Draw(sheet)
        for i, name in enumerate(chunk):
            x, y = (i % cols) * tw, (i // cols) * (th + cap)
            im = Image.open(os.path.join(IMAGE_DIR, name)).convert("RGB")
            sheet.paste(im.resize((tw - 4, th - 4)), (x + 2, y + 2))
            draw.text((x + 4, y + th), name[:-4], fill="black", font=font)
        out = os.path.join(BASE, "data", f"contact_sheet_{page + 1}.jpg")
        sheet.save(out, "JPEG", quality=82)
        print(f"contact sheet -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="fetch every photograph again")
    ap.add_argument("--only", default="", help="comma-separated image files, e.g. W001.jpg")
    ap.add_argument("--contact-sheet", action="store_true", help="build a montage and exit")
    args = ap.parse_args()

    os.makedirs(IMAGE_DIR, exist_ok=True)
    names = list(PHOTOS)
    if args.only:
        wanted = {n.strip() for n in args.only.split(",")}
        names = [n for n in names if n in wanted]
    if args.contact_sheet:
        contact_sheet(names)
        return

    failed = fetch(names, args.force)
    print(f"\n{len(names) - len(failed)} of {len(names)} photographs in place; "
          f"credits in {CREDITS}")
    for name, why in failed:
        print(f"  FAILED {name}: {why}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
