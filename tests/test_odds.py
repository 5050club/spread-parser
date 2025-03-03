
# Generated by Qodo Gen
from app.odds import get_teams
import elasticsearch


# Dependencies:
# pip install pytest-mock
import pytest

class TestGetTeams:

    # Successfully connect to ES and retrieve teams data
    def test_get_teams_success(self, mocker):
        # Arrange
        mock_es = mocker.patch('elasticsearch.Elasticsearch')
        mock_es_instance = mock_es.return_value
        mock_es_instance.search.return_value._body = {
            'hits': {
                'hits': [
                    {'_source': {'team_id': 1, 'name': 'Team 1'}},
                    {'_source': {'team_id': 2, 'name': 'Team 2'}}
                ]
            }
        }

        # Act
        result = get_teams()

        # Assert
        mock_es.assert_called_once_with(
            "https://localhost:9200/",
            verify_certs=False,
            ssl_show_warn=False,
            api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ=="
        )
        mock_es_instance.search.assert_called_once_with(index="teams", size=100)
        assert len(result) == 2

    # Handle ES connection failure
    def test_get_teams_connection_error(self, mocker):
        # Arrange
        mock_es = mocker.patch('elasticsearch.Elasticsearch')
        mock_es_instance = mock_es.return_value
        mock_es_instance.search.side_effect = elasticsearch.ConnectionError("Connection failed")

        # Act & Assert
        with pytest.raises(elasticsearch.ConnectionError) as exc_info:
            get_teams()
        assert str(exc_info.value) == "Connection failed"