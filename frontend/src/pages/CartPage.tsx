import { Link } from "react-router-dom";
import { useShoppingCart } from "../context/ShoppingCartContext";
import { formatMergedIngredient } from "../lib/shoppingCart";

export function CartPage() {
  const { entries, merged, uncheckedCount, removeEntry, clearAll, toggleChecked, isChecked } = useShoppingCart();

  const checkedCount = merged.length - uncheckedCount;

  return (
    <div className="page">
      <header style={{ marginBottom: "1rem" }}>
        <h1 className="page-title">Shopping list</h1>
        <p className="page-sub" style={{ margin: 0 }}>
          Ingredients gathered from recipes — separate from your cookbook.
        </p>
      </header>

      {entries.length === 0 ? (
        <section className="card" style={{ textAlign: "center", padding: "2rem 1rem" }}>
          <p style={{ margin: "0 0 1rem", color: "var(--text-muted)" }}>
            Add recipes from the cookbook to build your shopping list. Similar ingredients are combined automatically.
          </p>
          <Link to="/cookbook" className="btn btn--primary" style={{ textDecoration: "none" }}>
            Browse cookbook
          </Link>
        </section>
      ) : (
        <>
          <section className="card cart-recipes">
            <div className="cart-section-head">
              <strong>Recipes in list</strong>
              <span className="cart-section-head__meta">{entries.length} added</span>
            </div>
            <ul className="cart-recipes__list">
              {entries.map((entry) => (
                <li key={entry.entryId} className="cart-recipes__item">
                  <Link to={`/recipe/${entry.recipeId}`} className="cart-recipes__title">
                    {entry.title}
                  </Link>
                  <span className="cart-recipes__meta">{entry.lines.length} items</span>
                  <button
                    type="button"
                    className="btn btn--ghost cart-recipes__remove"
                    aria-label={`Remove ${entry.title} from shopping list`}
                    onClick={() => removeEntry(entry.entryId)}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <section className="card cart-checklist">
            <div className="cart-section-head">
              <strong>Ingredients</strong>
              <span className="cart-section-head__meta">
                {checkedCount}/{merged.length} checked
              </span>
            </div>
            {merged.length === 0 ? (
              <p className="page-sub" style={{ margin: 0 }}>No ingredients in these recipes.</p>
            ) : (
              <ul className="cart-checklist__list">
                {merged.map((item) => {
                  const checked = isChecked(item.mergeKey);
                  return (
                    <li key={item.mergeKey}>
                      <label className={`cart-checklist__row ${checked ? "cart-checklist__row--done" : ""}`}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleChecked(item.mergeKey)}
                        />
                        <span className="cart-checklist__text">{formatMergedIngredient(item)}</span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          {entries.length > 0 ? (
            <button type="button" className="btn btn--secondary btn--block" onClick={clearAll}>
              Clear shopping list
            </button>
          ) : null}
        </>
      )}
    </div>
  );
}
