"""Recommended module sequence. IDs stay fixed; this list sets the order learners take them.

TRACK is the engineering leveling track: its own foundation (ENG-0), then six dimensions, each taken at
four levels (the suffix is the level the module targets; -2 covers levels 1 and 2). The seventh dimension,
IAC (infrastructure as code and configuration management), has three modules numbered in sequence:
IAC-1 is the entry level (levels 1 and 2), IAC-2 targets level 3 and IAC-3 targets level 4.
"""

TRACK = [
    "ENG-0", "ENG-1",
    "GRC-2", "VM-2", "SDR-2", "CPS-2", "AID-2", "ARC-2", "IAC-1",
    "GRC-3", "VM-3", "SDR-3", "CPS-3", "AID-3", "ARC-3", "IAC-2",
    "GRC-4", "VM-4", "SDR-4", "CPS-4", "AID-4", "ARC-4", "IAC-3",
    "GRC-5", "VM-5", "SDR-5", "CPS-5", "AID-5", "ARC-5",
]


def position(module_id: str) -> tuple[int, int]:
    """Return (1-based position, total) for a module id within the track."""
    return TRACK.index(module_id) + 1, len(TRACK)
