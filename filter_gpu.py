# filter_gpu.py
import re

# NVIDIA / AMD discrete-only keywords/patterns
GPU_INCLUDE = [
    r"\brtx\b", r"\bgtx\b", r"\bgeforce\b", r"\bnvidia\b",
    r"\bradeon\b", r"\brx\b", r"\bamd\s+radeon\b",
]

# Exclude integrated + Intel Arc 
GPU_EXCLUDE = [
    r"\bintel\b.*\buhd\b", r"\buhd\s+graphics\b",
    r"\biris\b", r"\biris\s+xe\b",
    r"\bintegrated\b", r"\buma\b", r"\bshared\b",
    r"\barc\b", r"\bintel\s+arc\b",
]

def normalize_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.lower()).strip()

def has_nvidia_amd_discrete_gpu(text: str) -> bool:
    t = normalize_text(text)
    include_hit = any(re.search(p, t) for p in GPU_INCLUDE)
    exclude_hit = any(re.search(p, t) for p in GPU_EXCLUDE)

    return include_hit and not exclude_hit
