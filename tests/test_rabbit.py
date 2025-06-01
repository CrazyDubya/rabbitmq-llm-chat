import pytest  # noqa: F401
from rabbit import (
    create_queue_name,
)  # Assuming rabbit.py is in the root and PYTHONPATH is set up correctly for tests


def test_create_queue_name():
    topic = "sports"
    subtopic = "football"
    model_name = "haiku"
    expected_queue_name = "sports.football.haiku"
    assert create_queue_name(topic, subtopic, model_name) == expected_queue_name


def test_create_queue_name_with_empty_strings():
    topic = ""
    subtopic = ""
    model_name = ""
    expected_queue_name = ".."
    assert create_queue_name(topic, subtopic, model_name) == expected_queue_name


def test_create_queue_name_with_numbers():
    topic = "topic1"
    subtopic = "sub2"
    model_name = "model3"
    expected_queue_name = "topic1.sub2.model3"
    assert create_queue_name(topic, subtopic, model_name) == expected_queue_name
