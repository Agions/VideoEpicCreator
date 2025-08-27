"""
UI components package for VideoEpicCreator
"""

from .main_window import MainWindow
from .dashboard import Dashboard
from .sidebar import Sidebar
from .header import Header
from .settings_dialog import SettingsDialog

__all__ = [
    'MainWindow',
    'Dashboard', 
    'Sidebar',
    'Header',
    'SettingsDialog'
]