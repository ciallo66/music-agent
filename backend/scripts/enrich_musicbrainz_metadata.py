"""用 MusicBrainz recording MBID 为 AcousticBrainz JSONL 补齐展示元数据。"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx

USER_AGENT = "music-agent-metadata-enricher/1.0 (https://music-agent.cloud)"
MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2/recording"


def batches(items: list[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    """按固定大小拆分记录，控制 MusicBrainz 请求长度和频率。"""
    for index in range(0, len(items), size):
        yield items[index : index + size]


def recording_metadata(recording: dict[str, Any]) -> dict[str, str | None] | None:
    """从 MusicBrainz recording 响应中提取曲名、艺术家和首个发行标题。"""
    mbid = str(recording.get("id", "")).strip()
    title = str(recording.get("title", "")).strip()
    credits = recording.get("artist-credit") or []
    artist = str(credits[0].get("name", "")).strip() if credits else ""
    releases = recording.get("releases") or []
    album = str(releases[0].get("title", "")).strip() if releases else ""
    if not mbid or not title or not artist:
        return None
    return {"mbid": mbid, "title": title, "artist": artist, "album": album or None}


def fetch_metadata(client: httpx.Client, mbids: list[str]) -> dict[str, dict[str, str | None]]:
    """一次查询一组精确 MBID，并按 MBID 返回真实元数据。"""
    query = f"rid:({' OR '.join(mbids)})"
    response: httpx.Response | None = None
    for attempt in range(5):
        response = client.get(MUSICBRAINZ_URL, params={"query": query, "fmt": "json", "limit": 100})
        if response.status_code not in {429, 502, 503, 504}:
            break
        time.sleep(2 ** (attempt + 1))
    if response is None:
        raise RuntimeError("MusicBrainz 未返回响应")
    response.raise_for_status()
    result: dict[str, dict[str, str | None]] = {}
    for recording in response.json().get("recordings", []):
        metadata = recording_metadata(recording)
        if metadata is not None and metadata["mbid"] in mbids:
            result[str(metadata["mbid"])] = metadata
    return result


def enrich_file(source: Path, destination: Path, batch_size: int = 20) -> dict[str, int]:
    """读取特征 JSONL，补齐真实元数据，并丢弃无法核验的记录。"""
    records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line]
    enriched: list[dict[str, Any]] = []
    unresolved = 0
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30) as client:
        groups = list(batches(records, batch_size))
        for index, group in enumerate(groups):
            metadata_by_mbid = fetch_metadata(client, [str(item.get("mbid", "")) for item in group])
            for item in group:
                metadata = metadata_by_mbid.get(str(item.get("mbid", "")))
                if metadata is None:
                    unresolved += 1
                    continue
                item.update({key: value for key, value in metadata.items() if key != "mbid"})
                enriched.append(item)
            if index + 1 < len(groups):
                time.sleep(1.1)
    with destination.open("w", encoding="utf-8") as output:
        for item in enriched:
            output.write(json.dumps(item, ensure_ascii=False) + "\n")
    return {"enriched": len(enriched), "unresolved": unresolved}


def main() -> None:
    """解析输入输出路径并执行 MusicBrainz 元数据补全。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()
    print(enrich_file(args.source, args.destination, args.batch_size))


if __name__ == "__main__":
    main()
