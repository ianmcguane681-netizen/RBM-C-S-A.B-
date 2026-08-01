"""The runtime can name more than one methodology, and still refuses unknown ones.

The identity of the methodology profile used to be a constant in `rbe_runtime`, and
its location a hardcoded path in the loader. That made the runtime capable of exactly
one methodology by construction -- not by policy, and with no error to read.

Moving identity into a registry is the whole seam, and it has to preserve the check it
replaced. A package states its own id and version in `PROFILE.json`, so validating
that against the package itself proves only that a file equals itself. The registry is
the independent claim: the runtime says what it expects to find, and a package that
disagrees fails to load.
"""

from __future__ import annotations

import pytest

from controlled_authority import profiles
from controlled_authority.rbm_package import validate_package
from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.errors import RBEError
from rbe_runtime.profile import ProfilePolicy


class TestTheRegistry:
    def test_the_research_board_is_registered(self):
        spec = profiles.get("RBM-001")

        assert spec.profile_version == "2.2.0"
        assert spec.package_root.name == "review-board"

    def test_omitting_the_id_resolves_the_research_board(self):
        """Existing callers named no profile, so the default must stay what it was."""

        assert profiles.get() is profiles.get("RBM-001")

    def test_an_unregistered_profile_is_refused_rather_than_defaulted(self):
        """A caller that asked for RBM-002 and silently got RBM-001 would run an
        engineering review under research rules with nothing to say so."""

        with pytest.raises(LookupError, match="RBM-999"):
            profiles.get("RBM-999")

    def test_every_registered_profile_is_keyed_by_its_own_id(self):
        for key, spec in profiles.PROFILES.items():
            assert key == spec.profile_id


class TestEveryProfileOnOneEngine:
    """The claim this repository exists to make good.

    If the profiles resolved to the same rules, the registry would be decoration. If
    loading one disturbed another, the runtime would be carrying a global.

    Written against `PROFILES` rather than a hardcoded list, so a fourth profile is
    covered the moment it is registered. A test that enumerated three would silently
    stop testing the thing it was written for.
    """

    def test_every_registered_profile_loads_and_is_distinct(self):
        pools = {}
        for profile_id in profiles.PROFILES:
            bundle = AuthorityBundle.load(profile_id=profile_id)
            pools[profile_id] = frozenset(
                bundle.profile["quorum"]["tier_3"]["specialist_pool"]
            )

        assert len(pools) >= 3
        # Pools may legitimately share a role -- RPA audits reproducibility under both
        # RBM-002 and RBM-003 -- but no two profiles may have the same pool, or one of
        # them is not doing its own job.
        assert len(set(pools.values())) == len(pools)

    def test_every_profile_shares_the_architecture_it_maps_onto(self):
        """A profile that supplied its own outcomes would be deciding what FAIL means."""

        loaded = [
            AuthorityBundle.load(profile_id=p).profile for p in profiles.PROFILES
        ]
        first = loaded[0]
        for other in loaded[1:]:
            assert other["permitted_outcomes"] == first["permitted_outcomes"]
            assert other["process_statuses"] == first["process_statuses"]
            assert other["canonical_lifecycle_mapping"] == first["canonical_lifecycle_mapping"]
            assert [r["rule_id"] for r in other["decision_precedence"]] == [
                r["rule_id"] for r in first["decision_precedence"]
            ]

    def test_no_profile_may_authorise_action_while_a_release_candidate(self):
        """The safety property the whole design rests on. A profile that is still a
        release candidate cannot permit a merge, a stake, or any other action -- and
        that is enforced by the same function for every profile."""

        from controlled_authority.rbm_package import is_merge_permitted

        for profile_id in profiles.PROFILES:
            profile = AuthorityBundle.load(profile_id=profile_id).profile
            if profile["status"] != "ACTIVE":
                assert is_merge_permitted(
                    profile_status=profile["status"],
                    binding=profile["binding"],
                    process_status="READY",
                    outcome="PASS",
                ) is False


class TestTheCryptoProfile:
    def test_the_chain_gates_each_name_a_failure_mode(self):
        """A gate with no failure mode is a checklist item. Each of these describes a
        specific way a checkable claim still misleads once you start checking."""

        gates = AuthorityBundle.load(profile_id="RBM-003").profile["chain_gates"]

        assert [g["gate_id"] for g in gates] == [
            "CG-01", "CG-02", "CG-03", "CG-04", "CG-05", "CG-06",
        ]
        for gate in gates:
            assert gate["failure_mode"].strip()
            assert gate["requirement"].strip()

    def test_every_chain_gate_has_a_seat_that_owns_it(self):
        profile = AuthorityBundle.load(profile_id="RBM-003").profile
        pool = set(profile["quorum"]["tier_3"]["specialist_pool"])

        assert {g["reviewer_role"] for g in profile["chain_gates"]} == pool


