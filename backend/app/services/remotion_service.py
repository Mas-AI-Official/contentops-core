"""
Remotion Render Service - Handles stitching and final rendering (Phase 4).
"""
import asyncio
import json
import shutil
import uuid
from pathlib import Path
from typing import List, Optional
from loguru import logger
from app.core.config import settings


class RemotionService:
    """Service to bridge Python and Remotion for High-End Video Assembly."""

    def __init__(self):
        self.remotion_path = Path(settings.base_path) / "backend" / "remotion"

    async def render_promo(
        self,
        assets: List[str],
        audio_path: str,
        output_path: str,
        logo_path: Optional[str] = None,
    ) -> str:
        """
        Execute Remotion render command line with timeout/abort safety.
        """
        abs_assets = [str(Path(a).absolute()).replace("\\", "/") for a in assets]
        abs_audio = str(Path(audio_path).absolute()).replace("\\", "/")
        abs_output = str(Path(output_path).absolute()).replace("\\", "/")
        abs_logo = str(Path(logo_path).absolute()).replace("\\", "/") if logo_path else None

        # Remotion blocks direct local file:// media for safety; copy inputs into remotion/public runtime folder.
        run_id = uuid.uuid4().hex[:12]
        runtime_dir = self.remotion_path / "public" / "runtime" / run_id
        runtime_dir.mkdir(parents=True, exist_ok=True)

        public_assets: List[str] = []
        for i, src in enumerate(abs_assets):
            src_path = Path(src)
            dst_name = f"asset_{i}{src_path.suffix or '.mp4'}"
            dst_path = runtime_dir / dst_name
            shutil.copy2(src_path, dst_path)
            public_assets.append(f"/runtime/{run_id}/{dst_name}")

        audio_src = Path(abs_audio)
        audio_name = f"audio{audio_src.suffix or '.wav'}"
        audio_dst = runtime_dir / audio_name
        shutil.copy2(audio_src, audio_dst)
        public_audio = f"/runtime/{run_id}/{audio_name}"

        public_logo = None
        if abs_logo:
            logo_src = Path(abs_logo)
            logo_name = f"logo{logo_src.suffix or '.png'}"
            logo_dst = runtime_dir / logo_name
            shutil.copy2(logo_src, logo_dst)
            public_logo = f"/runtime/{run_id}/{logo_name}"

        from app.services.render_service import render_service

        duration_s = render_service.get_audio_duration(Path(audio_path))
        if duration_s < 1:
            duration_s = 60
        duration_frames = int(duration_s * 30)

        input_props = {
            "assets": public_assets,
            "audioPath": public_audio,
            "logoPath": public_logo,
        }

        npx_bin = shutil.which("npx") or shutil.which("npx.cmd")
        npm_bin = shutil.which("npm") or shutil.which("npm.cmd")
        if npx_bin:
            cmd = [
                npx_bin,
                "remotion",
                "render",
                "src/index.ts",
                "DaenaPromo",
                abs_output,
                "--props",
                json.dumps(input_props),
                "--duration",
                str(duration_frames),
                "--public-dir",
                str((self.remotion_path / "public").resolve()),
            ]
        elif npm_bin:
            cmd = [
                npm_bin,
                "exec",
                "--",
                "remotion",
                "render",
                "src/index.ts",
                "DaenaPromo",
                abs_output,
                "--props",
                json.dumps(input_props),
                "--duration",
                str(duration_frames),
                "--public-dir",
                str((self.remotion_path / "public").resolve()),
            ]
        else:
            raise RuntimeError("Neither npx nor npm was found in PATH for Remotion rendering.")

        logger.info(
            f"Triggering Remotion assembly for {len(assets)} scenes ({duration_s:.1f}s), timeout={settings.remotion_render_timeout_seconds}s"
        )

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.remotion_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=float(settings.remotion_render_timeout_seconds),
            )
        except asyncio.TimeoutError:
            logger.error("Remotion render timed out. Terminating subprocess.")
            process.kill()
            await process.communicate()
            raise RuntimeError(
                f"Remotion timed out after {settings.remotion_render_timeout_seconds}s"
            )

        if process.returncode != 0:
            out = stdout.decode(errors="ignore")
            err = stderr.decode(errors="ignore")
            logger.error(f"Remotion render failed with code {process.returncode}")
            logger.error(f"STDERR: {err}")
            if out:
                logger.debug(f"STDOUT: {out}")
            raise RuntimeError(f"Remotion render failed: {err or out or 'unknown error'}")

        logger.info(f"Remotion render complete: {abs_output}")
        return abs_output


remotion_service = RemotionService()
