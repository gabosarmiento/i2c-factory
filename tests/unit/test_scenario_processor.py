import pytest
from unittest.mock import patch

# Import your actual ScenarioProcessor here
from i2c.workflow.scenario_processor import ScenarioProcessor


class DummyScenarioProcessor(ScenarioProcessor):
    def __init__(self):
        # bypass base class init logic
        self.project_name = None

    def _handle_knowledge_ingestion(self, document_path, metadata, is_folder):
        if not self.project_name:
            raise ValueError(
                "No 'project_name' defined. Explicit project name is required to define a knowledge space. "
                "Avoid using deprecated fallback to 'global'."
            )

        from i2c.agents.knowledge.enhanced_knowledge_ingestor import EnhancedKnowledgeIngestorAgent

        knowledge_space = self.project_name
        ingestor = EnhancedKnowledgeIngestorAgent(
            knowledge_space=knowledge_space,
            metadata=metadata,
            use_cache=True,
            recursive=is_folder
        )
        stats = ingestor.execute(document_path)
        print(f"[Knowledge Ingestion] Completed with stats: {stats}")
        return stats


def test_knowledge_ingestion_without_project_name_should_fail():
    processor = DummyScenarioProcessor()
    processor.project_name = None  # simulate missing project name

    with pytest.raises(ValueError) as exc_info:
        processor._handle_knowledge_ingestion("some/fake/path", metadata={}, is_folder=True)

    assert "Explicit project name is required" in str(exc_info.value)


@patch("i2c.agents.knowledge.enhanced_knowledge_ingestor.EnhancedKnowledgeIngestorAgent")
def test_knowledge_ingestion_with_project_name(mock_ingestor_class):
    mock_ingestor = mock_ingestor_class.return_value
    mock_ingestor.execute.return_value = {"files_processed": 1}

    processor = DummyScenarioProcessor()
    processor.project_name = "my_test_project"

    result = processor._handle_knowledge_ingestion("some/fake/path", metadata={"type": "guide"}, is_folder=True)

    assert result == {"files_processed": 1}
    mock_ingestor_class.assert_called_once()
    mock_ingestor.execute.assert_called_once_with("some/fake/path")
