#!/usr/bin/env python3
"""Build a single-file playable ONE CAREER.

game/index.html loads the engine with <script src="vendor/phaser.min.js">, which
keeps the source readable and the diff small. That file cannot be opened on its
own, so this inlines the engine and writes game/one-career.html — the build you
hand to someone who just wants to play.
"""
import io, os, sys, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "game", "index.html")
OUT = os.path.join(ROOT, "game", "one-career.html")
ENGINES = [
    ("vendor/phaser.min.js", "Phaser 3.80.1 — https://phaser.io — MIT"),
    ("vendor/three.min.js", "three.js r128 — https://threejs.org — MIT"),
]

def main():
    html = io.open(SRC, encoding="utf-8").read()
    for rel, label in ENGINES:
        tag = '<script src="%s"></script>' % rel
        if tag not in html:
            sys.exit("build: the vendor script tag for %s is not in game/index.html" % rel)
        engine = io.open(os.path.join(ROOT, "game", rel), encoding="utf-8").read()
        # </script> inside the engine would close our tag early
        engine = engine.replace("</script>", "<\\/script>")
        html = html.replace(tag, "<script>\n/* %s */\n" % label + engine + "\n</script>")
    # the manifest and icon live next to index.html; a standalone file has neither
    html = re.sub(r'\n\s*<link rel="manifest"[^>]*>', "", html)
    io.open(OUT, "w", encoding="utf-8").write(html)
    kb = os.path.getsize(OUT) / 1024
    print("built %s  (%.0f KB)" % (os.path.relpath(OUT, ROOT), kb))

if __name__ == "__main__":
    main()
