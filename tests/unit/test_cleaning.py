from __future__ import annotations

from app.core import cleaning
from app.core.schemas import Page


def make_pages(*texts: str) -> list[Page]:
    return [
        Page(number=index, text=text, char_count=len(text.strip()))
        for index, text in enumerate(texts, start=1)
    ]


def test_normalize_unicode_folds_ligatures_and_quotes():
    assert cleaning.normalize_unicode("\ufb01nance \u2019s \u2014 dash") == "finance 's - dash"


def test_clean_line_unifies_bullets():
    assert cleaning.clean_line("\u2022   Built an API") == "- Built an API"
    assert cleaning.clean_line("*  Built an API") == "- Built an API"
    assert cleaning.clean_line("-\tBuilt an API") == "- Built an API"


def test_clean_line_handles_unmapped_glyph_codes():
    assert cleaning.clean_line("(cid:127) Built an API") == "- Built an API"
    assert cleaning.clean_line("Python(cid:160)and Flask") == "Python and Flask"


def test_clean_line_collapses_whitespace():
    assert cleaning.clean_line("  Python     Flask  ") == "Python Flask"


def test_clean_line_keeps_hyphenated_words_intact():
    assert cleaning.clean_line("Full-stack developer") == "Full-stack developer"


def test_build_lines_records_page_and_line_numbers():
    pages = make_pages("Alpha\nBeta", "Gamma")
    lines = cleaning.build_lines(pages)

    assert [line.text for line in lines] == ["Alpha", "Beta", "Gamma"]
    assert [line.page for line in lines] == [1, 1, 2]
    assert [line.index for line in lines] == [0, 1, 2]
    assert [line.page_line_index for line in lines] == [0, 1, 0]


def test_build_lines_keeps_original_text():
    lines = cleaning.build_lines(make_pages("\u2022  Shipped   a feature"))
    assert lines[0].text == "- Shipped a feature"
    assert lines[0].original_text == "\u2022  Shipped   a feature"


def test_build_lines_joins_hyphenated_line_wraps():
    lines = cleaning.build_lines(make_pages("Java-\nScript and Type-\nScript"))
    assert [line.text for line in lines] == ["JavaScript and TypeScript"]


def test_build_lines_collapses_repeated_blank_lines():
    lines = cleaning.build_lines(make_pages("Alpha\n\n\n\nBeta"))
    assert [line.text for line in lines] == ["Alpha", "", "Beta"]


def test_build_lines_strips_leading_and_trailing_blanks():
    lines = cleaning.build_lines(make_pages("\n\nAlpha\n\n"))
    assert [line.text for line in lines] == ["Alpha"]


def test_build_lines_drops_running_headers_and_page_numbers():
    pages = make_pages(
        "Vaishnavi Daida - Resume\nSKILLS\nPython\n1",
        "Vaishnavi Daida - Resume\nEDUCATION\nB.Tech\n2",
    )
    texts = [line.text for line in cleaning.build_lines(pages)]

    assert "Vaishnavi Daida - Resume" not in texts
    assert "1" not in texts
    assert texts == ["SKILLS", "Python", "EDUCATION", "B.Tech"]


def test_build_lines_keeps_repeated_content_when_disabled():
    pages = make_pages("Header\nPython", "Header\nFlask")
    texts = [line.text for line in cleaning.build_lines(pages, drop_repeated=False)]
    assert texts.count("Header") == 2


def test_lines_to_text_round_trip():
    lines = cleaning.build_lines(make_pages("Alpha\nBeta"))
    assert cleaning.lines_to_text(lines) == "Alpha\nBeta"
