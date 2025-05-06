# Knowledge Management Testing Guide

This guide explains how to use the test scripts to validate your knowledge management implementation.

## Prerequisites

Before running the tests, make sure you have:

1. Installed all required dependencies:
   ```bash
   pip install sentence-transformers lancedb pyarrow agno
   ```

2. Set up your project structure with the following files in place:
   - `lean_knowledge_ingest.py`
   - `db_utils.py`
   - `cli/utils/documentation_type_selector.py`

## Running the Tests

### Option 1: Using Python Directly

The test script can be run directly with Python:

```bash
# From the project root directory
python tests/test_knowledge_management.py

# To see available options
python tests/test_knowledge_management.py --help

# To list all available tests
python tests/test_knowledge_management.py --list

# To run a specific test by number
python tests/test_knowledge_management.py --test 1

# To run a specific test by name
python tests/test_knowledge_management.py --test test_01_ingest_markdown_file
```

### Option 2: Using the Shell Script

For a more interactive experience, use the provided shell script:

```bash
# Make the script executable
chmod +x tests/run_knowledge_tests.sh

# Run the script
./tests/run_knowledge_tests.sh
```

The script will guide you through options for running all tests, specific tests, or cleaning up test data.

## Understanding the Tests

The test suite verifies several aspects of the knowledge management system:

1. **Document Ingestion**: Tests the ability to process and store various document types including Markdown, text, and JSON.

2. **Directory Processing**: Ensures documents in nested directories can be properly processed.

3. **Search Functionality**: Tests the vector search capabilities of the system.

4. **Metadata Handling**: Verifies that metadata is correctly stored and associated with documents.

5. **Content Verification**: Confirms that document content is properly preserved in the database.

## Troubleshooting

If you encounter errors during testing:

1. **Database Connection Issues**:
   - Check that LanceDB is properly installed
   - Verify that the database path is writable
   - Ensure the database tables are created with the correct schema

2. **File Processing Errors**:
   - Confirm the appropriate document readers are available
   - Check that file encoding issues are properly handled

3. **Embedding Model Issues**:
   - Verify that sentence-transformers is installed
   - Check that the embedding model 'all-MiniLM-L6-v2' is available

4. **Test File Issues**:
   - The tests create temporary files that should be automatically cleaned up
   - If files remain after testing, manually remove the temporary directory

## Modifying Tests

If you need to adapt the tests for your specific implementation:

1. Modify the `process_document` function to match your document processing approach
2. Update the database schema and connection parameters if different
3. Adjust the expected document types and metadata fields as needed

Remember that the test is designed to work with your actual implementation, so make sure the interfaces match what your code expects.