class TestTwoProfilesOnOneEngine:
    """Retained from the extraction: the original two-profile checks, still specific."""

    def test_the_engineering_board_is_registered(self):
        spec = profiles.get("RBM-002")

        assert spec.profile_version == "1.0.0"
        assert spec.package_root.name == "engineering-board"

    def test_each_profile_supplies_its_own_specialist_pool(self):
        research = AuthorityBundle.load(profile_id="RBM-001")
        engineering = AuthorityBundle.load(profile_id="RBM-002")

        research_pool = set(research.profile["quorum"]["tier_2"]["specialist_pool"])
        engineering_pool = set(engineering.profile["quorum"]["tier_2"]["specialist_pool"])

        assert research_pool == {"SAA", "BCA", "DEA", "QRA", "SPA", "POA"}
        assert engineering_pool == {"GCA", "MCA", "EFA", "ATA", "SVA", "RPA"}
        assert not research_pool & engineering_pool

    def test_reviewer_roles_are_discovered_per_profile(self):
        """Roles come from the specs on disk, so this also proves the loader read the
        engineering board's directory rather than the default one."""

        engineering = ProfilePolicy.from_authority(AuthorityBundle.load(profile_id="RBM-002"))

        assert set(engineering.role_to_spec) == {
            "MA", "GCA", "MCA", "EFA", "ATA", "SVA", "RPA", "SR",
        }

    def test_loading_one_profile_does_not_disturb_the_other(self):
        first = AuthorityBundle.load(profile_id="RBM-001")
        AuthorityBundle.load(profile_id="RBM-002")
        again = AuthorityBundle.load(profile_id="RBM-001")

        assert again.profile == first.profile

    def test_both_profiles_share_the_architecture_they_map_onto(self):
        """A profile that could supply its own outcomes would be deciding what FAIL
        means. The vocabulary is RBE-001's, and both must agree on it."""

        research = AuthorityBundle.load(profile_id="RBM-001").profile
        engineering = AuthorityBundle.load(profile_id="RBM-002").profile

        assert research["permitted_outcomes"] == engineering["permitted_outcomes"]
        assert research["process_statuses"] == engineering["process_statuses"]
        assert research["canonical_lifecycle_mapping"] == engineering["canonical_lifecycle_mapping"]
        assert [rule["rule_id"] for rule in research["decision_precedence"]] == [
            rule["rule_id"] for rule in engineering["decision_precedence"]
        ]

    def test_the_engineering_gates_each_name_an_observed_instance(self):
        """The gate list's authority is that every entry is a defect this system
        produced. A gate with no observed instance is a checklist item."""

        gates = AuthorityBundle.load(profile_id="RBM-002").profile["engineering_gates"]

        assert [gate["gate_id"] for gate in gates] == [
            "EG-01", "EG-02", "EG-03", "EG-04", "EG-05", "EG-06",
        ]
        for gate in gates:
            assert gate["observed_instance"].strip()
            assert gate["reviewer_role"] in {"GCA", "MCA", "EFA", "ATA", "SVA", "RPA"}

    def test_every_gate_has_a_seat_that_owns_it(self):
        gates = AuthorityBundle.load(profile_id="RBM-002").profile["engineering_gates"]
        pool = set(
            AuthorityBundle.load(profile_id="RBM-002").profile["quorum"]["tier_3"][
                "specialist_pool"
            ]
        )

        assert {gate["reviewer_role"] for gate in gates} == pool


class TestIdentityIsStillCheckedIndependently:
    def test_a_package_cannot_declare_its_own_identity(self):
        """The registry's claim wins. This is the check the refactor had to keep."""

        impostor = profiles.PackageSpec(
            profile_id="RBM-001",
            profile_version="9.9.9",
            package_root=profiles.RBM_001.package_root,
            schema_files=profiles.RBM_001.schema_files,
            reviewer_spec_count=profiles.RBM_001.reviewer_spec_count,
            methodology_document=profiles.RBM_001.methodology_document,
        )

        with pytest.raises(Exception, match="version mismatch"):
            validate_package(impostor)

    def test_a_missing_reviewer_spec_is_detected_not_absorbed(self):
        """Counting the directory would make a missing file undetectable: the
        expectation would simply become one fewer."""

        expecting_more = profiles.PackageSpec(
            profile_id="RBM-001",
            profile_version="2.2.0",
            package_root=profiles.RBM_001.package_root,
            schema_files=profiles.RBM_001.schema_files,
            reviewer_spec_count=9,
            methodology_document=profiles.RBM_001.methodology_document,
            methodology_terms=profiles.RBM_001.methodology_terms,
        )

        with pytest.raises(Exception, match="reviewer specifications"):
            validate_package(expecting_more)


class TestTheLoader:
    def test_the_bundle_carries_the_profile_it_was_loaded_under(self):
        bundle = AuthorityBundle.load()

        assert bundle.profile_id == "RBM-001"
        assert bundle.profile["profile_id"] == bundle.spec.profile_id

    def test_loading_an_unregistered_profile_fails(self):
        with pytest.raises(LookupError):
            AuthorityBundle.load(profile_id="RBM-999")

    def test_a_non_canonical_repo_root_is_still_refused(self, tmp_path):
        """Unchanged by the refactor and worth pinning: the package validators derive
        their own roots, so a different repo_root would load unvalidated authority."""

        with pytest.raises(RBEError) as error:
            AuthorityBundle.load(repo_root=tmp_path)

        assert error.value.code == "RBE_AUTHORITY_ROOT_NOT_VALIDATABLE"
