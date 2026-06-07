from interpiped.events import schemas


def test_schema_version_present() -> None:
    assert schemas.schema_version == "1.0"


def test_get_event_schemas_contains_models() -> None:
    mapping = schemas.get_event_schemas()
    expected = [
        "BaseEvent",
        "IssueCreated",
        "TaskCreated",
        "TaskCompleted",
        "TestPassed",
        "TestFailed",
        "ArchitectureApproved",
        "ArchitectureRejected",
        "PullRequestCreated",
        "PullRequestFailed",
    ]
    for name in expected:
        assert name in mapping
