"""Run with RUN_MISSION_02=1 pytest tests/missions/test_mission02_future.py -q.
Intentionally failing before the class solves the mission.
"""
import os
import pytest
from app.mission02_autocomplete import suggest_cities

pytestmark = pytest.mark.skipif(os.getenv('RUN_MISSION_02') != '1', reason='Mission 02 locked')


def test_trie_prefix_search():
    assert suggest_cities('ber', ['Berlin', 'Bern', 'Bergen', 'Bonn']) == ['Bergen', 'Berlin', 'Bern']


def test_trie_empty_prefix_does_not_dump_dictionary():
    assert suggest_cities('', ['Berlin', 'Bern']) == []
