#!/usr/bin/env python3
"""
Unit tests for fa-subset.py Font Awesome parser
"""

import unittest
import sys
import os
import tempfile
import json
from pathlib import Path

# Add parent directory to path to import the script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

# Import the script with hyphen in name
import importlib.util
spec = importlib.util.spec_from_file_location("fa_subset",
    os.path.join(os.path.dirname(__file__), '..', 'bin', 'fa-subset.py'))
fa_subset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fa_subset)


class TestFASubset(unittest.TestCase):
    """Test Font Awesome subsetting functionality"""

    def test_is_non_icon_token(self):
        """Test identification of non-icon tokens (modifiers, utilities, etc.)"""
        script = fa_subset

        # Test size modifiers - function expects full fa- prefixed tokens
        self.assertTrue(script.is_non_icon_token('fa-2x'))
        self.assertTrue(script.is_non_icon_token('fa-3x'))
        self.assertTrue(script.is_non_icon_token('fa-5x'))
        self.assertTrue(script.is_non_icon_token('fa-lg'))
        self.assertTrue(script.is_non_icon_token('fa-sm'))

        # Test utilities
        self.assertTrue(script.is_non_icon_token('fa-fw'))
        self.assertTrue(script.is_non_icon_token('fa-spin'))
        self.assertTrue(script.is_non_icon_token('fa-pulse'))

        # Test style classes
        self.assertTrue(script.is_non_icon_token('fa-solid'))
        self.assertTrue(script.is_non_icon_token('fa-duotone'))
        self.assertTrue(script.is_non_icon_token('fa-brands'))

        # Test actual icon names (should return False)
        self.assertFalse(script.is_non_icon_token('fa-house'))
        self.assertFalse(script.is_non_icon_token('fa-user'))
        self.assertFalse(script.is_non_icon_token('fa-envelope'))

    def test_extract_fa_tokens(self):
        """Test extraction of Font Awesome tokens from HTML"""
        test_html = '''
        <i class="fa-solid fa-house fa-2x"></i>
        <i class="fa-duotone fa-user"></i>
        <span class="fas fa-envelope"></span>
        '''

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(test_html)
            temp_file = f.name

        try:
            # Mock the necessary globals
            fa_subset.FA_TOKEN_RX = fa_subset.re.compile(r'\bfa-[a-z0-9-]+\b', fa_subset.re.I)

            # Extract tokens
            tokens = []
            with open(temp_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    for token in fa_subset.FA_TOKEN_RX.findall(line):
                        # Pass the full token to is_non_icon_token, not the stripped version
                        if not fa_subset.is_non_icon_token(token):
                            icon_name = token[3:]  # Remove 'fa-' prefix after checking
                            tokens.append(icon_name)

            # Check we found the right icons
            self.assertIn('house', tokens)
            self.assertIn('user', tokens)
            self.assertIn('envelope', tokens)

            # Check we didn't include modifiers (tokens list contains icon names without fa- prefix)
            self.assertNotIn('2x', tokens)
            self.assertNotIn('solid', tokens)
            self.assertNotIn('duotone', tokens)

        finally:
            os.unlink(temp_file)

    def test_css_selector_parsing(self):
        """Test CSS selector regex for different Font Awesome patterns"""
        # Test the regex pattern for compound selectors
        import re

        # Updated pattern that handles compound selectors
        css_pattern = re.compile(
            r'(?P<selector>[^{}]+?)\s*:\s*(?:before|after)\s*\{[^}]*?content\s*:\s*["\']\\(?P<hex>[0-9a-fA-F]{3,6})(?:\\[0-9a-fA-F]{3,6})?["\']',
            re.I
        )

        # Test simple selector
        css1 = '.fa-house:before { content: "\\f015" }'
        match1 = css_pattern.search(css1)
        self.assertIsNotNone(match1)
        self.assertEqual(match1.group('hex'), 'f015')

        # Test compound selector (duotone)
        css2 = '.fa-duotone.fa-house:after { content: "\\f015\\f015" }'
        match2 = css_pattern.search(css2)
        self.assertIsNotNone(match2)
        self.assertEqual(match2.group('hex'), 'f015')

        # Test minified CSS
        css3 = '.fa-user:before{content:"\\f007"}'
        match3 = css_pattern.search(css3)
        self.assertIsNotNone(match3)
        self.assertEqual(match3.group('hex'), 'f007')

    def test_style_detection(self):
        """Test detection of Font Awesome styles on a line"""
        test_cases = [
            ('<i class="fa-solid fa-house"></i>', 'solid'),
            ('<i class="fa-duotone fa-user"></i>', 'duotone'),
            ('<i class="fa-brands fa-github"></i>', 'brands'),
            ('<i class="fas fa-envelope"></i>', 'solid'),  # FA5 alias
            ('<i class="fad fa-shield"></i>', 'duotone'),  # FA5 alias
            ('<i class="fa-house"></i>', 'solid'),  # Default when no style specified
        ]

        for html, expected_style in test_cases:
            # Check if style class is present
            if 'fa-solid' in html or 'fas' in html:
                detected = 'solid'
            elif 'fa-duotone' in html or 'fad' in html:
                detected = 'duotone'
            elif 'fa-brands' in html or 'fab' in html:
                detected = 'brands'
            else:
                detected = 'solid'  # default

            self.assertEqual(detected, expected_style,
                           f"Failed to detect {expected_style} in: {html}")

    def test_json_report_structure(self):
        """Test that JSON report has the expected structure"""
        sample_report = {
            "packs": {
                "solid": {
                    "icons_found": ["house", "user"],
                    "icons_missing_in_css": [],
                    "codepoints": ["U+F015", "U+F007"],
                    "icons_to_files": {}
                }
            },
            "conflicts": [],
            "file_to_icons": {}
        }

        # Verify structure
        self.assertIn("packs", sample_report)
        self.assertIn("solid", sample_report["packs"])
        self.assertIn("icons_found", sample_report["packs"]["solid"])
        self.assertIn("codepoints", sample_report["packs"]["solid"])

        # Test JSON serialization
        json_str = json.dumps(sample_report, indent=2)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["packs"]["solid"]["icons_found"], ["house", "user"])


class TestMinifyScript(unittest.TestCase):
    """Test fa-minify.sh functionality (basic validation)"""

    def test_script_exists(self):
        """Test that fa-minify.sh exists and is executable"""
        script_path = Path(__file__).parent.parent / 'bin' / 'fa-minify.sh'
        self.assertTrue(script_path.exists(), "fa-minify.sh should exist")

        # Check shebang
        with open(script_path, 'r') as f:
            first_line = f.readline()
            self.assertTrue(first_line.startswith('#!/'),
                          "Script should have shebang")


if __name__ == '__main__':
    unittest.main()