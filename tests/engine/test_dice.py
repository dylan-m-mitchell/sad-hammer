from backend.engine.core.dice import Dice, DiceError, DiceState, stable_fraction


def test_same_seed_produces_same_sequence():
    first = Dice(12345)
    second = Dice(12345)

    assert [first.d6() for _ in range(20)] == [second.d6() for _ in range(20)]


def test_different_seed_produces_different_sequence():
    first = Dice(1)
    second = Dice(2)

    assert [first.d6() for _ in range(20)] != [second.d6() for _ in range(20)]


def test_roll_expression_supports_pool_and_modifier():
    dice = Dice(7)
    result = dice.roll("2D6+1")

    assert result.expression == "2D6+1"
    assert len(result.rolls) == 2
    assert result.modifier == 1
    assert result.total == sum(result.rolls) + 1
    assert all(1 <= roll <= 6 for roll in result.rolls)


def test_d3_and_roll_validation():
    dice = Dice(2)
    assert dice.roll("D3").total in (1, 2, 3)

    for expression in ("", "banana", "0D6", "D1", "2D6+", "101D6"):
        try:
            dice.roll(expression)
        except DiceError:
            continue
        raise AssertionError(f"{expression!r} should be rejected")


def test_dice_state_roundtrip_and_continuation():
    first = Dice(DiceState(seed=99, cursor=4))
    first.roll("2D6")
    saved = first.state

    second = Dice(DiceState.from_dict(saved.to_dict()))
    assert second.state == saved
    assert second.d6() == first.d6()
    assert second.roll("D3").to_dict() == first.roll("D3").to_dict()


def test_stable_fraction_is_seeded_and_bounded():
    values = [stable_fraction(42, key) for key in ("a", "b", "c")]
    assert values == [stable_fraction(42, key) for key in ("a", "b", "c")]
    assert all(0.0 <= value < 1.0 for value in values)
    assert len(set(values)) == 3
