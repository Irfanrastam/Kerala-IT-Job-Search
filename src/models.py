from dataclasses import dataclass, field


@dataclass
class Job:
    title: str
    company: str
    location: str
    source: str
    source_url: str
    link: str
    posted_date: str = "Not listed"
    apply_by: str = "Not listed"
    description: str = ""
    experience: str = "Not specified"
    match_reason: str = ""
    category: str = "Other"
    verification_status: str = "UNVERIFIED"
    verification_notes: str = "Not checked"
    official_url: str = ""
    company_website: str = ""
    risk_flags: list[str] = field(default_factory=list)

    @property
    def searchable_text(self) -> str:
        return " ".join(
            [
                self.title,
                self.company,
                self.location,
                self.description,
                self.experience,
                self.category,
            ]
        ).lower()
