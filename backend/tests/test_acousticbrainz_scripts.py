"""AcousticBrainz 批量数据补全与导入校验测试。"""

from scripts.enrich_musicbrainz_metadata import recording_metadata
from scripts.import_acousticbrainz_batch import has_real_metadata


def test_recording_metadata_extracts_verified_fields() -> None:
    """MusicBrainz 响应应转换为可展示的真实元数据。"""
    result = recording_metadata(
        {
            "id": "recording-id",
            "title": "真实曲名",
            "artist-credit": [{"name": "真实艺术家"}],
            "releases": [{"title": "真实专辑"}],
        }
    )

    assert result == {
        "mbid": "recording-id",
        "title": "真实曲名",
        "artist": "真实艺术家",
        "album": "真实专辑",
    }


def test_recording_metadata_rejects_missing_artist() -> None:
    """缺失艺术家的记录不能伪造成可展示内容。"""
    assert recording_metadata({"id": "recording-id", "title": "曲名"}) is None


def test_batch_import_rejects_old_placeholders() -> None:
    """旧批量文件中的占位曲名和占位艺术家必须被拒绝。"""
    assert not has_real_metadata("AcousticBrainz recording abc123", "AcousticBrainz sample")
    assert has_real_metadata("Time", "Pink Floyd")
