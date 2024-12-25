def dynamic_mock_osrm(*args, **kwargs):
    url = args[0]
    coords = url.split('/driving/')[-1].split('?')[0].split(';')
    n = len(coords)
    distances = [[1000 * abs(i - j) for j in range(n)] for i in range(n)]
    durations = [[600 * abs(i - j) for j in range(n)] for i in range(n)]

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"distances": distances, "durations": durations}

    return MockResponse()


class MockResponseInvalid:
    def raise_for_status(self):
        pass  # Не выбрасывать исключение

    def json(self):
        return {"invalid_key": []}
