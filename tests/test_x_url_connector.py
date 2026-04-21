from hermes_pulse.connectors.x_url import XUrlConnector


def test_xurl_connector_collects_bookmarks_likes_and_reverse_chronological_home_timeline() -> None:
    responses = {
        "/2/users/me": {
            "data": {"id": "42", "username": "akita"},
        },
        "/2/users/42/bookmarks?max_results=100&tweet.fields=created_at,author_id,text": {
            "data": [
                {
                    "id": "100",
                    "text": "Saved launch thread",
                    "created_at": "2026-04-20T08:00:00Z",
                    "author_id": "7",
                }
            ],
            "includes": {"users": [{"id": "7", "username": "openai"}]},
        },
        "/2/users/42/liked_tweets?max_results=100&tweet.fields=created_at,author_id,text": {
            "data": [
                {
                    "id": "101",
                    "text": "Liked benchmark result",
                    "created_at": "2026-04-20T09:00:00Z",
                    "author_id": "8",
                }
            ],
            "includes": {"users": [{"id": "8", "username": "anthropic"}]},
        },
        "/2/users/42/timelines/reverse_chronological?max_results=100&tweet.fields=created_at,author_id,text": {
            "data": [
                {
                    "id": "102",
                    "text": "Timeline post worth scanning",
                    "created_at": "2026-04-20T10:00:00Z",
                    "author_id": "9",
                }
            ],
            "includes": {"users": [{"id": "9", "username": "xdev"}]},
        },
    }
    requested_paths: list[str] = []

    def runner(path: str, auth_type: str) -> dict:
        requested_paths.append(path)
        return responses[path]

    items = XUrlConnector(runner=runner).collect(["bookmarks", "likes", "home_timeline_reverse_chronological"])

    assert requested_paths == [
        "/2/users/me",
        "/2/users/42/bookmarks?max_results=100&tweet.fields=created_at,author_id,text",
        "/2/users/42/liked_tweets?max_results=100&tweet.fields=created_at,author_id,text",
        "/2/users/42/timelines/reverse_chronological?max_results=100&tweet.fields=created_at,author_id,text",
    ]
    assert [item.source for item in items] == ["x_bookmarks", "x_likes", "x_home_timeline_reverse_chronological"]
    assert [item.url for item in items] == [
        "https://x.com/openai/status/100",
        "https://x.com/anthropic/status/101",
        "https://x.com/xdev/status/102",
    ]
    assert items[0].intent_signals is not None and items[0].intent_signals.saved is True
    assert items[1].intent_signals is not None and items[1].intent_signals.liked is True
    assert items[2].metadata["x_signal"] == "home_timeline_reverse_chronological"
    assert items[2].provenance is not None and items[2].provenance.acquisition_mode == "official_api"


def test_xurl_connector_rejects_unknown_signal_type() -> None:
    connector = XUrlConnector(runner=lambda path, auth_type: {"data": {"id": "42", "username": "akita"}})

    try:
        connector.collect(["for_you"])
    except ValueError as exc:
        assert "Unsupported X signal type" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_xurl_connector_falls_back_to_oauth1_when_oauth2_fails() -> None:
    requests: list[tuple[str, str]] = []

    def runner(path: str, auth_type: str) -> dict:
        requests.append((auth_type, path))
        if auth_type == "oauth2":
            raise RuntimeError("oauth2 missing")
        responses = {
            "/2/users/me": {"data": {"id": "42", "username": "akita"}},
            "/2/users/42/bookmarks?max_results=100&tweet.fields=created_at,author_id,text": {
                "data": [
                    {
                        "id": "100",
                        "text": "Saved launch thread",
                        "created_at": "2026-04-20T08:00:00Z",
                        "author_id": "7",
                    }
                ],
                "includes": {"users": [{"id": "7", "username": "openai"}]},
            },
        }
        return responses[path]

    items = XUrlConnector(runner=runner).collect(["bookmarks"])

    assert requests == [
        ("oauth2", "/2/users/me"),
        ("oauth1", "/2/users/me"),
        ("oauth1", "/2/users/42/bookmarks?max_results=100&tweet.fields=created_at,author_id,text"),
    ]
    assert len(items) == 1
    assert items[0].source == "x_bookmarks"
