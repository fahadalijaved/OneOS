#!/usr/bin/env python3
"""Build a MysticGSI image from partition images already extracted (scripts/payload-stream.py).

MysticGSI's build takes a firmware archive and starts by extracting it into its work folder;
packing extracted images back into a tar for it doubles the disk they take (vivo's CN OTA:
about 9 GB). This runs the same build as `cli.py build <name> <archive>` with its defaults,
except that the extract step hard-links the images given instead (same filesystem, no copy).

Usage (from anywhere): mysticgsi/.venv/bin/python scripts/mysticgsi-from-images.py [--drop] [--type=TYPE] <name> <images dir> [partition,...]
--type is cli.py's --type (default auto). MysticGSI does not detect OriginOS by itself: vivo
images need --type=originos (patches/<sdk>/originos: the image's own init, no device overlays).
Partitions default to system, system_ext, product, odm (vendor is never merged into a GSI).
--drop deletes each partition image (both links) once it is unpacked: the build then needs room
for the trees and the image only (nothing later reads the images).
The image ends up in mysticgsi/out/<name>/, as with cli.py.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MYST = os.path.join(ROOT, "mysticgsi")


def main():
    args = sys.argv[1:]
    drop = "--drop" in args
    rom_type = next((a.split("=", 1)[1] for a in args if a.startswith("--type=")), "auto")
    args = [a for a in args if a != "--drop" and not a.startswith("--type=")]
    if len(args) not in (2, 3):
        sys.exit(__doc__)
    name, images = args[0], os.path.abspath(args[1])
    parts = args[2].split(",") if len(args) == 3 else ["system", "system_ext", "product", "odm"]
    os.chdir(MYST)
    sys.path.insert(0, MYST)
    import buildlock
    import cli
    import fsops
    import make
    import tools

    tools.check_environment(cli.erofs_tools(None))
    wt = make.RomPorter(name, "")
    rtype, _, rcustom = rom_type.partition(":")
    wt.rom_type = make.safe_name(rtype, "rom_type")
    wt.override_rom_type = make.safe_name(rcustom or "default", "rom_custom")
    wt.logger = cli.ConsoleLogger()
    wt.debloat = True
    wt.no_merge = False
    wt.erofs_format = None
    wt.avb_key = None

    def from_images(_archive):
        wt.images_dir = os.path.join(wt.work_dir, "images")
        fsops.rmrf(wt.images_dir)
        os.makedirs(wt.images_dir)
        wt.image_files.clear()
        for part in parts:
            src = os.path.join(images, f"{part}.img")
            if part not in make.RomPorter.PARTITION_NAMES or not os.path.isfile(src):
                wt.log(f"{part}.img: not used ({'not a partition MysticGSI takes' if os.path.isfile(src) else 'missing'})")
                continue
            dst = os.path.join(wt.images_dir, f"{part}.img")
            os.link(src, dst)
            wt.image_files[part] = dst
            wt.log(f"Linked {src} ({os.path.getsize(src) >> 20} MB)")
        return 0 if "system" in wt.image_files else -1

    wt._extract_firmware = from_images
    unpack = wt._unpack_partitions

    def unpack_then_drop():
        rc = unpack()
        if rc == 0 and drop:
            for part, path in list(wt.image_files.items()):
                for p in (path, os.path.join(images, f"{part}.img")):
                    if os.path.exists(p):
                        os.remove(p)
                wt.log(f"Dropped {part}.img (unpacked)")
        return rc

    wt._unpack_partitions = unpack_then_drop
    with buildlock.hold(on_busy=cli.wait_for_lock):
        rc = wt.build("extracted-images")
        if rc != 0:
            sys.exit(f"build failed ({rc})")
        cli.append_list(wt)
    print()
    print(cli.summarize(wt.output))
    for image in wt.output_images.values():
        print(image)


if __name__ == "__main__":
    main()
