import re

from ailog import query

SELECTOR = '{app="ai-fixture"}'
UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
MAX_WINDOW = 3600


def scope_problems(expr):
    problems = []
    if re.findall(r"\{[^}]*\}", expr) != [SELECTOR]:
        problems.append("selector must be exactly " + SELECTOR)
    windows = re.findall(r"\[(\d+)([smhd])\]", expr)
    if not windows or any(int(n) * UNITS[u] > MAX_WINDOW for n, u in windows):
        problems.append("every range must be present and at most 1h")
    return problems


def rows(expr):
    return query(expr)["data"]["result"]
