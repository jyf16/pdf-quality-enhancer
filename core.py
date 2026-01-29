import io
import os
from dataclasses import dataclass

import fitz
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import numpy as np
import cv2


@dataclass(frozen=True)
class EnhanceParams:
    contrast: float = 2.0
    radius: float = 1.4
    percent: int = 100
    threshold: int = 0


def enhance_image(image: Image.Image, params: EnhanceParams) -> Image.Image:
    imnp = np.array(image)

    if len(imnp.shape) > 2 and imnp.shape[2] == 3:
        gray = cv2.cvtColor(imnp, cv2.COLOR_RGB2GRAY)
    else:
        gray = imnp
    tmp = gray / 8
    kernel = np.array(
        (
            [1, 1, 1],
            [1, 0, 1],
            [1, 1, 1],
        )
    )
    mask = cv2.filter2D(tmp, -1, kernel)
    mask = mask.astype(np.uint8)

    mask[mask < 240] = 0
    mask[mask != 0] = 255
    mask[mask == 0] = 25
    mask[mask == 255] = 0
    mask[mask == 25] = 255

    stretched_image = ImageOps.autocontrast(image, cutoff=1)
    enh_con = ImageEnhance.Contrast(stretched_image)
    img_contrasted = enh_con.enhance(params.contrast)

    ced = np.array(img_contrasted, dtype=np.uint8)

    if len(imnp.shape) > 2 and imnp.shape[2] == 3:
        result = (~mask)[..., np.newaxis] + (ced & mask[..., np.newaxis])
    else:
        result = ~mask + (ced & mask)
    image = Image.fromarray(result)

    img_sharpened = image.filter(
        ImageFilter.UnsharpMask(
            radius=params.radius,
            percent=params.percent,
            threshold=params.threshold,
        )
    )

    return img_sharpened


def build_output_path(file_path: str, suffix: str = "_enhanced") -> str | None:
    base, ext = os.path.splitext(file_path)
    if ext.lower() != ".pdf":
        return None
    if base.endswith(suffix):
        return None
    return f"{base}{suffix}.pdf"


def collect_pdf_files(paths: list[str]) -> list[str]:
    files: list[str] = []
    seen: set[str] = set()

    for path in paths:
        if os.path.isdir(path):
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                if os.path.isfile(full_path) and entry.lower().endswith(".pdf"):
                    if full_path not in seen:
                        files.append(full_path)
                        seen.add(full_path)
        elif os.path.isfile(path) and path.lower().endswith(".pdf"):
            if path not in seen:
                files.append(path)
                seen.add(path)

    return files


def process_pdf(
    file_path: str,
    params: EnhanceParams,
    suffix: str = "_enhanced",
    on_status=None,
) -> str | None:
    output_path = build_output_path(file_path, suffix=suffix)
    if output_path is None:
        if on_status:
            on_status(f"跳过已处理文件: {os.path.basename(file_path)}")
        return None

    if on_status:
        on_status(f"开始处理: {os.path.basename(file_path)}")

    with fitz.open(file_path) as doc:
        page_count = doc.page_count
        if page_count < 1:
            return None

        for page_num, page in enumerate(doc):
            if on_status:
                on_status(
                    f"处理 {os.path.basename(file_path)} - 第 {page_num + 1}/{page_count} 页"
                )

            image_list = page.get_images(full=True)
            if not image_list:
                continue

            for img_info in image_list:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue

                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))

                processed_image = enhance_image(image, params)

                buffer = io.BytesIO()
                dpi = (base_image.get("xres", 96), base_image.get("yres", 96))
                processed_image.save(buffer, format="PNG", dpi=dpi)

                page.replace_image(xref, stream=buffer.getvalue())

            page.clean_contents()

        doc.save(output_path, garbage=4, deflate=True, clean=True)

    return output_path


def process_files(
    file_list: list[str],
    params: EnhanceParams,
    suffix: str = "_enhanced",
    on_status=None,
    on_total_progress=None,
) -> tuple[int, int]:
    total_files = len(file_list)
    processed = 0

    for i, file_path in enumerate(file_list):
        if on_total_progress:
            on_total_progress(i + 1, total_files)

        output_path = process_pdf(
            file_path,
            params,
            suffix=suffix,
            on_status=on_status,
        )
        if output_path:
            processed += 1

    return processed, total_files
