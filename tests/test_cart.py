from unittest.mock import Mock

import pytest

from shop.cart import Cart


def test_new_cart_is_empty(empty_cart: Cart) -> None:
    assert empty_cart.items_count() == 0
    assert empty_cart.total() == 0


def test_add_new_item(empty_cart: Cart) -> None:
    # Arrange: the empty_cart fixture provides a fresh empty cart
    # Act
    empty_cart.add("book", price=200.0, qty=2)
    # Assert
    assert empty_cart.items_count() == 2
    assert empty_cart.total() == pytest.approx(400.0)


def test_items_count_sums_quantities(cart_with_items: Cart) -> None:
    assert cart_with_items.items_count() == 6


def test_total_without_discount(cart_with_items: Cart) -> None:
    assert cart_with_items.total() == pytest.approx(460.0)


@pytest.mark.parametrize(
    ("discount", "expected"),
    [(0, 400.0), (10, 360.0), (12.5, 350.0), (50, 200.0), (100, 0.0)],
)
def test_total_with_discount(empty_cart: Cart, discount: float, expected: float) -> None:
    empty_cart.add("book", price=200.0, qty=2)
    assert empty_cart.total(discount_percent=discount) == pytest.approx(expected)


def test_add_negative_price_raises(empty_cart: Cart) -> None:
    with pytest.raises(ValueError, match="price"):
        empty_cart.add("book", price=-1.0)


def test_add_zero_price_is_allowed(empty_cart: Cart) -> None:
    # Boundary: price 0 is valid (a free item), only negative prices are rejected
    empty_cart.add("gift", price=0.0)
    assert empty_cart.items_count() == 1
    assert empty_cart.total() == 0


@pytest.mark.parametrize("qty", [0, -1])
def test_add_non_positive_qty_raises(empty_cart: Cart, qty: int) -> None:
    with pytest.raises(ValueError, match="qty"):
        empty_cart.add("book", price=10.0, qty=qty)


@pytest.mark.parametrize("discount", [-0.01, 100.01, -50, 150])
def test_total_invalid_discount_raises(cart_with_items: Cart, discount: float) -> None:
    with pytest.raises(ValueError, match="discount_percent"):
        cart_with_items.total(discount_percent=discount)


def test_remove_existing_item(cart_with_items: Cart) -> None:
    cart_with_items.remove("pen")
    assert cart_with_items.items_count() == 2
    assert cart_with_items.total() == pytest.approx(400.0)


def test_remove_missing_item_raises(cart_with_items: Cart) -> None:
    with pytest.raises(KeyError, match="phone"):
        cart_with_items.remove("phone")


def test_total_in_uses_rate_from_provider(cart_with_items: Cart) -> None:
    # Mock replaces the real exchange-rate service: no network, fixed answer
    rates = Mock()
    rates.get_rate.return_value = 40.0  # 1 USD = 40 UAH
    assert cart_with_items.total_in("USD", rates) == pytest.approx(11.5)
    # A mock also records calls, so we can check how it was used
    rates.get_rate.assert_called_once_with("USD")


@pytest.mark.parametrize("rate", [0.0, -40.0])
def test_total_in_non_positive_rate_raises(cart_with_items: Cart, rate: float) -> None:
    rates = Mock()
    rates.get_rate.return_value = rate
    with pytest.raises(ValueError, match="rate"):
        cart_with_items.total_in("USD", rates)


class FixedRates:
    """Stub: returns a preset rate for any currency and records nothing."""

    def __init__(self, rate: float) -> None:
        self.rate = rate

    def get_rate(self, currency: str) -> float:
        return self.rate


def test_total_in_rounds_to_two_decimals(cart_with_items: Cart) -> None:
    # 460 / 3 = 153.333..., the method must round to cents
    assert cart_with_items.total_in("XYZ", FixedRates(3.0)) == 153.33


def test_add_same_item_twice_sums_qty(empty_cart: Cart) -> None:
    empty_cart.add("book", price=200.0, qty=1)
    empty_cart.add("book", price=200.0, qty=2)
    assert empty_cart.items_count() == 3
    assert empty_cart.total() == pytest.approx(600.0)


def test_add_same_name_other_price_raises(empty_cart: Cart) -> None:
    # Design decision: a second price for the same item is an error,
    # otherwise the new price would be silently lost
    empty_cart.add("book", price=200.0)
    with pytest.raises(ValueError, match="price differs"):
        empty_cart.add("book", price=150.0)
    # The cart is unchanged after the rejected call
    assert empty_cart.items_count() == 1
    assert empty_cart.total() == pytest.approx(200.0)


def test_most_expensive_empty_cart_returns_none(empty_cart: Cart) -> None:
    assert empty_cart.most_expensive() is None


def test_most_expensive_single_item(empty_cart: Cart) -> None:
    empty_cart.add("pen", price=15.0)
    item = empty_cart.most_expensive()
    assert item is not None
    assert item.name == "pen"


def test_most_expensive_returns_item_with_highest_price(cart_with_items: Cart) -> None:
    item = cart_with_items.most_expensive()
    assert item is not None
    assert item.name == "book"
    assert item.price == 200.0


def test_most_expensive_compares_unit_price_not_line_total(empty_cart: Cart) -> None:
    # 100 pens cost 1500 in total, but one book (200) is the more expensive item
    empty_cart.add("pen", price=15.0, qty=100)
    empty_cart.add("book", price=200.0, qty=1)
    item = empty_cart.most_expensive()
    assert item is not None
    assert item.name == "book"


def test_format_total_returns_string_with_cents(cart_with_items: Cart) -> None:
    assert cart_with_items.format_total() == "460.00"
