"""lab build-image: build the tools container from lab/image/Dockerfile (local only, never pushes)."""
from __future__ import annotations

from argparse import Namespace

from labcli.context import EXIT_FAIL, EXIT_OK, EXIT_USAGE, LAB_ROOT, Ctx, engine_or_none

IMAGE_DIR = LAB_ROOT / "image"


def cmd_build_image(ctx: Ctx, args: Namespace) -> int:
    if ctx.in_shell:
        ctx.say("Run this from your own computer, not inside the lab shell.")
        return EXIT_USAGE
    env = engine_or_none(ctx)
    if env is None:
        return EXIT_USAGE
    dockerfile = IMAGE_DIR / "Dockerfile"
    argv = (env.engine, "build", "-t", env.image, "-f", str(dockerfile), str(IMAGE_DIR))
    if args.dry_run:
        ctx.show(argv)
        return EXIT_OK
    if not dockerfile.is_file():
        ctx.say(f"ERROR: {dockerfile} not found.")
        return EXIT_FAIL
    ctx.say(f"Building {env.image} with {env.engine}. This downloads about 400 MB and can take several minutes.")
    if ctx.deps.runner.run_interactive(argv) != 0:
        ctx.say("Image build failed. Read the last error above, fix it, and run 'lab build-image' again.")
        return EXIT_FAIL
    ctx.say(f"Built {env.image}.")
    return EXIT_OK
