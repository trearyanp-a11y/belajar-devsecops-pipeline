"""Render the exam diagram. Optional documentation dependency: Pillow."""

from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
image = Image.new("RGB", (2560, 1940), "#f5f7fb")
draw = ImageDraw.Draw(image)
INK = "#172b46"


def font(size):
    """Use an available system font for readable exported labels."""
    for name in ("C:/Windows/Fonts/segoeui.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default(size=size)


def text(x, y, value, size=28, fill=INK):
    """Draw explicit line breaks with consistent spacing."""
    draw.multiline_text((x, y), value, font=font(size), fill=fill, spacing=9)


def box(rect, title, detail, fill="#ffffff"):
    """Draw a labeled architecture component."""
    draw.rounded_rectangle(rect, radius=18, fill=fill, outline="#bfd0e3", width=2)
    x, y, _, _ = rect
    text(x + 22, y + 17, title, 30)
    text(x + 22, y + 61, detail, 24)


def arrow(points, fill="#526983", width=5):
    """Draw an orthogonal connector and its final arrowhead."""
    draw.line(points, fill=fill, width=width, joint="curve")
    x, y = points[-1]
    px, py = points[-2]
    if abs(x - px) >= abs(y - py):
        direction = 1 if x > px else -1
        triangle = [(x, y), (x - 16 * direction, y - 9), (x - 16 * direction, y + 9)]
    else:
        direction = 1 if y > py else -1
        triangle = [(x, y), (x - 9, y - 16 * direction), (x + 9, y - 16 * direction)]
    draw.polygon(triangle, fill=fill)


text(90, 45, "DEVSECOPS CI/CD  |  LOGIN FLASK", 53)
text(92, 119, "GitHub Actions -> VMware Ubuntu -> K3s  |  image hasil scan dipakai langsung", 29)
draw.rounded_rectangle((65, 185, 2495, 940), radius=24, fill="#edf3fc")
text(95, 208, "01  PIPELINE: EMPAT GATE PARALEL, SATU IMAGE DEPLOYMENT", 30)
box((105, 315, 535, 440), "Developer Windows", "Edit -> commit -> push", "#fff4d9")
box((105, 530, 535, 690), "GitHub Actions", "Push main/master atau manual\nPR: CI saja, deploy skipped", "#fff4d9")
arrow([(320, 440), (320, 530)])
gates = [("Semgrep", "SAST kode"), ("Pylint + tests", "Minimal 9.0 + regresi"),
         ("pip-audit", "Dependensi terkunci"), ("Trivy filesystem", "HIGH / CRITICAL")]
for index, (title, detail) in enumerate(gates):
    y = 290 + index * 145
    box((725, y, 1195, y + 115), title, detail, "#eee8ff")
    arrow([(535, 605), (625, 605), (625, y + 58), (725, y + 58)])
    arrow([(1195, y + 58), (1280, y + 58), (1280, 470), (1390, 470)])
box((1390, 365, 1845, 555), "Build + Trivy image", "Build satu kali, tag SHA\nCRITICAL, ignore-unfixed\nHarus lolos untuk deploy", "#dff3e9")
box((1990, 365, 2445, 555), "Artifact pada run sama", "image.tar + SHA256\nImage tidak dibangun ulang", "#dff3e9")
arrow([(1845, 470), (1990, 470)])
box((1390, 730, 1845, 860), "Gate gagal", "Build/deploy dilewati", "#ffe5e5")
arrow([(1280, 660), (1280, 795), (1390, 795)], "#be4545")
arrow([(1610, 555), (1610, 730)], "#be4545")
text(1920, 705, "LOLOS -> kirim artifact", 27, "#176c50")
text(1920, 750, "GAGAL -> pertahankan\naplikasi versi sebelumnya", 25, "#a34040")

draw.rounded_rectangle((560, 1040, 2495, 1830), radius=24, fill="#edf7f1",
                       outline="#8ab69a", width=3)
text(590, 1060, "02  VM UBUNTU / NODE yan  |  192.168.15.151  |  VMware NAT VMnet8", 29)
box((655, 1150, 1110, 1300), "Runner yan", "Download + verifikasi SHA256\nUser yan / self-hosted", "#ffffff")
box((1285, 1150, 1740, 1300), "containerd K3s", "Import artifact image\nTanpa docker build ulang", "#ffffff")
box((1915, 1150, 2370, 1300), "Deployment flask-app", "Tag SHA -> rollout status\n2 replika, UID 1000", "#ffffff")
arrow([(2210, 555), (2210, 985), (530, 985), (530, 1125), (880, 1125), (880, 1150)])
arrow([(1110, 1220), (1285, 1220)])
arrow([(1740, 1220), (1915, 1220)])
box((80, 1430, 475, 1585), "Browser Windows", "VMnet8: 192.168.15.1\nHTTP ke VM:30050", "#fff4d9")
box((655, 1430, 1110, 1585), "flask-service", "NodePort 30050 -> 5000\nClusterIP: 10.43.187.238", "#e0ecff")
box((1285, 1380, 1740, 1520), "Pod Flask 1", "Gunicorn :5000\nReady /health; live /live", "#ffffff")
box((1285, 1610, 1740, 1750), "Pod Flask 2", "Gunicorn :5000\nReady /health; live /live", "#ffffff")
box((1915, 1500, 2370, 1680), "PVC flask-pvc", "1 GiB local-path / RWO\n/data/users.db bersama\nPassword disimpan hash", "#dcf1df")
arrow([(475, 1500), (655, 1500)])
arrow([(1110, 1500), (1195, 1500), (1195, 1450), (1285, 1450)])
arrow([(1110, 1500), (1195, 1500), (1195, 1680), (1285, 1680)])
arrow([(2140, 1300), (2140, 1340), (1510, 1340), (1510, 1380)])
arrow([(2370, 1220), (2430, 1220), (2430, 1785), (1510, 1785), (1510, 1750)])
arrow([(1740, 1450), (1830, 1450), (1830, 1550), (1915, 1550)])
arrow([(1740, 1680), (1830, 1680), (1830, 1620), (1915, 1620)])
text(95, 1870, "Verifikasi: HTTP 200 + DB ready + /about.revision sesuai SHA  |  Satu VM, bukan HA antar-node", 28)
image.save(ROOT / "diagram_pipeline.jpg", quality=95, subsampling=0)
desktop = Path.home() / "Desktop"
if desktop.is_dir():
    shutil.copyfile(ROOT / "diagram_pipeline.jpg", desktop / "diagram_pipeline.jpg")
print(ROOT / "diagram_pipeline.jpg")
