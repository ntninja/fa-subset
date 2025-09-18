#!/usr/bin/env python3
"""
Basic tests for fa-subset.py functionality
"""

import unittest
import os
import subprocess
import sys
from pathlib import Path


class TestFASubsetScript(unittest.TestCase):
    """Test fa-subset.py script basic functionality"""

    def setUp(self):
        """Set up test paths"""
        self.script_path = Path(__file__).parent.parent / 'bin' / 'fa-subset.py'
        self.examples_dir = Path(__file__).parent.parent / 'examples'

    def test_script_exists(self):
        """Test that fa-subset.py exists"""
        self.assertTrue(self.script_path.exists(),
                       f"Script should exist at {self.script_path}")

    def test_script_syntax(self):
        """Test that the script has valid Python syntax"""
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', str(self.script_path)],
            capture_output=True
        )
        self.assertEqual(result.returncode, 0,
                        "Script should have valid Python syntax")

    def test_script_help(self):
        """Test that script shows help message"""
        result = subprocess.run(
            [sys.executable, str(self.script_path), '--help'],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, "Help should exit with 0")
        self.assertIn('fa-subset', result.stdout.lower() or result.stderr.lower(),
                     "Help should mention fa-subset")
        self.assertIn('--pack', result.stdout or result.stderr,
                     "Help should mention --pack option")

    def test_sample_files_exist(self):
        """Test that example files exist"""
        sample_html = self.examples_dir / 'sample.html'
        sample_css = self.examples_dir / 'sample.css'

        self.assertTrue(sample_html.exists(),
                       f"sample.html should exist at {sample_html}")
        self.assertTrue(sample_css.exists(),
                       f"sample.css should exist at {sample_css}")


class TestFAMinifyScript(unittest.TestCase):
    """Test fa-minify.sh basic functionality"""

    def setUp(self):
        """Set up test paths"""
        self.script_path = Path(__file__).parent.parent / 'bin' / 'fa-minify.sh'

    def test_script_exists(self):
        """Test that fa-minify.sh exists"""
        self.assertTrue(self.script_path.exists(),
                       f"Script should exist at {self.script_path}")

    def test_script_executable(self):
        """Test that script has proper shebang"""
        with open(self.script_path, 'r') as f:
            first_line = f.readline()
            self.assertTrue(first_line.startswith('#!/'),
                          "Script should have shebang")
            self.assertIn('sh', first_line,
                         "Script should be a shell script")

    def test_script_has_sed_detection(self):
        """Test that script detects sed capabilities"""
        with open(self.script_path, 'r') as f:
            content = f.read()
            self.assertIn('gsed', content,
                         "Script should check for gsed")
            self.assertIn('SED=', content,
                         "Script should set SED variable")
            self.assertIn('-E', content,
                         "Script should check for -E flag support")


class TestIconParsing(unittest.TestCase):
    """Test icon parsing patterns"""

    def test_fa_token_pattern(self):
        """Test Font Awesome token regex pattern"""
        import re

        # Pattern used in the script
        pattern = re.compile(r'\bfa-[a-z0-9-]+\b', re.I)

        # Test valid tokens
        test_cases = [
            ('fa-house', True),
            ('fa-2x', True),
            ('fa-solid', True),
            ('fa-user-tie', True),
            ('fa-', False),
            ('prefix-fa-icon', True),  # This would match fa-icon part
        ]

        for text, should_match in test_cases:
            match = pattern.search(text)
            if should_match:
                self.assertIsNotNone(match, f"Should match: {text}")
            else:
                self.assertIsNone(match, f"Should not match: {text}")

    def test_css_content_pattern(self):
        """Test CSS content extraction pattern"""
        import re

        # Pattern that handles compound selectors
        pattern = re.compile(
            r'(?P<selector>[^{}]+?)\s*:\s*(?:before|after)\s*\{[^}]*?content\s*:\s*["\']\\(?P<hex>[0-9a-fA-F]{3,6})(?:\\[0-9a-fA-F]{3,6})?["\']',
            re.I
        )

        # Test cases
        test_cases = [
            ('.fa-house:before { content: "\\f015" }', 'f015'),
            ('.fa-duotone.fa-house:after { content: "\\f015\\f015" }', 'f015'),
            ('.fa-user:before{content:"\\f007"}', 'f007'),
        ]

        for css, expected_hex in test_cases:
            match = pattern.search(css)
            self.assertIsNotNone(match, f"Should match: {css}")
            self.assertEqual(match.group('hex'), expected_hex,
                           f"Should extract {expected_hex} from {css}")


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)