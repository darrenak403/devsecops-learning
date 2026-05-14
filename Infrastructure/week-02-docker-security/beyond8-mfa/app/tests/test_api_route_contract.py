from app.api.v1.api import api_router


def test_critical_api_routes_are_stable() -> None:
    route_paths = {route.path for route in api_router.routes}
    assert "/v1/subjects" in route_paths
    assert "/v1/subjects/{slug}/bank" in route_paths
    assert "/v1/admin/question-sources/subjects" in route_paths
    assert "/v1/admin/question-sources/subjects/{slug}/upload" in route_paths
    assert "/v1/admin/question-sources/subjects/{slug}/sources/{source_id}/questions" in route_paths
    assert "/v1/admin/question-sources/subjects/{slug}/sources/{source_id}/questions/{ordinal}" in route_paths
    assert "/stats/otp-verifications" in route_paths
    assert "/otp/generate" in route_paths


def test_dashboard_and_stats_routes_coexist() -> None:
    route_paths = {route.path for route in api_router.routes}
    assert "/otp-verifications" in route_paths
    assert "/otp-verifications/history" in route_paths
    assert "/stats/otp-verifications/history" in route_paths
