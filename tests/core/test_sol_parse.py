"""Tests for the line-based Solidity source scanner."""

import pathlib

from ruin.core.sol_parse import parse_source

FIXTURES = pathlib.Path(__file__).parents[1] / "fixtures" / "protocol_src"


def _vault() -> str:
    return (FIXTURES / "contracts_StakedAvantCoinV2.sol").read_text()


def test_parses_pragma_and_imports() -> None:
    facts = parse_source("vault", _vault())
    assert facts.pragma == "0.8.20"
    assert facts.imports == (
        "./StakedAvantCoin.sol",
        "./AvantCoinSilo.sol",
        "./interfaces/IStakedAvantCoinCooldown.sol",
    )


def test_vault_contract_header() -> None:
    facts = parse_source("vault", _vault())
    contract = facts.contracts[0]
    assert contract.name == "StakedAvantCoinV2"
    assert contract.kind == "contract"
    assert contract.inherits == ("IStakedAvantCoinCooldown", "StakedAvantCoin")


def test_vault_state_vars_include_mapping_and_immutable() -> None:
    facts = parse_source("vault", _vault())
    names = [(v.name, v.type, v.visibility) for v in facts.contracts[0].state_vars]
    assert ("cooldowns", "mapping", "public") in names
    assert ("silo", "AvantCoinSilo", "public") in names
    assert ("cooldownDuration", "uint24", "public") in names


def test_vault_functions_and_modifiers() -> None:
    facts = parse_source("vault", _vault())
    fns = {f.name: f for f in facts.contracts[0].functions}
    assert set(fns) == {
        "withdraw",
        "redeem",
        "unstake",
        "cooldownAssets",
        "cooldownShares",
        "setCooldownDuration",
    }
    assert fns["setCooldownDuration"].visibility == "external"
    assert fns["setCooldownDuration"].modifiers == ("onlyRole",)
    assert fns["cooldownAssets"].modifiers == ("ensureCooldownOn",)


def test_multiline_signature_limitation_is_documented() -> None:
    facts = parse_source("vault", _vault())
    fns = {f.name: f for f in facts.contracts[0].functions}
    assert fns["withdraw"].modifiers == ()


def test_erc20_inherits_and_functions() -> None:
    text = (
        FIXTURES / "lib_openzeppelin-contracts_contracts_token_ERC20_ERC20.sol"
    ).read_text()
    facts = parse_source("erc20", text)
    erc20 = next(c for c in facts.contracts if c.name == "ERC20")
    assert erc20.inherits == ("Context", "IERC20", "IERC20Metadata", "IERC20Errors")
    names = [f.name for f in erc20.functions]
    assert names[:5] == ["name", "symbol", "decimals", "totalSupply", "balanceOf"]
    assert ("_transfer", "internal", "nonpayable") in [
        (f.name, f.visibility, f.mutability) for f in erc20.functions
    ]


def test_import_forms_all_captured() -> None:
    text = (
        "pragma solidity ^0.8.0;\n"
        'import "a.sol";\n'
        'import b from "b.sol";\n'
        'import {C as D} from "c.sol";\n'
    )
    facts = parse_source("x", text)
    assert facts.imports == ("a.sol", "b.sol", "c.sol")


def test_pre_05_defaults_visibility_to_public() -> None:
    facts = parse_source("x", "pragma solidity ^0.4.24;\ncontract C {\n  uint x;\n}")
    assert facts.contracts[0].state_vars[0].visibility == "public"


def test_post_05_function_defaults_to_external() -> None:
    facts = parse_source(
        "x", "pragma solidity ^0.8.0;\ncontract C {\n  function f() {}\n}"
    )
    assert facts.contracts[0].functions[0].visibility == "external"


def test_modifier_before_returns_clause() -> None:
    text = (
        "pragma solidity ^0.8.0;\n"
        "contract C {\n"
        "  function f() external onlyOwner returns (uint256) {}\n"
        "}"
    )
    facts = parse_source("x", text)
    assert facts.contracts[0].functions[0].modifiers == ("onlyOwner",)


def test_constant_state_vars_are_skipped() -> None:
    text = (
        "pragma solidity ^0.8.0;\n"
        "contract C {\n"
        "  uint24 public constant MAX = 90 days;\n"
        "  uint24 public stored;\n"
        "}"
    )
    facts = parse_source("x", text)
    assert [v.name for v in facts.contracts[0].state_vars] == ["stored"]
