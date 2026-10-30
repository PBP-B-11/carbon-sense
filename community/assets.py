import json
from hashlib import sha256

from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe

JS_DIR = "js/community"


def community_assets():
    """Versi skrip Community dan import map yang memberi versi itu ke setiap modul.

    `?v=` pada tag script tidak ikut ke file hasil `import`, jadi tanpa import map
    modul yang di-import tetap bisa berasal dari cache lama."""
    digest = sha256()
    scripts = sorted((settings.BASE_DIR / "static" / JS_DIR).glob("*.js"))
    for script in scripts:
        digest.update(script.name.encode("utf-8"))
        digest.update(script.read_bytes())
    version = digest.hexdigest()[:12]
    imports = {
        static(f"{JS_DIR}/{s.name}"): f"{static(f'{JS_DIR}/{s.name}')}?v={version}"
        for s in scripts
    }
    return {
        "js_version": version,
        "js_importmap": mark_safe(json.dumps({"imports": imports})),
    }
