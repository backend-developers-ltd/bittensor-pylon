from pylon._internal.common.settings import Identity, Settings, get_identities
from pylon._internal.common.types import HotkeyName, IdentityName, NetUid, PylonAuthToken, WalletName
from tests.helpers import override_env


@override_env(
    PYLON_IDENTITIES='["sn1", "debug"]',
    PYLON_ID_SN1_WALLET_NAME="wallet_sn1",
    PYLON_ID_SN1_HOTKEY_NAME="hotkey_sn1",
    PYLON_ID_SN1_NETUID="1",
    PYLON_ID_SN1_TOKEN="token_sn1",
    PYLON_ID_DEBUG_WALLET_NAME="wallet_debug",
    PYLON_ID_DEBUG_HOTKEY_NAME="hotkey_debug",
    PYLON_ID_DEBUG_NETUID="0",
    PYLON_ID_DEBUG_TOKEN="token_debug",
)
def test_identities_settings():
    settings = Settings()  # type: ignore
    assert settings.identities == ["sn1", "debug"]
    identities = get_identities(*settings.identities)
    assert identities == {
        "sn1": Identity(
            identity_name=IdentityName("sn1"),
            wallet_name=WalletName("wallet_sn1"),
            hotkey_name=HotkeyName("hotkey_sn1"),
            netuid=NetUid(1),
            token=PylonAuthToken("token_sn1"),
        ),
        "debug": Identity(
            identity_name=IdentityName("debug"),
            wallet_name=WalletName("wallet_debug"),
            hotkey_name=HotkeyName("hotkey_debug"),
            netuid=NetUid(0),
            token=PylonAuthToken("token_debug"),
        ),
    }
