from __future__ import annotations

from pydantic import BaseModel, Field


class LintIssue(BaseModel):
    rule_id: str
    message: str
    fragment_ref: str
    replacement_text: str | None = None


class LintResult(BaseModel):
    text: str
    issues: list[LintIssue] = Field(default_factory=list)

    @property
    def rules_applied(self) -> list[str]:
        rules: list[str] = []
        for issue in self.issues:
            if issue.rule_id not in rules:
                rules.append(issue.rule_id)
        return rules
