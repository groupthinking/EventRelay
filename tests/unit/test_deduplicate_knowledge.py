import json

from scripts.maintenance.deduplicate_knowledge import KnowledgeDeduplicator


def test_knowledge_deduplicator_run(tmp_path):
    # Setup mock database JSON
    mock_db = {
        "technologies": {
            "docker": {
                "name": "Docker",
                "count": 2,
                "first_seen": "2025-11-25T02:51:31.861635",
                "videos": ["video_1", "video_2"]
            },
            "containers": {
                "name": "containers",
                "count": 1,
                "first_seen": "2025-12-01T10:35:06.439149",
                "videos": ["video_2"]
            }
        },
        "videos": [
            {
                "id": "video_1",
                "title": "Test Video 1",
                "url": "https://youtube.com/watch?v=video_1",
                "technologies": ["Docker"],
                "captured_at": "2025-11-25T02:51:31.861617"
            },
            {
                "id": "video_1",  # Duplicate entry
                "title": "Test Video 1",
                "url": "https://youtube.com/watch?v=video_1",
                "technologies": ["Docker"],
                "captured_at": "2025-11-25T03:00:00.000000"
            },
            {
                "id": "video_2",
                "title": "Test Video 2",
                "url": "https://youtube.com/watch?v=video_2",
                "technologies": ["containers"],
                "captured_at": "2025-12-01T10:35:06.439111"
            }
        ],
        "capabilities": [
            {
                "id": 1,
                "technology": "containers",
                "name": "Generate container integration"
            }
        ]
    }

    db_file = tmp_path / "test_knowledge.json"
    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(mock_db, f)

    deduplicator = KnowledgeDeduplicator(str(db_file))
    assert deduplicator.load() is True

    # Run without consolidation first
    stats = deduplicator.run_deduplication(dry_run=False, consolidate_similar=False)
    assert stats["original_videos"] == 3
    assert stats["deduplicated_videos"] == 2
    assert stats["original_techs"] == 2
    assert stats["deduplicated_techs"] == 2

    # Check database was modified on disk
    with open(db_file, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["videos"]) == 2
    assert "docker" in data["technologies"]
    assert "containers" in data["technologies"]

    # Now run with consolidation
    stats_c = deduplicator.run_deduplication(dry_run=False, consolidate_similar=True)
    assert stats_c["deduplicated_techs"] == 1
    assert "containers consolidated into docker" in stats_c["consolidated_similar"]

    with open(db_file, encoding="utf-8") as f:
        data_c = json.load(f)
    assert "containers" not in data_c["technologies"]
    assert "docker" in data_c["technologies"]
    # Docker count should include consolidated containers video (video_2)
    assert data_c["technologies"]["docker"]["count"] == 2
