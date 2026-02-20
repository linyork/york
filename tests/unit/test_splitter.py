import pytest

from src.utils.splitter import MarkdownSplitter
from src.constants import KNOWLEDGE_CONSTANTS

def test_empty_content():
    splitter = MarkdownSplitter("test_doc")
    chunks = splitter.split("")
    assert len(chunks) == 0

def test_no_headers_long():
    splitter = MarkdownSplitter("test_doc")
    content = "Line 1\nLine 2\nLine 3"
    chunks = splitter.split(content)
    assert len(chunks) == 1
    assert chunks[0].header_path == "(Root)"
    assert chunks[0].content == content

def test_no_headers_short():
    splitter = MarkdownSplitter("test_doc")
    # MIN_CHUNK_LINES was 3, but we removed the line count check
    # to avoid data loss. Now it only depends on character count (>= 10).
    content = "Line 1\nLine 2" # Length 13
    chunks = splitter.split(content)
    assert len(chunks) == 1
    assert chunks[0].content == content

def test_headers_only_no_content():
    splitter = MarkdownSplitter("test_doc")
    content = "# H1\n## H2\n### H3"
    chunks = splitter.split(content)
    # Each potential chunk only has 1 line (the header), so they are all dropped
    assert len(chunks) == 0

def test_nested_headers_breadcrumb():
    splitter = MarkdownSplitter("test_doc")
    content = """# H1
content line 1
content line 2
## H1.1
content line 1
content line 2
### H1.1.1
content line 1
content line 2
"""
    chunks = splitter.split(content)
    assert len(chunks) == 3
    assert chunks[0].header_path == "H1"
    assert chunks[1].header_path == "H1 > H1.1"
    assert chunks[2].header_path == "H1 > H1.1 > H1.1.1"

def test_skipping_levels():
    splitter = MarkdownSplitter("test_doc")
    content = """# H1
content line 1
content line 2
### H3
content line 1
content line 2
"""
    chunks = splitter.split(content)
    assert len(chunks) == 2
    assert chunks[0].header_path == "H1"
    assert chunks[1].header_path == "H1 > H3"

def test_resetting_levels():
    splitter = MarkdownSplitter("test_doc")
    content = """# H1
content line 1
content line 2
## H1.1
content line 1
content line 2
# H2
content line 1
content line 2
"""
    chunks = splitter.split(content)
    assert len(chunks) == 3
    assert chunks[0].header_path == "H1"
    assert chunks[1].header_path == "H1 > H1.1"
    assert chunks[2].header_path == "H2"

def test_header_with_special_characters():
    splitter = MarkdownSplitter("test_doc")
    content = """# Header with symbols @#$%
line 1
line 2
line 3
"""
    chunks = splitter.split(content)
    assert len(chunks) == 1
    assert chunks[0].header_path == "Header with symbols @#$%"

def test_header_with_extra_spaces():
    splitter = MarkdownSplitter("test_doc")
    content = """#   Header with spaces
line 1
line 2
line 3
"""
    chunks = splitter.split(content)
    assert len(chunks) == 1
    assert chunks[0].header_path == "Header with spaces"

def test_malformed_header():
    splitter = MarkdownSplitter("test_doc")
    # No space after #
    content = """#NoSpace
line 1
line 2
line 3
"""
    chunks = splitter.split(content)
    assert len(chunks) == 1
    assert chunks[0].header_path == "(Root)"
    assert "#NoSpace" in chunks[0].content

def test_content_too_short_char_count():
    splitter = MarkdownSplitter("test_doc")
    # Content lines >= 3, but total chars < 10
    content = "# H1\na\nb"
    chunks = splitter.split(content)
    assert len(chunks) == 0

def test_id_consistency():
    splitter = MarkdownSplitter("test_doc")
    content = "# H1\nline 1\nline 2\nline 3"
    chunks1 = splitter.split(content)
    chunks2 = splitter.split(content)
    assert chunks1[0].id == chunks2[0].id

def test_id_uniqueness():
    splitter = MarkdownSplitter("test_doc")
    content = """# H1
line 1
line 2
line 3
# H2
line 1
line 2
line 3
"""
    chunks = splitter.split(content)
    assert chunks[0].id != chunks[1].id

def test_long_header_only():
    splitter = MarkdownSplitter("test_doc")
    content = "# This is a very long header that should be preserved"
    chunks = splitter.split(content)
    assert len(chunks) == 1
    assert chunks[0].header_path == "This is a very long header that should be preserved"

def test_no_data_loss_for_small_sections():
    splitter = MarkdownSplitter("test_doc")
    # Using shorter headers to avoid them being captured as separate chunks
    content = """# S1
## Sub 1.1
Content for 1.1
# S2
## Sub 2.1
Content for 2.1"""
    chunks = splitter.split(content)
    # Now "# S1" and "# S2" are < 10 chars, so they should be dropped.
    # The sub-sections should be preserved.
    assert len(chunks) == 2
    assert "Sub 1.1" in chunks[0].header_path
    assert "Sub 2.1" in chunks[1].header_path
