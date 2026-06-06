export function RecipeCardSkeleton() {
  return (
    <div className="recipe-card recipe-card--skeleton" aria-hidden>
      <div className="skeleton skeleton--thumb" />
      <div className="recipe-card__body">
        <div className="skeleton skeleton--line" style={{ width: "90%" }} />
        <div className="skeleton skeleton--line skeleton--short" />
      </div>
    </div>
  );
}

export function RecipeGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <ul className="recipe-grid">
      {Array.from({ length: count }, (_, i) => (
        <li key={i}>
          <RecipeCardSkeleton />
        </li>
      ))}
    </ul>
  );
}
