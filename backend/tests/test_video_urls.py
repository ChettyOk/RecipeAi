from app.video_urls import detect_platform, normalize_video_url, validate_video_url


def test_youtube_shorts():
    assert validate_video_url("https://www.youtube.com/shorts/abc123XYZ01") == (
        "https://www.youtube.com/watch?v=abc123XYZ01"
    )


def test_youtube_channel_shorts():
    assert validate_video_url("https://www.youtube.com/@chef/shorts/abc123XYZ01") == (
        "https://www.youtube.com/watch?v=abc123XYZ01"
    )


def test_youtu_be():
    assert normalize_video_url("https://youtu.be/dQw4w9WgXcQ") == (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )


def test_tiktok_unchanged():
    url = "https://www.tiktok.com/@user/video/7123456789"
    assert validate_video_url(url) == url


def test_detect_platform():
    assert detect_platform("https://youtu.be/x") == "youtube"
    assert detect_platform("https://www.tiktok.com/x") == "tiktok"
