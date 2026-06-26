import os
import re
from urllib.parse import unquote, urlparse

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

def upload_image(file):
    result = cloudinary.uploader.upload(
        file,
        folder="metropolitan"
    )
    return result["secure_url"]


def upload_document(file):
    result = cloudinary.uploader.upload(
        file,
        folder="metropolitan/documentos",
        resource_type="raw",
    )
    return {
        "secure_url": result["secure_url"],
        "format": result.get("format"),
        "resource_type": result.get("resource_type", "raw"),
        "original_filename": result.get("original_filename") or getattr(file, "filename", "documento"),
    }


def extract_public_id_from_url(image_url):
    if not image_url:
        return None

    parsed_url = urlparse(image_url)
    if "/upload/" not in parsed_url.path:
        return None

    upload_path = parsed_url.path.split("/upload/", 1)[1]
    segments = [segment for segment in upload_path.split("/") if segment]
    if not segments:
        return None

    version_index = next(
        (index for index, segment in enumerate(segments) if re.fullmatch(r"v\d+", segment)),
        None,
    )
    public_segments = segments[version_index + 1:] if version_index is not None else segments

    if not public_segments:
        return None

    public_segments[-1] = os.path.splitext(public_segments[-1])[0]
    return unquote("/".join(public_segments))


def delete_image_by_url(image_url):
    public_id = extract_public_id_from_url(image_url)
    if not public_id:
        return False

    result = cloudinary.uploader.destroy(public_id)
    return result.get("result") in {"ok", "not found"}


def delete_resource_by_url(resource_url, resource_type="raw"):
    public_id = extract_public_id_from_url(resource_url)
    if not public_id:
        return False

    result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
    return result.get("result") in {"ok", "not found"}
