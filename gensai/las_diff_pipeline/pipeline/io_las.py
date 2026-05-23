"""Point cloud I/O — LAS / CSV."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PointCloud:
    xyz: np.ndarray                            # (N, 3) float64
    classification: Optional[np.ndarray] = None
    intensity: Optional[np.ndarray] = None
    crs_epsg: Optional[int] = None
    extras: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.xyz)


def read_las(path: str | Path) -> PointCloud:
    """LAS / LAZ を読む."""
    try:
        import laspy
    except ImportError as e:
        raise ImportError("laspy is required to read LAS") from e

    path = Path(path)
    logger.info("Reading LAS: %s", path)
    las = laspy.read(str(path))
    xyz = np.column_stack([np.asarray(las.x, dtype=np.float64),
                            np.asarray(las.y, dtype=np.float64),
                            np.asarray(las.z, dtype=np.float64)])
    cls = np.asarray(las.classification, dtype=np.int8) if hasattr(las, "classification") else None
    inten = np.asarray(las.intensity, dtype=np.uint16) if hasattr(las, "intensity") else None

    epsg = None
    try:
        crs = las.header.parse_crs()
        if crs is not None:
            auth = crs.to_authority()
            if auth and auth[0] == "EPSG":
                epsg = int(auth[1])
    except Exception:
        pass

    return PointCloud(xyz=xyz, classification=cls, intensity=inten, crs_epsg=epsg)


def read_csv(path: str | Path, fallback_epsg: int | None = None) -> PointCloud:
    """CSV (x,y,z header 必須) を読む."""
    path = Path(path)
    logger.info("Reading CSV: %s", path)
    arr = np.genfromtxt(str(path), delimiter=",", names=True)
    xyz = np.column_stack([arr["x"], arr["y"], arr["z"]]).astype(np.float64)
    return PointCloud(xyz=xyz, crs_epsg=fallback_epsg)


def read_auto(path: str | Path, fallback_epsg: int | None = None) -> PointCloud:
    """拡張子で振り分け."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext in (".las", ".laz"):
        pc = read_las(path)
        if pc.crs_epsg is None and fallback_epsg is not None:
            pc.crs_epsg = fallback_epsg
        return pc
    if ext == ".csv":
        return read_csv(path, fallback_epsg=fallback_epsg)
    raise ValueError(f"Unsupported file type: {ext}")


def write_las(pc: PointCloud, path: str | Path, extra_dims: dict | None = None) -> None:
    """LAS で書き出す.

    extra_dims: {name: ndarray} で追加属性を保存可能（laspy ExtraBytes）.
    """
    try:
        import laspy
    except ImportError as e:
        raise ImportError("laspy is required to write LAS") from e

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    header = laspy.LasHeader(point_format=3, version="1.4")
    if pc.n > 0:
        header.offsets = pc.xyz.min(axis=0)
    else:
        header.offsets = np.array([0.0, 0.0, 0.0])
    header.scales = np.array([0.001, 0.001, 0.001])

    if pc.crs_epsg is not None:
        try:
            import pyproj
            header.add_crs(pyproj.CRS.from_epsg(pc.crs_epsg))
        except Exception:
            pass

    if extra_dims:
        for name, arr in extra_dims.items():
            header.add_extra_dim(laspy.ExtraBytesParams(name=name, type=np.float32))

    las = laspy.LasData(header)
    if pc.n > 0:
        las.x = pc.xyz[:, 0]
        las.y = pc.xyz[:, 1]
        las.z = pc.xyz[:, 2]
        if pc.classification is not None:
            las.classification = pc.classification
        if pc.intensity is not None:
            las.intensity = pc.intensity
        if extra_dims:
            for name, arr in extra_dims.items():
                setattr(las, name, np.asarray(arr, dtype=np.float32))

    las.write(str(path))
    logger.info("Wrote LAS: %s (%d points)", path, pc.n)
