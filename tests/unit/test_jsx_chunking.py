import pytest
from pathlib import Path
from i2c.agents.modification_team.chunkers.jsx_code import JSXCodeChunkingStrategy
from agno.document.base import Document

def test_jsx_chunking_react_components():
    """Test JSX chunking with React components"""
    
    jsx_content = """
import React, { useState, useEffect } from 'react';
import './SnippetEditor.css';

const SnippetEditor = ({ snippet, onSave, onCancel }) => {
  const [code, setCode] = useState(snippet?.content || '');
  const [language, setLanguage] = useState(snippet?.language || 'javascript');
  const [title, setTitle] = useState(snippet?.title || '');

  useEffect(() => {
    if (snippet) {
      setCode(snippet.content);
      setLanguage(snippet.language);
      setTitle(snippet.title);
    }
  }, [snippet]);

  const handleSave = () => {
    onSave({
      id: snippet?.id,
      title,
      content: code,
      language,
      createdAt: snippet?.createdAt || new Date().toISOString()
    });
  };

  return (
    <div className="snippet-editor">
      <h2>{snippet ? 'Edit Snippet' : 'Create New Snippet'}</h2>
      <div className="form-group">
        <label htmlFor="title">Title:</label>
        <input
          type="text"
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Enter snippet title"
        />
      </div>
    </div>
  );
};

export default SnippetEditor;

// Helper function
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString();
};

// Custom hook
const useSnippetValidation = (snippet) => {
  const [isValid, setIsValid] = useState(false);
  
  useEffect(() => {
    setIsValid(snippet.title && snippet.content);
  }, [snippet]);
  
  return isValid;
};
"""

    # Create document
    document = Document(
        content=jsx_content,
        meta_data={'file_path': 'SnippetEditor.jsx'}
    )
    
    # Create JSX chunker
    chunker = JSXCodeChunkingStrategy()
    
    # Chunk the content
    chunks = chunker.chunk(document)
    
    print(f"📦 Generated {len(chunks)} JSX chunks")
    
    # Should find multiple chunks
    assert len(chunks) > 1, "Should extract multiple JSX chunks"
    
    # Check chunk types and names
    chunk_names = [chunk.meta_data.get('chunk_name') for chunk in chunks]
    chunk_types = [chunk.meta_data.get('chunk_type') for chunk in chunks]
    
    print(f"🔍 Chunk names: {chunk_names}")
    print(f"🏷️ Chunk types: {chunk_types}")
    
    # Should identify React component
    assert 'SnippetEditor' in chunk_names, "Should identify main React component"
    
    # Should identify helper function
    assert 'formatDate' in chunk_names, "Should identify helper function"
    
    # Should identify custom hook
    assert 'useSnippetValidation' in chunk_names, "Should identify custom hook"
    
    # Check component types
    assert 'component' in chunk_types or 'arrow_function' in chunk_types, "Should identify component type"
    assert 'hook' in chunk_types, "Should identify hook type"
    
    # Verify chunk content
    main_component_chunk = next((c for c in chunks if c.meta_data.get('chunk_name') == 'SnippetEditor'), None)
    assert main_component_chunk is not None, "Should have main component chunk"
    assert 'useState' in main_component_chunk.content, "Component chunk should contain React hooks"
    assert 'return (' in main_component_chunk.content, "Component chunk should contain JSX return"
    
    print("✅ JSX chunking working correctly")


def test_jsx_chunking_class_components():
    """Test JSX chunking with class components"""
    
    class_jsx_content = """
import React, { Component } from 'react';

class TaskList extends Component {
  constructor(props) {
    super(props);
    this.state = {
      tasks: [],
      loading: true
    };
  }

  componentDidMount() {
    this.fetchTasks();
  }

  fetchTasks = async () => {
    try {
      const response = await fetch('/api/tasks');
      const tasks = await response.json();
      this.setState({ tasks, loading: false });
    } catch (error) {
      console.error('Error fetching tasks:', error);
      this.setState({ loading: false });
    }
  };

  render() {
    const { tasks, loading } = this.state;
    
    if (loading) {
      return <div>Loading...</div>;
    }

    return (
      <div className="task-list">
        {tasks.map(task => (
          <div key={task.id} className="task-item">
            {task.title}
          </div>
        ))}
      </div>
    );
  }
}

export default TaskList;
"""

    document = Document(
        content=class_jsx_content,
        meta_data={'file_path': 'TaskList.jsx'}
    )
    
    chunker = JSXCodeChunkingStrategy()
    chunks = chunker.chunk(document)
    
    print(f"📦 Generated {len(chunks)} chunks from class component")
    
    # Should identify class component
    chunk_names = [chunk.meta_data.get('chunk_name') for chunk in chunks]
    chunk_types = [chunk.meta_data.get('chunk_type') for chunk in chunks]
    
    print(f"🔍 Chunk names: {chunk_names}")
    print(f"🏷️ Chunk types: {chunk_types}")
    
    assert 'TaskList' in chunk_names, "Should identify class component"
    assert 'class_component' in chunk_types, "Should identify as class component"
    
    print("✅ Class component JSX chunking working")


def test_jsx_chunking_fallback():
    """Test JSX chunking fallback for unrecognized patterns"""
    
    weird_jsx = """
// Some weird JSX that doesn't match patterns
const weirdStuff = "hello";
let x = 5;
"""

    document = Document(
        content=weird_jsx,
        meta_data={'file_path': 'weird.jsx'}
    )
    
    chunker = JSXCodeChunkingStrategy()
    chunks = chunker.chunk(document)
    
    # Should still create a chunk (fallback)
    assert len(chunks) >= 1, "Should create at least one fallback chunk"
    
    # Should have jsx_file type as fallback
    assert chunks[0].meta_data.get('chunk_type') == 'jsx_file', "Should use jsx_file fallback type"
    
    print("✅ JSX fallback chunking working")


if __name__ == "__main__":
    print("Testing JSX chunking...")
    test_jsx_chunking_react_components()
    test_jsx_chunking_class_components() 
    test_jsx_chunking_fallback()
    print("✅ All JSX chunking tests passed!")