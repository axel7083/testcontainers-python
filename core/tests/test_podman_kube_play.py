from pathlib import Path

from testcontainers.podman import KubePlay

FIXTURES = Path(__file__).parent.joinpath("podman_fixtures", "kube_play")

def test_podman_kube_play():
    basic = KubePlay(
        kube_play_file=FIXTURES.joinpath("basic", "play.yaml"),
        replace=True,
    )

    with basic:
        assert len(basic.get_pods()) == 1
