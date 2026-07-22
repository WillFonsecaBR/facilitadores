"""
Fast Video Pack Creator.

Creates video packs from a source folder with progress indicators.
"""

import csv
import json
import logging
import os
import random
import re
import shutil
import sys
import traceback

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import cv2
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE_NAME = "config.json"
PACK_CREATOR_FOLDER_NAME = "pack_creator"

DEFAULT_PRINT_COUNT = 30

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".mpeg",
    ".mpg",
}

DESCRIPTION_FILES = {
    "DIAMOND": "descricao_diamond.html",
    "GOLD": "descricao_gold.html",
    "SILVER": "descricao_silver.html",
    "BRONZE": "descricao_bronze.html",
}

CATALOG_FILE_CANDIDATES = [
    "video_packs_catalog.json",
    "video_packs_catalog.txt",
    "video_packs_catalog.TXT.txt",
]

WOOCOMMERCE_HEADERS = [
    "id",
    "tipo",
    "sku",
    "nome",
    "publicado",
    "em_destaque_",
    "visibilidade_no_catalogo",
    "descricao_curta",
    "descricao",
    "status_de_taxa",
    "classe_de_taxa",
    "em_estoque_",
    "estoque",
    "preco_promocional",
    "preco_padrao",
    "categorias",
    "imagens",
    "limite_de_download",
    "dias_de_expiracao_do_download",
    "download_1_nome",
    "download_1_url",
    "download_2_nome",
    "download_2_url",
    "virtual",
    "baixavel",
]

def clean_text(value: Any) -> str:
    """
    Cleans text values loaded from JSON.
    """

    if value is None:
        return ""

    return (
        str(value)
        .replace("\ufeff", "")
        .replace("\u200b", "")
        .replace("\u00a0", " ")
        .strip()
        .strip('"')
        .strip("'")
        .strip()
    )

def create_logger():
    """
    Creates execution and error logs.
    """

    logs_folder = PROJECT_ROOT / "logs"
    error_folder = PROJECT_ROOT / "error"

    logs_folder.mkdir(parents=True, exist_ok=True)
    error_folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    log_path = logs_folder / (
        f"video_pack_creator_{timestamp}.log"
    )

    error_path = error_folder / (
        f"video_pack_creator_errors_{timestamp}.log"
    )

    logger = logging.getLogger("video_pack_creator")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        log_path,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("Video Pack Creator started.")
    logger.info("Project root: %s", PROJECT_ROOT)
    logger.info(
        "Configuration file: %s",
        PROJECT_ROOT / CONFIG_FILE_NAME,
    )

    return logger, error_path

def write_error(
    logger: logging.Logger,
    error_path: Path,
    error: BaseException,
) -> None:
    """
    Saves the complete error traceback.
    """

    logger.error("Video pack creation failed.")

    with error_path.open("a", encoding="utf-8") as file:
        file.write("\n" + "=" * 80 + "\n")
        file.write(f"Timestamp: {datetime.now().isoformat()}\n")
        file.write(f"Error: {error}\n")
        file.write(traceback.format_exc())
        file.write("\n")

def load_config() -> Dict[str, Any]:
    """
    Loads config.json from the project root.
    """

    config_path = PROJECT_ROOT / CONFIG_FILE_NAME

    print(
        f"Loading configuration: {config_path}",
        flush=True,
    )

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    with config_path.open(
        "r",
        encoding="utf-8-sig",
    ) as file:
        config = json.load(file)

    if not isinstance(config, dict):
        raise ValueError(
            "The configuration root must be a JSON object."
        )

    return config

