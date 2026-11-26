"""
Local pytest fixtures for dpath utilities tests.
"""

import pytest

# =============================================================================
# Dpath Engine Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def dpath_dict_engine_reduce():
    """Fixture to set LAMB_DPATH_DICT_ENGINE to 'reduce' for testing."""
    from django.conf import settings

    from lamb.utils.dpath import adapt_dict_impl
    
    # Store original value
    original_engine = getattr(settings, 'LAMB_DPATH_DICT_ENGINE', None)
    
    # Set to reduce
    settings.LAMB_DPATH_DICT_ENGINE = "reduce"
    adapt_dict_impl()
    
    yield
    
    # Restore original value
    if original_engine is not None:
        settings.LAMB_DPATH_DICT_ENGINE = original_engine
    elif hasattr(settings, 'LAMB_DPATH_DICT_ENGINE'):
        delattr(settings, 'LAMB_DPATH_DICT_ENGINE')
    adapt_dict_impl()


@pytest.fixture(scope="function")
def dpath_dict_engine_dpath():
    """Fixture to set LAMB_DPATH_DICT_ENGINE to 'dpath' for testing."""
    from django.conf import settings

    from lamb.utils.dpath import adapt_dict_impl
    
    # Store original value
    original_engine = getattr(settings, 'LAMB_DPATH_DICT_ENGINE', None)
    
    # Set to dpath
    settings.LAMB_DPATH_DICT_ENGINE = "dpath"
    adapt_dict_impl()
    
    yield
    
    # Restore original value
    if original_engine is not None:
        settings.LAMB_DPATH_DICT_ENGINE = original_engine
    elif hasattr(settings, 'LAMB_DPATH_DICT_ENGINE'):
        delattr(settings, 'LAMB_DPATH_DICT_ENGINE')
    adapt_dict_impl()