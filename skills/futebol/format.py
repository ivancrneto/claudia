"""PT-BR humanization of kickoff times: "hoje às 18h30", "amanhã às 16h", "no sábado".

Pure/deterministic: the caller passes `now` (already in the target timezone) so the output
is testable without touching the clock.
"""

from __future__ import annotations

from datetime import datetime

# Monday=0 .. Sunday=6
_WEEKDAYS = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]
# "no sábado" / "no domingo" but "na terça-feira" etc.
_ARTICLE = {"sábado": "no", "domingo": "no"}


def _time_pt(dt: datetime) -> str:
    return f"{dt.hour}h{dt.minute:02d}" if dt.minute else f"{dt.hour}h"


def humanize_kickoff(kickoff: datetime, now: datetime) -> str:
    """Both datetimes must be in the same (target) timezone."""
    delta_days = (kickoff.date() - now.date()).days
    time_str = _time_pt(kickoff)

    if delta_days < 0:
        return f"no dia {kickoff.day:02d}/{kickoff.month:02d} às {time_str}"
    if delta_days == 0:
        return f"hoje às {time_str}"
    if delta_days == 1:
        return f"amanhã às {time_str}"
    if delta_days <= 6:
        weekday = _WEEKDAYS[kickoff.weekday()]
        article = _ARTICLE.get(weekday, "na")
        # Within the coming week but past this weekday's name → "no próximo ...".
        prefix = "no próximo" if weekday in ("sábado", "domingo") else "na próxima"
        near = f"{article} {weekday}" if delta_days <= 3 else f"{prefix} {weekday}"
        return f"{near} às {time_str}"
    return f"no dia {kickoff.day:02d}/{kickoff.month:02d} às {time_str}"
