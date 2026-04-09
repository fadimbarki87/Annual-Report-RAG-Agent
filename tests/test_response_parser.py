from __future__ import annotations

import unittest

from api.response_parser import parse_answer_response


class ResponseParserTests(unittest.TestCase):
    def test_parses_numbered_resources_with_short_page_prefix(self) -> None:
        response = """Answer
Volkswagen Group expects its sales revenue in 2025 to exceed the previous year's figure by up to 5%.

Reporting Period
2025 (forecast)

Resources
1. Volkswagen Group, volkswagen_2024.pdf, p229
2. Volkswagen Group, volkswagen_2024.pdf, p185

Evidence
1. "We expect the sales revenue of the Volkswagen Group..." (Volkswagen Group, volkswagen_2024.pdf, p229)
2. "The operating result is projected..." (Volkswagen Group, volkswagen_2024.pdf, p185)
"""

        parsed = parse_answer_response(response)

        self.assertEqual(len(parsed["resources"]), 2)
        self.assertEqual(parsed["resources"][0]["company"], "Volkswagen Group")
        self.assertEqual(parsed["resources"][0]["source_file"], "volkswagen_2024.pdf")
        self.assertEqual(parsed["resources"][0]["page_number"], 229)
        self.assertEqual(parsed["resources"][1]["page_number"], 185)

        self.assertEqual(len(parsed["evidence"]), 2)
        self.assertEqual(parsed["evidence"][0]["page_number"], 229)
        self.assertEqual(parsed["evidence"][1]["source_file"], "volkswagen_2024.pdf")

    def test_derives_resources_from_evidence_when_resource_lines_are_empty(self) -> None:
        response = """Answer:
Volkswagen discusses lobbying activities in the sustainability governance section.

Resources:
None

Evidence:
Volkswagen Group, volkswagen_2024.pdf, p183:
"The Group represents its interests in legislative procedures and public policy dialogue through its lobbying activities."

Volkswagen Group, volkswagen_2024.pdf, p184:
"Lobbying activities are governed by internal compliance requirements and transparency rules."
"""

        parsed = parse_answer_response(response)

        self.assertEqual(len(parsed["resources"]), 2)
        self.assertEqual(parsed["resources"][0]["page_number"], 183)
        self.assertEqual(parsed["resources"][1]["page_number"], 184)
        self.assertEqual(parsed["evidence"][0]["company"], "Volkswagen Group")
        self.assertTrue(
            parsed["evidence"][0]["text"].startswith(
                '"The Group represents its interests in legislative procedures'
            )
        )

    def test_backfills_single_resource_metadata_into_plain_evidence(self) -> None:
        response = """Answer
Robert Bosch GmbH raised its scope 3 reduction target to 30 percent in absolute terms.

Resources
- Robert Bosch GmbH, bosch_2024.pdf, page 49

Evidence
"In 2024, we decided to raise our scope 3 reduction target to 30 percent in absolute terms."
"""

        parsed = parse_answer_response(response)

        self.assertEqual(len(parsed["resources"]), 1)
        self.assertEqual(parsed["evidence"][0]["company"], "Robert Bosch GmbH")
        self.assertEqual(parsed["evidence"][0]["source_file"], "bosch_2024.pdf")
        self.assertEqual(parsed["evidence"][0]["page_number"], 49)

    def test_parses_mixed_multicompany_evidence_blocks(self) -> None:
        response = """Answer
BMW Group:
BMW expects deliveries to rise slightly in 2025.

Volkswagen Group:
Volkswagen expects sales revenue to exceed the previous year's figure by up to 5%.

Reporting Period
2025 outlook.

Resources
- BMW Group, bmw_2024.pdf, p262
- Volkswagen Group, volkswagen_2024.pdf, p229

Evidence
BMW Group, bmw_2024.pdf, p262:
"Deliveries of BMW, MINI and Rolls-Royce brand vehicles are expected to rise slightly year-on-year."

Volkswagen Group, volkswagen_2024.pdf, p229:
"We expect the sales revenue of the Volkswagen Group ... to exceed the previous year's figure by up to 5% in 2025."
"""

        parsed = parse_answer_response(response)

        self.assertEqual(len(parsed["resources"]), 2)
        self.assertEqual(parsed["evidence"][0]["source_file"], "bmw_2024.pdf")
        self.assertEqual(parsed["evidence"][0]["page_number"], 262)
        self.assertEqual(parsed["evidence"][1]["company"], "Volkswagen Group")
        self.assertEqual(parsed["evidence"][1]["page_number"], 229)


if __name__ == "__main__":
    unittest.main()
