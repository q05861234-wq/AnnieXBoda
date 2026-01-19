from .user_agent import AgentInfo
from .user_agent import UserAgent


class Browsers:
    def __init__(self):
        # 🔥 TitanOS Update: Latest Chrome Version (2024/2025)
        self._chrome_agent = AgentInfo(
            'Chrome',
            '124.0.0.0', # Updated from 94
        )

        # MOZILLA BASE AGENTS
        self._mozilla_android_agent = AgentInfo(
            'Mozilla',
            '5.0',
            'Linux',
            'Android 13', # Updated to Android 13
        )
        self._mozilla_ios_agent = AgentInfo(
            'Mozilla',
            '5.0',
            'iPhone',
            'CPU iPhone OS 17_4 like Mac OS X', # Updated to iOS 17
        )
        self._mozilla_linux_agent = AgentInfo(
            'Mozilla',
            '5.0',
            'X11',
            'Linux x86_64',
        )
        self._mozilla_macos_agent = AgentInfo(
            'Mozilla',
            '5.0',
            'Macintosh',
            'Intel Mac OS X 14_4', # Updated to macOS Sonoma
        )
        self._mozilla_windows_agent = AgentInfo(
            'Mozilla',
            '5.0',
            'Windows NT 10.0',
            'Win64',
            'x64',
        )

        # APPLE_WEBKIT BASE AGENT
        self._apple_webkit_agent = AgentInfo(
            'AppleWebKit',
            '537.36',
            'KHTML',
            'like Gecko',
        )
        self._apple_webkit_apple_agent = AgentInfo(
            'AppleWebKit',
            '605.1.15',
            'KHTML',
            'like Gecko',
        )

        # SAFARI BASE AGENT
        self._safari_agent = AgentInfo(
            'Safari',
            '537.36',
        )
        self._safari_mobile_agent = AgentInfo(
            'Mobile Safari',
            '537.36',
        )
        self._safari_macos_agent = AgentInfo(
            'Safari',
            '605.1.15',
        )
        self._safari_ios_agent = AgentInfo(
            'Safari',
            '604.1',
        )

        # EDGE BASE AGENT (Updated to Chromium Edge)
        self._edge_android_agent = AgentInfo(
            'EdgA',
            '124.0.0.0',
        )
        self._edge_ios_agent = AgentInfo(
            'EdgiOS',
            '124.0.0.0',
        )
        self._edge_pc_agent = AgentInfo(
            'Edg',
            '124.0.0.0',
        )
        # Removed obsolete Edge Mobile/Xbox agents to avoid detection
        self._edge_windows_mob_agent = AgentInfo('Edge', '124.0.0.0') 
        self._edge_xbox_agent = AgentInfo('Edge', '124.0.0.0')

        # FIREFOX BASE AGENT
        self._firefox_default_agent = AgentInfo(
            'Firefox',
            '125.0', # Updated to latest FF
        )
        self._firefox_ios_agent = AgentInfo(
            'FxiOS',
            '125.0',
        )

        # OPERA BASE AGENT
        self._opera_default_agent = AgentInfo(
            'OPR',
            '109.0.0.0', # Updated Opera
        )
        self._opera_mobile_agent = AgentInfo(
            'OPR',
            '81.0.0.0',
        )

    # CHROME
    @property
    def chrome_android(self):
        return str(
            UserAgent([
                self._mozilla_android_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_mobile_agent,
            ]),
        )

    @property
    def chrome_ios(self):
        return str(
            UserAgent([
                self._mozilla_ios_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
            ]),
        )

    @property
    def chrome_linux(self):
        return str(
            UserAgent([
                self._mozilla_linux_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
            ]),
        )

    @property
    def chrome_macos(self):
        return str(
            UserAgent([
                self._mozilla_macos_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
            ]),
        )

    @property
    def chrome_windows(self):
        # 🔥 This is the GOLDEN AGENT (Most supported)
        return str(
            UserAgent([
                self._mozilla_windows_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
            ]),
        )

    # EDGE
    @property
    def edge_android(self):
        return str(
            UserAgent([
                self._mozilla_android_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_mobile_agent,
                self._edge_android_agent,
            ]),
        )

    @property
    def edge_ios(self):
        return str(
            UserAgent([
                self._mozilla_ios_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
                self._edge_ios_agent,
            ]),
        )

    @property
    def edge_macos(self):
        return str(
            UserAgent([
                self._mozilla_macos_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
                self._edge_pc_agent,
            ]),
        )

    @property
    def edge_windows(self):
        return str(
            UserAgent([
                self._mozilla_windows_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
                self._edge_pc_agent,
            ]),
        )

    @property
    def edge_windows_mobile(self):
        return str(
            UserAgent([
                self._mozilla_windows_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
                self._edge_windows_mob_agent,
            ]),
        )

    @property
    def edge_xbox_one(self):
        return str(
            UserAgent([
                self._mozilla_windows_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
                self._edge_xbox_agent,
            ]),
        )

    # FIREFOX
    @property
    def firefox_android(self):
        return str(
            UserAgent([
                self._mozilla_android_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_mobile_agent,
                self._firefox_default_agent,
            ]),
        )

    @property
    def firefox_ios(self):
        return str(
            UserAgent([
                self._mozilla_ios_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
                self._firefox_ios_agent,
            ]),
        )

    @property
    def firefox_linux(self):
        return str(
            UserAgent([
                self._mozilla_linux_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
                self._firefox_default_agent,
            ]),
        )

    @property
    def firefox_macos(self):
        return str(
            UserAgent([
                self._mozilla_macos_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
                self._firefox_default_agent,
            ]),
        )

    @property
    def firefox_windows(self):
        return str(
            UserAgent([
                self._mozilla_windows_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
                self._firefox_default_agent,
            ]),
        )

    # OPERA
    @property
    def opera_android(self):
        return str(
            UserAgent([
                self._mozilla_android_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_mobile_agent,
                self._opera_mobile_agent,
            ]),
        )

    @property
    def opera_linux(self):
        return str(
            UserAgent([
                self._mozilla_linux_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
                self._opera_default_agent,
            ]),
        )

    @property
    def opera_macos(self):
        return str(
            UserAgent([
                self._mozilla_macos_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
                self._opera_default_agent,
            ]),
        )

    @property
    def opera_windows(self):
        return str(
            UserAgent([
                self._mozilla_windows_agent,
                self._apple_webkit_agent,
                self._chrome_agent,
                self._safari_agent,
                self._opera_default_agent,
            ]),
        )

    # SAFARI
    @property
    def safari_ios(self):
        return str(
            UserAgent([
                self._mozilla_ios_agent,
                self._apple_webkit_apple_agent,
                self._chrome_agent,
                self._safari_ios_agent,
            ]),
        )

    @property
    def safari_macos(self):
        return str(
            UserAgent([
                self._mozilla_macos_agent,
                self._apple_webkit_apple_agent,
                self._chrome_agent,
                self._safari_macos_agent,
            ]),
        )
