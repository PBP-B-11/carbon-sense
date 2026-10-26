from hashlib import sha256

from django.conf import settings


def tracker_asset_version():
    #Ubah URL JavaScript ketika isinya berubah agar browser tidak memakai skrip lama.
    digest = sha256()
    scripts = settings.BASE_DIR / "static" / "js"
    for script in sorted(scripts.glob("tracker*.js")):
        digest.update(script.name.encode("utf-8"))
        digest.update(script.read_bytes())
    return digest.hexdigest()[:12]
