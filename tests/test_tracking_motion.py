import time
from statistics import mean

import pytest
import config
from speedcam.tracking.motion import MotionTrack


@pytest.fixture
def mock_config(mocker):
    config_mock = mocker.MagicMock(spec=config.config.Config)
    return config_mock


def test_last_seen_is_within_timeout(mock_config):
    mock_config.event_timeout = 2000

    motion = MotionTrack(mock_config)
    motion.last_seen = time.time() - 1000
    assert not motion.has_exceeded_track_timeout()


def test_last_seen_is_exceeds_timeout(mock_config):
    mock_config.event_timeout = 100

    motion = MotionTrack(mock_config)
    motion.last_seen = time.time() - 1000
    assert motion.has_exceeded_track_timeout()


def test_tracking_count_within_limit(mock_config):
    mock_config.track_counter = 5

    motion = MotionTrack(mock_config)
    motion.track_count = 3
    assert not motion.has_track_count_exceeded_track_limit()


def test_tracking_count_exceeds_limit(mock_config):
    mock_config.track_counter = 5

    motion = MotionTrack(mock_config)
    motion.track_count = 10
    assert motion.has_track_count_exceeded_track_limit()


def test_avg_speed_calculation(mock_config):
    motion = MotionTrack(mock_config)
    motion.speed_list = [50.0, 55.2, 30.1, 70.1]

    assert motion.get_avg_speed() == mean(motion.speed_list)


def test_below_speeding_threshold(mock_config):
    mock_config.max_speed_over = 55
    motion = MotionTrack(mock_config)
    motion.speed_list = [50.0]

    assert not motion.is_object_speeding()


def test_speeding(mock_config):
    mock_config.max_speed_over = 55
    motion = MotionTrack(mock_config)
    motion.speed_list = [70.0]

    assert motion.is_object_speeding()
