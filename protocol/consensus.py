from __future__ import annotations

from config import settings
from protocol.message import Conflict, Finding


class ConflictDetector:
    def detect(self, findings: dict[str, Finding]) -> list[Conflict]:
        finding_list = list(findings.values())
        conflicts: list[Conflict] = []
        seen: set[tuple[str, str]] = set()

        for i, fa in enumerate(finding_list):
            for fb in finding_list[i + 1 :]:
                pair = tuple(sorted([fa.id, fb.id]))
                if pair in seen or fa.category == fb.category:
                    continue

                conflict = self._check_conflict(fa, fb)
                if conflict:
                    conflicts.append(conflict)
                    seen.add(pair)

        return conflicts

    def _check_conflict(self, fa: Finding, fb: Finding) -> Conflict | None:
        if fa.file != fb.file:
            return None

        location_conflict = self._location_overlap(fa, fb)
        if location_conflict:
            return Conflict(
                finding_a=fa,
                finding_b=fb,
                conflict_type="location",
                description=(
                    f"{fa.category.value} and {fb.category.value} both flag "
                    f"{fa.file} lines {fa.line}-{fa.line_end} vs {fb.line}-{fb.line_end}"
                ),
            )

        semantic_conflict = self._semantic_contradiction(fa, fb)
        if semantic_conflict:
            return Conflict(
                finding_a=fa,
                finding_b=fb,
                conflict_type="semantic",
                description=semantic_conflict,
            )

        return None

    def _location_overlap(self, fa: Finding, fb: Finding) -> bool:
        if fa.line is None or fb.line is None:
            return False
        window = settings.conflict_line_window
        a_start = fa.line
        a_end = fa.line_end or fa.line
        b_start = fb.line
        b_end = fb.line_end or fb.line
        return not (a_end + window < b_start or b_end + window < a_start)

    def _semantic_contradiction(self, fa: Finding, fb: Finding) -> str | None:
        add_keywords = {"add", "introduce", "include", "wrap", "enable"}
        remove_keywords = {"remove", "delete", "eliminate", "avoid", "disable"}

        a_adds = any(w in fa.suggestion.lower() for w in add_keywords)
        a_removes = any(w in fa.suggestion.lower() for w in remove_keywords)
        b_adds = any(w in fb.suggestion.lower() for w in add_keywords)
        b_removes = any(w in fb.suggestion.lower() for w in remove_keywords)

        if (a_adds and b_removes) or (a_removes and b_adds):
            return (
                f"{fa.category.value} suggests to add/change while "
                f"{fb.category.value} suggests to remove/simplify in the same area"
            )
        return None
