"""Tests for StudyCraft engine with mocked LLM."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from studycraft.engine import StudyCraft


def test_run_single_chapter(tmp_path: Path):
    """Test that engine can generate a single chapter with mocked LLM."""
    # Create a simple document
    doc = tmp_path / "test.txt"
    doc.write_text("Chapter 1: Introduction\nThis is the content of chapter one.")

    # Mock LLM response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "# Chapter 1: Introduction\n\n"
        "## 1. Learning Objectives\n"
        "- Understand the basics\n"
        "- Learn key concepts\n"
        "- Apply knowledge\n\n"
        "## 2. Key Concepts\n...\n\n"
        "## 3. Worked Examples\n...\n\n"
        "## 4. Practice Exercises\n...\n\n"
        "## 5. Mini Project\n...\n\n"
        "## 6. Further Reading\n...\n\n"
        "---\n\n"
        "## Chapter Quiz\n"
        "1. Question one?\n   - A) Answer A\n   - B) Answer B\n"
        "2. Question two?\n   - A) Answer A\n   - B) Answer B\n"
        "3. Question three?\n   - A) Answer A\n   - B) Answer B\n"
        "4. Question four?\n   - A) Answer A\n   - B) Answer B\n"
        "5. Question five?\n   - A) Answer A\n   - B) Answer B\n"
        "6. Question six?\n   - A) Answer A\n   - B) Answer B\n"
        "7. Question seven?\n   - A) Answer A\n   - B) Answer B\n"
        "8. Question eight?\n   - A) Answer A\n   - B) Answer B\n"
        "9. Question nine?\n   - A) Answer A\n   - B) Answer B\n"
        "10. Question ten?\n    - A) Answer A\n    - B) Answer B\n"
        "\n"
        "## Practice Exercises\n"
        "1. Exercise one?\n   - Solution: ...\n"
        "2. Exercise two?\n   - Solution: ...\n"
        "3. Exercise three?\n   - Solution: ...\n"
    )

    # Patch all external I/O: OpenAI, RAG indexing, web research
    # Note: `research` is imported in engine.py as `from .researcher import research`,
    # so we must patch it in the engine module's namespace, not the researcher module.
    with (
        patch("studycraft.engine.OpenAI") as MockOpenAI,
        patch("studycraft.engine.RAGIndex") as MockRAG,
        patch("studycraft.engine.research") as MockResearch,
    ):
        mock_client = MockOpenAI.return_value
        mock_client.chat.completions.create.return_value = mock_response
        MockRAG.return_value.query.return_value = "Relevant context from document"
        MockResearch.return_value = "Web research results"

        craft = StudyCraft(api_key="test-key", output_dir=tmp_path / "out")
        craft.rag = MockRAG.return_value  # Replace RAG instance
        # Run only chapter 1
        result = craft.run(doc, only_chapter=1, workers=1)

    # Check result contains expected formats (export: md, html, pdf/docx/epub)
    assert isinstance(result, dict)
    # Markdown file should exist
    md_files = list(Path(craft.output_dir).glob("*.md"))
    assert len(md_files) >= 1, "Markdown export missing"  # noqa: PT011
