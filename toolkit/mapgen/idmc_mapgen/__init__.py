"""Headless IDMC CDI mapping generator: JSON spec -> IMF -> DTEMPLATE package -> import -> task -> run.

    from idmc_mapgen import load_spec, build, package_bytes
    spec = load_spec("examples/retail/m_rdf_customer_cleanse.json", profile="profile.local.json")
    pkg = package_bytes(spec, build(spec))

Public names are loaded lazily, so importing a helper module (e.g. idmc_mapgen.lock) stays cheap.
"""
__version__ = "1.0.0"

_LAZY = {
    "load_spec": ("spec", "load_spec"),
    "load_profile": ("spec", "load_profile"),
    "SpecError": ("spec", "SpecError"),
    "build": ("compile", "build"),
    "compile_file": ("compile", "compile_file"),
    "package": ("package", "package"),
    "package_bytes": ("package", "package_bytes"),
}

__all__ = ["__version__"] + sorted(_LAZY)


def __getattr__(name):
    if name in _LAZY:
        import importlib
        mod, attr = _LAZY[name]
        return getattr(importlib.import_module("." + mod, __name__), attr)
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
