#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integrations module for CineAIStudio

This module contains integrations with external video editing tools:
- JianYing (剪映) integration for professional video editing
- Other video editing software integrations
"""

from .jianying_integration import JianYingIntegration, JianYingProject

__version__ = "1.0.0"

__all__ = [
    'JianYingIntegration', 'JianYingProject'
]
