# models/user_story.py
"""User Story Model for Feature Pipeline"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import json
from enum import Enum


class StoryPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StoryStatus(Enum):
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class AcceptanceCriteria:
    """Individual acceptance criterion for a user story"""
    description: str
    is_met: bool = False
    verification_steps: List[str] = field(default_factory=list)


@dataclass
class UserStory:
    """User Story model for Feature Pipeline"""
    title: str
    description: str
    as_a: str  # "As a [role]"
    i_want: str  # "I want [feature]"
    so_that: str  # "So that [benefit]"
    acceptance_criteria: List[AcceptanceCriteria]
    priority: StoryPriority = StoryPriority.MEDIUM
    status: StoryStatus = StoryStatus.DRAFT
    story_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_effort: Optional[int] = None  # Story points
    actual_effort: Optional[int] = None
    context_documents: List[str] = field(default_factory=list)
    implementation_notes: str = ""
    
    def to_dict(self) -> Dict:
        """Convert story to dictionary"""
        return {
            "story_id": self.story_id,
            "title": self.title,
            "description": self.description,
            "as_a": self.as_a,
            "i_want": self.i_want,
            "so_that": self.so_that,
            "acceptance_criteria": [
                {
                    "description": ac.description,
                    "is_met": ac.is_met,
                    "verification_steps": ac.verification_steps
                }
                for ac in self.acceptance_criteria
            ],
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "dependencies": self.dependencies,
            "estimated_effort": self.estimated_effort,
            "actual_effort": self.actual_effort,
            "context_documents": self.context_documents,
            "implementation_notes": self.implementation_notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserStory':
        """Create story from dictionary"""
        data = data.copy()
        data["priority"] = StoryPriority(data["priority"])
        data["status"] = StoryStatus(data["status"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        data["acceptance_criteria"] = [
            AcceptanceCriteria(
                description=ac["description"],
                is_met=ac["is_met"],
                verification_steps=ac["verification_steps"]
            )
            for ac in data["acceptance_criteria"]
        ]
        return cls(**data)
    
    def to_prompt(self) -> str:
        """Convert to a prompt format for LLM consumption"""
        ac_text = "\n".join([
            f"  - {ac.description}" for ac in self.acceptance_criteria
        ])
        return f"""
# User Story: {self.title}

## Story Format
As a {self.as_a},
I want {self.i_want},
So that {self.so_that}.

## Description
{self.description}

## Acceptance Criteria
{ac_text}

## Context
Priority: {self.priority.value}
Tags: {', '.join(self.tags) if self.tags else 'None'}
Dependencies: {', '.join(self.dependencies) if self.dependencies else 'None'}
"""
    
    def validate(self) -> List[str]:
        """Validate the story and return list of issues"""
        issues = []
        
        if not self.title:
            issues.append("Title is required")
        if not self.as_a:
            issues.append("'As a' role is required")
        if not self.i_want:
            issues.append("'I want' feature description is required")
        if not self.so_that:
            issues.append("'So that' benefit is required")
        if not self.acceptance_criteria:
            issues.append("At least one acceptance criterion is required")
        
        return issues