def load_settings(
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Loads and validates pack settings.
    """

    print(
        "Reading pack settings...",
        flush=True,
    )

    section = config.get("criador_de_packs")

    if not isinstance(section, dict):
        raise ValueError(
            "The 'criador_de_packs' section was not found."
        )

    root_folder = clean_text(
        section.get("root_folder")
    )

    niche = clean_text(
        section.get("nicho")
    ).upper()

    pack_type = clean_text(
        section.get("tipo_do_pack")
    ).upper()

    packs_quantity = section.get("qtd_packs")
    videos_per_pack = section.get("qtd_videos")

    valid_pack_types = {
        "DIAMOND",
        "GOLD",
        "SILVER",
        "BRONZE",
    }

    if pack_type not in valid_pack_types:
        raise ValueError(
            "The 'tipo_do_pack' field must be "
            "DIAMOND, GOLD, SILVER, or BRONZE. "
            f"Value received: {pack_type!r}."
        )

    if not root_folder:
        raise ValueError(
            "The 'root_folder' field is empty."
        )

    if not isinstance(packs_quantity, int):
        raise ValueError(
            "'qtd_packs' must be an integer."
        )

    if not isinstance(videos_per_pack, int):
        raise ValueError(
            "'qtd_videos' must be an integer."
        )

    if packs_quantity <= 0:
        raise ValueError(
            "'qtd_packs' must be greater than zero."
        )

    if videos_per_pack <= 0:
        raise ValueError(
            "'qtd_videos' must be greater than zero."
        )

    if not niche:
        raise ValueError(
            "'nicho' must contain a valid value."
        )

    return {
        "source_folder": Path(root_folder).expanduser().resolve(),
        "packs_quantity": packs_quantity,
        "videos_per_pack": videos_per_pack,
        "niche": niche,
        "pack_type": pack_type,
        "allowed_extensions": get_allowed_extensions(config),
    }

def get_allowed_extensions(
    config: Dict[str, Any],
) -> set:
    """
    Gets video extensions from config.json.
    """

    section = config.get("criador_de_packs", {})
    configured = section.get("allowed_video_ext")

    if not configured:
        return VIDEO_EXTENSIONS.copy()

    extensions = set()

    for extension in configured:
        extension = clean_text(extension).lower()

        if not extension.startswith("."):
            extension = "." + extension

        extensions.add(extension)

    return extensions or VIDEO_EXTENSIONS.copy()

def find_catalog_path() -> Path:
    """
    Finds the catalog file.
    """

    catalog_folder = PROJECT_ROOT / PACK_CREATOR_FOLDER_NAME

    for filename in CATALOG_FILE_CANDIDATES:
        path = catalog_folder / filename

        if path.exists():
            return path

    raise FileNotFoundError(
        "Video pack catalog was not found in the pack_creator folder."
    )

def load_catalog() -> Dict[str, Any]:
    """
    Loads the video pack catalog.
    """

    print(
        "Loading video pack catalog...",
        flush=True,
    )

    catalog_path = find_catalog_path()

    with catalog_path.open(
        "r",
        encoding="utf-8-sig",
    ) as file:
        catalog = json.load(file)

    if not isinstance(catalog, dict):
        raise ValueError(
            "The catalog root must be a JSON object."
        )

    return catalog

def get_niche_data(
    catalog: Dict[str, Any],
    niche: str,
) -> Dict[str, Any]:
    """
    Finds the configured niche in the catalog.
    """

    print(
        f"Loading niche catalog: {niche}",
        flush=True,
    )

    niches = catalog.get("niches", [])

    if not isinstance(niches, list):
        raise ValueError(
            "The catalog 'niches' field must be a list."
        )

    for item in niches:
        if not isinstance(item, dict):
            continue

        item_code = clean_text(
            item.get("niche_code")
        ).upper()

        if item_code == niche.upper():
            return item

    raise ValueError(
        f"Niche '{niche}' was not found in the catalog."
    )

def is_generated_folder(path: Path) -> bool:
    """
    Identifies generated output folders.
    """

    generated_names = {
        "PACKS_GENERATED",
        "PACKS_GENERADOS",
        "GENERATED_PACKS",
        "VIDEO_PACKS",
    }

    return any(
        part.upper() in generated_names
        for part in path.parts
    )

def scan_videos(
    source_folder: Path,
    extensions: set,
    logger: logging.Logger,
) -> List[Path]:
    """
    Scans videos with an immediate progress indicator.

    The total is intentionally omitted because counting the entire disk
    before processing would add another complete scan.
    """

    if not source_folder.exists():
        raise FileNotFoundError(
            f"Source folder does not exist: {source_folder}"
        )

    if not source_folder.is_dir():
        raise NotADirectoryError(
            f"Source path is not a directory: {source_folder}"
        )

    print(
        f"Scanning source folder: {source_folder}",
        flush=True,
    )

    videos = []

    with tqdm(
        desc="Organizing media",
        unit="file",
        dynamic_ncols=True,
        leave=True,
    ) as progress:

        for current_root, directories, files in os.walk(
            source_folder
        ):
            directories[:] = [
                directory
                for directory in directories
                if directory.upper()
                not in {
                    "PACKS_GENERATED",
                    "PACKS_GENERADOS",
                    "GENERATED_PACKS",
                    "VIDEO_PACKS",
                }
            ]

            for filename in files:
                progress.update(1)

                path = Path(current_root) / filename

                if path.suffix.lower() not in extensions:
                    continue

                if is_generated_folder(path):
                    continue

                videos.append(path)

    videos.sort(
        key=lambda item: str(item).lower()
    )

    logger.info(
        "Compatible videos found: %s",
        len(videos),
    )

    return videos

def select_videos_fast(
    videos: Sequence[Path],
    quantity: int,
    logger: logging.Logger,
) -> List[Path]:
    """
    Selects videos efficiently.

    This replaces the slow nested candidate-recalculation algorithm.
    random.sample performs the selection in a single efficient operation.

    The selected list is shuffled again so pack distribution remains random.
    """

    if len(videos) < quantity:
        raise ValueError(
            f"Not enough videos. Required: {quantity}; "
            f"available: {len(videos)}."
        )

    print(
        f"Selecting {quantity} videos quickly...",
        flush=True,
    )

    selected = random.sample(
        list(videos),
        quantity,
    )

    random.shuffle(selected)

    with tqdm(
        total=quantity,
        initial=quantity,
        desc="Selecting videos",
        unit="video",
        dynamic_ncols=True,
        leave=True,
    ):
        pass

    logger.info(
        "Videos selected: %s",
        len(selected),
    )

    return selected

def create_generation_folder(
    settings: Dict[str, Any],
) -> Path:
    """
    Creates the output folder before the expensive selection stage.
    """

    source_folder = settings["source_folder"]
    niche = settings["niche"]
    packs_quantity = settings["packs_quantity"]

    date_code = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    generation_folder = (
        source_folder
        / "PACKS_GENERATED"
        / f"{niche}_{packs_quantity}_PACKS_{date_code}"
    )

    generation_folder.mkdir(
        parents=True,
        exist_ok=False,
    )

    print(
        f"Output folder created: {generation_folder}",
        flush=True,
    )

    return generation_folder

def split_into_packs(
    selected: Sequence[Path],
    packs_quantity: int,
    videos_per_pack: int,
) -> List[List[Path]]:
    """
    Divides selected videos into packs.
    """

    packs = []

    with tqdm(
        total=packs_quantity,
        desc="Dividing videos into packs",
        unit="pack",
        dynamic_ncols=True,
        leave=True,
    ) as progress:

        for index in range(packs_quantity):
            start = index * videos_per_pack
            end = start + videos_per_pack

            packs.append(
                list(selected[start:end])
            )

            progress.update(1)

    return packs

def replace_template(
    template: str,
    pack_id: int,
    quantity: int,
    niche: str,
) -> str:
    """
    Replaces catalog placeholders.
    """

    if not template:
        return ""

    return template.format(
        PACK_ID=pack_id,
        QTY=quantity,
        SKU_SEQ=pack_id,
        NICHE_CODE=niche,
    )

def safe_folder_name(value: str) -> str:
    """
    Makes a safe folder name.
    """

    value = re.sub(
        r'[<>:"/\|?*]',
        "",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

def make_slug(value: str) -> str:
    """
    Creates a URL-safe slug.
    """

    value = value.lower()
    value = re.sub(
        r"[^a-z0-9\s-]",
        "",
        value,
    )
    value = re.sub(
        r"[\s_-]+",
        "-",
        value,
    )

    return value.strip("-")

def create_pack_metadata(
    niche_data: Dict[str, Any],
    settings: Dict[str, Any],
    pack_id: int,
    generation_folder: Path,
    video_files: List[Path],
) -> Dict[str, Any]:
    """
    Creates metadata for one pack.
    """

    quantity = len(video_files)
    niche = settings["niche"]

    short_name = replace_template(
        str(niche_data.get("short_name_template", "")),
        pack_id,
        quantity,
        niche,
    )

    seo_name = replace_template(
        str(niche_data.get("seo_name_template", "")),
        pack_id,
        quantity,
        niche,
    )

    slug = replace_template(
        str(niche_data.get("seo_slug_template", "")),
        pack_id,
        quantity,
        niche,
    )

    meta_title = replace_template(
        str(niche_data.get("meta_title_template", "")),
        pack_id,
        quantity,
        niche,
    )

    sku = replace_template(
        str(niche_data.get("sku_template", "")),
        pack_id,
        quantity,
        niche,
    )

    unique_title = replace_template(
        str(niche_data.get("unique_title_model", "")),
        pack_id,
        quantity,
        niche,
    )

    if not short_name:
        short_name = f"{niche} Video Pack {pack_id}"

    if not seo_name:
        seo_name = f"{short_name} - {quantity} Videos"

    pack_folder = (
        generation_folder
        / safe_folder_name(short_name)
    )

    return {
        "pack_id": pack_id,
        "short_name": safe_folder_name(short_name),
        "seo_name": seo_name,
        "slug": make_slug(slug or seo_name),
        "meta_title": meta_title or seo_name,
        "sku": sku or f"{niche}-{pack_id:04d}",
        "unique_title": unique_title or seo_name,
        "tags": niche_data.get("main_tags", []),
        "pack_type": settings["pack_type"],
        "niche": niche,
        "niche_label": niche_data.get(
            "niche_label",
            niche,
        ),
        "pack_folder": pack_folder,
        "videos_folder": pack_folder / "VIDEOS",
        "images_folder": pack_folder / "IMAGES",
        "prints_folder": (
            pack_folder
            / "IMAGES"
            / "PRINTS_OF_VIDEOS"
        ),
        "info_file": pack_folder / "INFO.txt",
        "description_file": (
            pack_folder / "DESCRIPTION.html"
        ),
        "video_files": video_files,
        "quantity": quantity,
    }

def create_pack_folders(
    metadata: Dict[str, Any],
) -> None:
    """
    Creates the pack folders.
    """

    metadata["videos_folder"].mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata["images_folder"].mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata["prints_folder"].mkdir(
        parents=True,
        exist_ok=True,
    )

def move_pack_videos(
    metadata: Dict[str, Any],
    logger: logging.Logger,
) -> None:
    """
    Moves videos into the pack folder.
    """

    moved_files = []

    with tqdm(
        metadata["video_files"],
        desc=f"Moving {metadata['short_name']}",
        unit="video",
        dynamic_ncols=True,
        leave=True,
    ) as progress:

        for source in progress:
            destination = (
                metadata["videos_folder"]
                / source.name
            )

            if destination.exists():
                stem = source.stem
                suffix = source.suffix
                counter = 1

                while destination.exists():
                    destination = (
                        metadata["videos_folder"]
                        / f"{stem}_{counter}{suffix}"
                    )
                    counter += 1

            shutil.move(
                str(source),
                str(destination),
            )

            moved_files.append(destination)

    metadata["video_files"] = moved_files

    logger.info(
        "Moved %s videos to %s",
        len(moved_files),
        metadata["short_name"],
    )

def load_description_template(
    pack_type: str,
) -> str:
    """
    Loads the selected HTML description.
    """

    filename = DESCRIPTION_FILES.get(
        pack_type.upper()
    )

    if not filename:
        raise ValueError(
            f"Unsupported pack type: {pack_type}"
        )

    path = (
        PROJECT_ROOT
        / PACK_CREATOR_FOLDER_NAME
        / filename
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Description file not found: {path}"
        )

    return path.read_text(
        encoding="utf-8"
    )

def create_description(
    metadata: Dict[str, Any],
) -> str:
    """
    Creates DESCRIPTION.html.
    """

    html = load_description_template(
        metadata["pack_type"]
    )

    title = metadata["short_name"].upper()

    html = html.replace(
        "<h1>[PACK TITLE]</h1>",
        f"<h1>{title}</h1>",
    )

    html = html.replace(
        "[PACK TITLE]",
        title,
    )

    metadata["description_file"].write_text(
        html,
        encoding="utf-8",
    )

    return html

def extract_second_frame(
    video_path: Path,
) -> Optional[Any]:
    """
    Extracts the second frame from a video.
    """

    capture = cv2.VideoCapture(
        str(video_path)
    )

    try:
        if not capture.isOpened():
            return None

        first_ok, _ = capture.read()

        if not first_ok:
            return None

        second_ok, frame = capture.read()

        if not second_ok:
            return None

        return frame

    finally:
        capture.release()

def create_prints(
    metadata: Dict[str, Any],
    logger: logging.Logger,
) -> int:
    """
    Creates up to 30 prints for the pack.
    """

    videos = list(metadata["video_files"])
    random.shuffle(videos)

    videos = videos[
        :min(DEFAULT_PRINT_COUNT, len(videos))
    ]

    generated = 0

    with tqdm(
        videos,
        desc=f"Creating prints for {metadata['short_name']}",
        unit="print",
        dynamic_ncols=True,
        leave=True,
    ) as progress:

        for video_path in progress:
            frame = extract_second_frame(
                video_path
            )

            if frame is None:
                logger.warning(
                    "Could not extract frame: %s",
                    video_path,
                )
                continue

            image_path = (
                metadata["prints_folder"]
                / f"print_{video_path.stem}.jpg"
            )

            if cv2.imwrite(
                str(image_path),
                frame,
            ):
                generated += 1

    return generated

def write_info(
    metadata: Dict[str, Any],
    generation_folder: Path,
    prints_count: int,
) -> None:
    """
    Writes INFO.txt for the pack.
    """

    video_names = "\n".join(
        f"- {video.name}"
        for video in metadata["video_files"]
    )

    tags = ", ".join(
        str(tag)
        for tag in metadata["tags"]
    )

    content = f"""VIDEO PACK INFORMATION
=======================

Pack Name: {metadata["short_name"]}
SEO Product Name: {metadata["seo_name"]}
Unique Product Title: {metadata["unique_title"]}
Pack ID: {metadata["pack_id"]}
Generation Folder: {generation_folder.name}

Niche: {metadata["niche"]}
Niche Label: {metadata["niche_label"]}
Pack Type: {metadata["pack_type"]}
Video Quantity: {metadata["quantity"]}
Prints Requested: {DEFAULT_PRINT_COUNT}
Prints Generated: {prints_count}

SKU: {metadata["sku"]}
Slug: {metadata["slug"]}
Meta Title: {metadata["meta_title"]}
Tags: {tags}

Product Price:
Promotional Price:
Product Images:
Download URL 1:
Download URL 2:

VIDEOS IN THIS PACK
===================
{video_names}
"""

    metadata["info_file"].write_text(
        content,
        encoding="utf-8",
    )

def create_csv_row(
    metadata: Dict[str, Any],
    description_html: str,
) -> Dict[str, Any]:
    """
    Creates a WooCommerce CSV row.
    """

    return {
        "id": "",
        "tipo": "simple",
        "sku": metadata["sku"],
        "nome": metadata["seo_name"],
        "publicado": 1,
        "em_destaque_": 0,
        "visibilidade_no_catalogo": "visible",
        "descricao_curta": (
            f"{metadata['quantity']} ready-to-post "
            f"{str(metadata['niche_label']).lower()} "
            "video clips for social media content."
        ),
        "descricao": description_html,
        "status_de_taxa": "taxable",
        "classe_de_taxa": "standard",
        "em_estoque_": 1,
        "estoque": metadata["quantity"],
        "preco_promocional": "",
        "preco_padrao": "",
        "categorias": metadata["niche_label"],
        "imagens": "",
        "limite_de_download": "",
        "dias_de_expiracao_do_download": "",
        "download_1_nome": (
            f"{metadata['short_name']} Videos"
        ),
        "download_1_url": "",
        "download_2_nome": (
            f"{metadata['short_name']} Bonus Files"
        ),
        "download_2_url": "",
        "virtual": 1,
        "baixavel": 1,
    }

def write_csv(
    generation_folder: Path,
    rows: List[Dict[str, Any]],
) -> Path:
    """
    Writes the WooCommerce CSV.
    """

    print(
        "Generating WooCommerce CSV...",
        flush=True,
    )

    csv_path = (
        generation_folder
        / f"{generation_folder.name}.csv"
    )

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=WOOCOMMERCE_HEADERS,
        )

        writer.writeheader()

        with tqdm(
            rows,
            desc="Writing products",
            unit="product",
            dynamic_ncols=True,
            leave=True,
        ) as progress:

            for row in progress:
                writer.writerow(row)

    return csv_path

def write_generation_summary(
    generation_folder: Path,
    settings: Dict[str, Any],
    metadata_list: List[Dict[str, Any]],
    csv_path: Path,
) -> None:
    """
    Writes a summary file for the complete generation.
    """

    summary_path = (
        generation_folder
        / "GENERATION_INFO.txt"
    )

    total_videos = sum(
        metadata["quantity"]
        for metadata in metadata_list
    )

    lines = [
        "VIDEO PACK GENERATION",
        "=====================",
        "",
        f"Creation Date: {datetime.now().isoformat()}",
        f"Source Folder: {settings['source_folder']}",
        f"Niche: {settings['niche']}",
        f"Pack Type: {settings['pack_type']}",
        f"Pack Quantity: {settings['packs_quantity']}",
        f"Videos Per Pack: {settings['videos_per_pack']}",
        f"Total Videos Moved: {total_videos}",
        f"CSV File: {csv_path.name}",
        "",
        "GENERATED PACKS",
        "===============",
    ]

    with tqdm(
        metadata_list,
        desc="Writing generation summary",
        unit="pack",
        dynamic_ncols=True,
        leave=True,
    ) as progress:

        for metadata in progress:
            lines.extend(
                [
                    "",
                    f"Pack ID: {metadata['pack_id']}",
                    f"Pack Name: {metadata['short_name']}",
                    f"SKU: {metadata['sku']}",
                    f"Video Quantity: {metadata['quantity']}",
                ]
            )

    summary_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

def run_video_pack_creator() -> None:
    """
    Runs the complete optimized workflow.
    """

    logger, error_path = create_logger()

    try:
        config = load_config()
        settings = load_settings(config)
        catalog = load_catalog()

        niche_data = get_niche_data(
            catalog,
            settings["niche"],
        )

        source_folder = settings["source_folder"]
        total_required = (
            settings["packs_quantity"]
            * settings["videos_per_pack"]
        )

        print(
            f"Total videos required: {total_required}",
            flush=True,
        )

        # Created before scanning and selection so the user gets
        # an output folder even if a later stage fails.
        generation_folder = create_generation_folder(
            settings
        )

        videos = scan_videos(
            source_folder,
            settings["allowed_extensions"],
            logger,
        )

        selected = select_videos_fast(
            videos,
            total_required,
            logger,
        )

        packs = split_into_packs(
            selected,
            settings["packs_quantity"],
            settings["videos_per_pack"],
        )

        metadata_list = []
        csv_rows = []

        with tqdm(
            packs,
            desc="Creating video packs",
            unit="pack",
            dynamic_ncols=True,
            leave=True,
        ) as progress:

            for pack_id, pack_files in enumerate(
                progress,
                start=1,
            ):
                progress.set_postfix(
                    pack=pack_id,
                )

                metadata = create_pack_metadata(
                    niche_data=niche_data,
                    settings=settings,
                    pack_id=pack_id,
                    generation_folder=generation_folder,
                    video_files=pack_files,
                )

                create_pack_folders(metadata)

                move_pack_videos(
                    metadata,
                    logger,
                )

                description_html = create_description(
                    metadata
                )

                prints_count = create_prints(
                    metadata,
                    logger,
                )

                write_info(
                    metadata=metadata,
                    generation_folder=generation_folder,
                    prints_count=prints_count,
                )

                metadata_list.append(metadata)

                csv_rows.append(
                    create_csv_row(
                        metadata,
                        description_html,
                    )
                )

        csv_path = write_csv(
            generation_folder,
            csv_rows,
        )

        write_generation_summary(
            generation_folder=generation_folder,
            settings=settings,
            metadata_list=metadata_list,
            csv_path=csv_path,
        )

        logger.info(
            "Video pack creation completed successfully."
        )

        print(
            f"Completed. Output folder: {generation_folder}",
            flush=True,
        )

    except Exception as error:
        write_error(
            logger,
            error_path,
            error,
        )
        raise

if __name__ == "__main__":
    run_video_pack_creator()