from src.notifications.prices import fetch_yahoo_prices


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def get(self, url, timeout, params=None, headers=None):
        self.requests.append({"url": url, "timeout": timeout, "params": params, "headers": headers})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_fetch_yahoo_prices_parses_price_and_change_pct():
    session = FakeSession(
        [
            FakeResponse(
                {
                    "chart": {
                        "result": [
                            {
                                "meta": {
                                    "symbol": "SPYM",
                                    "regularMarketPrice": 83.0,
                                    "previousClose": 82.0,
                                    "currency": "USD",
                                }
                            }
                        ],
                        "error": None,
                    }
                }
            )
        ]
    )

    result = fetch_yahoo_prices(["SPYM"], session=session)

    assert result.prices["SPYM"]["price"] == 83.0
    assert result.prices["SPYM"]["currency"] == "USD"
    assert round(result.prices["SPYM"]["change_pct"], 2) == 1.22
    assert result.warnings == []
    assert "query1.finance.yahoo.com" in session.requests[0]["url"]
    assert session.requests[0]["params"] == {"range": "2d", "interval": "1d"}
    assert "Mozilla" in session.requests[0]["headers"]["User-Agent"]


def test_fetch_yahoo_prices_returns_warning_when_symbol_fails():
    session = FakeSession([FakeResponse({"chart": {"result": None, "error": {"description": "not found"}}})])

    result = fetch_yahoo_prices(["BAD"], session=session)

    assert result.prices == {}
    assert any("BAD" in warning for warning in result.warnings)
