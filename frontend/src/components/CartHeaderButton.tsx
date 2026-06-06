import { NavLink, useLocation } from "react-router-dom";
import { useShoppingCart } from "../context/ShoppingCartContext";

function CartIcon() {
  return (
    <svg className="cart-header-btn__svg" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M6 6h15l-1.5 9h-12L6 6Z"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <path d="M6 6 5 3H2" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      <circle cx="9.5" cy="19.5" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="16.5" cy="19.5" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function CartHeaderButton() {
  const { pathname } = useLocation();
  const { uncheckedCount, entries } = useShoppingCart();

  if (pathname.startsWith("/profile") || pathname.startsWith("/onboarding")) {
    return null;
  }

  const badge = uncheckedCount > 0 ? uncheckedCount : entries.length > 0 ? entries.length : 0;
  const onCart = pathname.startsWith("/cart");

  return (
    <NavLink
      to="/cart"
      className={`cart-header-btn ${onCart ? "cart-header-btn--active" : ""}`}
      aria-label={
        badge > 0
          ? `Shopping list, ${badge} item${badge === 1 ? "" : "s"}`
          : "Shopping list"
      }
    >
      <CartIcon />
      {badge > 0 ? (
        <span className="cart-header-btn__badge">{badge > 99 ? "99+" : badge}</span>
      ) : null}
    </NavLink>
  );
}
