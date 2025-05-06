# from i2c/models/story_manager.py
"""Story Manager for User Story processing and persistence"""

import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from i2c.models.user_story import UserStory, StoryStatus, StoryPriority
from i2c.agents.knowledge.knowledge_manager import ExternalKnowledgeManager
from i2c.cli.controller import canvas


class StoryManager:
    """Manages user stories for the Feature Pipeline"""
    
    def __init__(self, storage_path: Path, knowledge_manager: ExternalKnowledgeManager):
        self.storage_path = storage_path
        self.knowledge_manager = knowledge_manager
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.stories_file = self.storage_path / "stories.json"
        self.stories: Dict[str, UserStory] = {}
        self._load_stories()
    
    def _load_stories(self) -> None:
        """Load stories from storage"""
        if self.stories_file.exists():
            try:
                with open(self.stories_file, 'r') as f:
                    data = json.load(f)
                    self.stories = {
                        story_id: UserStory.from_dict(story_data)
                        for story_id, story_data in data.items()
                    }
                canvas.info(f"Loaded {len(self.stories)} user stories")
            except Exception as e:
                canvas.error(f"Failed to load stories: {e}")
                self.stories = {}
        else:
            self.stories = {}
    
    def _save_stories(self) -> None:
        """Save stories to storage"""
        try:
            data = {
                story_id: story.to_dict()
                for story_id, story in self.stories.items()
            }
            with open(self.stories_file, 'w') as f:
                json.dump(data, f, indent=2)
            canvas.info(f"Saved {len(self.stories)} user stories")
        except Exception as e:
            canvas.error(f"Failed to save stories: {e}")
    
    def create_story(self, story: UserStory) -> str:
        """Create a new user story"""
        # Validate story
        issues = story.validate()
        if issues:
            raise ValueError(f"Story validation failed: {', '.join(issues)}")
        
        # Generate ID if not provided
        if not story.story_id:
            story.story_id = f"story_{uuid.uuid4().hex[:8]}"
        
        # Set timestamps
        story.created_at = datetime.now()
        story.updated_at = datetime.now()
        
        # Store story
        self.stories[story.story_id] = story
        self._save_stories()
        
        # Ingest story into knowledge base
        self._ingest_story_knowledge(story)
        
        canvas.success(f"Created user story: {story.story_id}")
        return story.story_id
    
    def _ingest_story_knowledge(self, story: UserStory) -> None:
        """Ingest story into knowledge base for RAG"""
        try:
            # Convert story to knowledge format
            content = story.to_prompt()
            metadata = {
                "category": "user_story",
                "story_id": story.story_id,
                "priority": story.priority.value,
                "status": story.status.value,
                "last_updated": datetime.now().isoformat()
            }
            
            # Ingest into knowledge base
            success = self.knowledge_manager.ingest_knowledge(
                source=f"story_{story.story_id}",
                content=content,
                metadata=metadata
            )
            
            if success:
                canvas.info(f"Ingested story {story.story_id} into knowledge base")
            else:
                canvas.warning(f"Failed to ingest story {story.story_id} into knowledge base")
                
        except Exception as e:
            canvas.error(f"Error ingesting story knowledge: {e}")
    
    def get_story(self, story_id: str) -> Optional[UserStory]:
        """Get a story by ID"""
        return self.stories.get(story_id)
    
    def update_story(self, story_id: str, updates: Dict) -> bool:
        """Update an existing story"""
        if story_id not in self.stories:
            canvas.error(f"Story {story_id} not found")
            return False
        
        story = self.stories[story_id]
        for key, value in updates.items():
            if hasattr(story, key):
                setattr(story, key, value)
        
        story.updated_at = datetime.now()
        self._save_stories()
        self._ingest_story_knowledge(story)
        
        canvas.success(f"Updated story: {story_id}")
        return True
    
    def update_story_status(self, story_id: str, status: StoryStatus) -> bool:
        """Update story status"""
        return self.update_story(story_id, {"status": status})
    
    def list_stories(self, status: Optional[StoryStatus] = None, 
                    priority: Optional[StoryPriority] = None) -> List[UserStory]:
        """List stories with optional filters"""
        stories = list(self.stories.values())
        
        if status:
            stories = [s for s in stories if s.status == status]
        
        if priority:
            stories = [s for s in stories if s.priority == priority]
        
        # Sort by priority and creation date
        priority_order = {
            StoryPriority.CRITICAL: 0,
            StoryPriority.HIGH: 1,
            StoryPriority.MEDIUM: 2,
            StoryPriority.LOW: 3
        }
        
        stories.sort(key=lambda s: (priority_order[s.priority], s.created_at))
        return stories
    
    def get_ready_stories(self) -> List[UserStory]:
        """Get stories that are ready for implementation"""
        return self.list_stories(status=StoryStatus.READY)
    
    def get_story_context(self, story_id: str) -> Optional[List[Dict]]:
        """Retrieve context knowledge for a story"""
        story = self.get_story(story_id)
        if not story:
            return None
        
        # Build query from story content
        query = f"{story.title} {story.description} {story.i_want}"
        
        # Retrieve relevant knowledge
        return self.knowledge_manager.retrieve_knowledge(query, limit=5)