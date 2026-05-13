import ctypes
import os
import tempfile
from pathlib import Path

from PIL import Image

from utils.resource_utils import get_data_path


WM_SETICON = 0x0080
ICON_SMALL = 0
ICON_BIG = 1
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040
GA_ROOT = 2


def get_app_icon_source_path():
    for filename in ("icon.png", "logo-goc.png", "app_v3.png", "logo.png"):
        icon_path = get_data_path(filename)
        if icon_path and os.path.exists(icon_path):
            return icon_path
    return get_data_path("icon.png")


def get_app_bitmap_icon_path():
    for filename in ("app_v3.ico", "app_v2.ico", "app.ico"):
        candidate = get_data_path(filename)
        if candidate and os.path.exists(candidate):
            return candidate

    source_path = get_app_icon_source_path()
    if not source_path or not os.path.exists(source_path):
        return ""

    generated_icon_path = Path(tempfile.gettempdir()) / "DeltaOne" / "delta_one_window_titlebar.ico"
    try:
        generated_icon_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source_path) as source_image:
            icon_image = source_image.convert("RGBA")
        icon_image.thumbnail((256, 256), Image.Resampling.LANCZOS)
        square_icon = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        square_icon.alpha_composite(
            icon_image,
            ((256 - icon_image.width) // 2, (256 - icon_image.height) // 2),
        )
        square_icon.save(
            generated_icon_path,
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )
        return str(generated_icon_path)
    except Exception:
        return ""


def apply_app_window_icon(window, owner=None):
    bitmap_icon_path = get_app_bitmap_icon_path()

    if bitmap_icon_path and os.path.exists(bitmap_icon_path):
        try:
            window.iconbitmap(bitmap_icon_path)
        except Exception:
            pass
        try:
            window.iconbitmap(default=bitmap_icon_path)
        except Exception:
            pass

    icon_refs = []
    for candidate_owner in (owner, getattr(window, "master", None), window.winfo_toplevel()):
        if candidate_owner is None:
            continue
        try:
            icon_refs = list(getattr(candidate_owner, "_icon_photo", []) or [])
        except Exception:
            icon_refs = []
        if icon_refs:
            break

    if icon_refs:
        try:
            window.iconphoto(True, *icon_refs)
        except Exception:
            pass

    _apply_native_windows_titlebar_icon(window, bitmap_icon_path)
    try:
        window.after(80, lambda: _apply_native_windows_titlebar_icon(window, bitmap_icon_path))
        window.after(260, lambda: _apply_native_windows_titlebar_icon(window, bitmap_icon_path))
    except Exception:
        pass

    return bitmap_icon_path


def _apply_native_windows_titlebar_icon(window, bitmap_icon_path):
    if os.name != "nt" or not bitmap_icon_path or not os.path.exists(bitmap_icon_path):
        return

    try:
        ctypes.windll.user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        ctypes.windll.user32.GetAncestor.restype = ctypes.c_void_p
        ctypes.windll.user32.LoadImageW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        ctypes.windll.user32.LoadImageW.restype = ctypes.c_void_p
        ctypes.windll.user32.SendMessageW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        ctypes.windll.user32.SendMessageW.restype = ctypes.c_void_p

        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetAncestor(int(window.winfo_id()), GA_ROOT)
        if not hwnd:
            hwnd = int(window.winfo_id())

        handles = []
        for icon_size, icon_type in ((16, ICON_SMALL), (32, ICON_BIG)):
            handle = ctypes.windll.user32.LoadImageW(
                None,
                bitmap_icon_path,
                IMAGE_ICON,
                icon_size,
                icon_size,
                LR_LOADFROMFILE | LR_DEFAULTSIZE,
            )
            if handle:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, icon_type, handle)
                handles.append(handle)

        if handles:
            existing_handles = list(getattr(window, "_native_icon_handles", []) or [])
            window._native_icon_handles = existing_handles + handles
    except Exception:
        pass
