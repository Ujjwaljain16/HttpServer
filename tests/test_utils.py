import re
from server_lib.utils import generate_upload_filename


def test_generate_upload_filename_pattern():
    """Test that generated filename matches expected pattern."""
    filename = generate_upload_filename()
    pattern = r"^upload_\d{8}_\d{6}_[a-f0-9]{6}\.json$"
    assert re.match(pattern, filename), f"Filename {filename} doesn't match pattern {pattern}"


def test_generate_upload_filename_uniqueness():
    """Test that multiple calls generate unique filenames."""
    filenames = {generate_upload_filename() for _ in range(100)}
    assert len(filenames) == 100, "Generated filenames are not unique"
