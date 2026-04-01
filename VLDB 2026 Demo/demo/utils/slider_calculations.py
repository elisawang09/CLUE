"""
Calculation utilities for simulator slider state management.
Handles target PLTV calculations and slider value adjustments.
"""

import streamlit as st


def calculate_target_pltv() -> float:
    """Calculate target PLTV based on pltv_input: 100 * (1 + pltv_input/100)."""
    return 100 * (1 + st.session_state.pltv_input / 100)


def generate_initial_slider_values(target: float) -> tuple[float, int, int]:
    """
    Generate initial values for the three sliders such that their product equals target.

    Args:
        target: The target product value for the three sliders

    Returns:
        tuple: (probability_of_active, num_orders, order_value)
    """
    # Start with a baseline product and scale it to reach target
    # Initial baseline: 0.4 * 5 * 50 = 100
    baseline_product = 100.0
    scale_factor = target / baseline_product

    # Scale proportionally
    prob_active = min(1.0, max(0.0, 0.4 * (scale_factor ** (1/3))))
    num_orders = min(10, max(0, int(5 * (scale_factor ** (1/3)))))

    # Adjust order value to hit the exact target
    if prob_active > 0 and num_orders > 0:
        order_value = target / (prob_active * num_orders)
        order_value = min(100, max(1, int(order_value)))
    else:
        order_value = 50

    st.session_state.prob_active = prob_active
    st.session_state.num_orders = num_orders
    st.session_state.order_value = order_value

    return prob_active, num_orders, order_value


def recalculate_sliders_for_target() -> None:
    """
    Recalculate slider values to hit the target PLTV.
    This is used when the target PLTV changes, and we want to adjust sliders to match the new target.
    """
    # Recalculate slider values for new target
    target = calculate_target_pltv()
    generate_initial_slider_values(target)


def adjust_sliders_for_target(changed_slider: str) -> None:
    """
    Adjust the other sliders to maintain product equal to target.

    When one slider is changed, recalculates the other two to maintain:
    prob_active × num_orders × order_value = target

    Args:
        changed_slider: Which slider was changed ('prob', 'num_orders', or 'order_value')
    """
    target = calculate_target_pltv()

    prob_active = st.session_state.prob_active
    num_orders = st.session_state.num_orders
    order_value = st.session_state.order_value

    if changed_slider == "prob":
        # Adjust num_orders and order_value
        remaining_product = target / max(prob_active, 0.01)

        # Try to keep order_value in valid range, adjust num_orders
        if order_value > 0:
            num_orders = remaining_product / order_value
            num_orders = min(10, max(0, int(num_orders)))

            # Recalculate order_value to hit exact target
            if num_orders > 0:
                order_value = remaining_product / num_orders
                order_value = min(100, max(1, int(order_value)))

        st.session_state.num_orders = num_orders
        st.session_state.order_value = order_value

    elif changed_slider == "num_orders":
        # Adjust prob_active and order_value
        remaining_product = target / max(num_orders, 1)

        # Try to keep order_value in valid range, adjust prob_active
        if order_value > 0:
            prob_active = remaining_product / order_value
            prob_active = min(1.0, max(0.0, prob_active))

            # Recalculate order_value to hit exact target
            if prob_active > 0:
                order_value = remaining_product / prob_active
                order_value = min(100, max(1, int(order_value)))

        st.session_state.prob_active = prob_active
        st.session_state.order_value = order_value

    elif changed_slider == "order_value":
        # Adjust prob_active and num_orders
        remaining_product = target / max(order_value, 1)

        # Try to keep num_orders in valid range, adjust prob_active
        if num_orders > 0:
            prob_active = remaining_product / num_orders
            prob_active = min(1.0, max(0.0, prob_active))

            # Recalculate num_orders to hit exact target
            if prob_active > 0:
                num_orders = remaining_product / prob_active
                num_orders = min(10, max(0, int(num_orders)))

        st.session_state.prob_active = prob_active
        st.session_state.num_orders = num_orders
