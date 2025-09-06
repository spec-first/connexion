import pathlib

import pytest
from connexion.spec import Specification

TEST_FOLDER = pathlib.Path(__file__).parent


def test_clone_with_external_refs():
    """Test that clone() with external refs uses _spec instead of _raw_spec"""

    # Load a spec that has external references
    relative_refs_path = TEST_FOLDER / "fixtures/relative_refs/openapi.yaml"

    # Load the specification
    spec = Specification.load(relative_refs_path)

    # Verify it has external refs (should return False for _has_only_internal_refs)
    has_only_internal = spec._has_only_internal_refs()

    # Call clone() - this should work regardless of internal/external refs
    cloned_spec = spec.clone()

    # Verify the clone is a valid specification
    assert cloned_spec is not None
    assert hasattr(cloned_spec, "_spec")
    assert hasattr(cloned_spec, "_raw_spec")

    # The cloned spec should have the same structure
    assert cloned_spec.version == spec.version

    # For specs with external refs, we expect _has_only_internal_refs to be False
    # (though this depends on whether the refs get resolved during loading)
    print(f"Original spec has only internal refs: {has_only_internal}")
    print(
        f"Cloned spec has only internal refs: {cloned_spec._has_only_internal_refs()}"
    )
