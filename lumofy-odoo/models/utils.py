import urllib
import requests


class LumofySession(requests.Session):
    def __init__(self, prefix_url):
        self.prefix_url = prefix_url
        super().__init__()

    def request(self, method, url, *args, **kwargs):
        url = urllib.parse.urljoin(self.prefix_url, url)
        return super().request(method, url, *args, **kwargs)


def get_session(setting_params):
    is_configuration_valid = setting_params.get_param(
        "lumofy.lumofy_is_configuration_valid"
    )

    if not is_configuration_valid:
        return None

    lumofy_remote_url = setting_params.get_param("lumofy.lumofy_remote_url")

    lumofy_integration_uuid = setting_params.get_param("lumofy.lumofy_integration_uuid")

    lumofy_authentication_token = setting_params.get_param(
        "lumofy.lumofy_authentication_token"
    )

    url = urllib.parse.urljoin(
        lumofy_remote_url,
        f"/api/integrations/{lumofy_integration_uuid}/",
    )

    session = LumofySession(prefix_url=url)
    session.headers.update(
        {
            "Authorization": f"Bearer {lumofy_authentication_token}",
            "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )

    return session
