import { useFavorites } from "../context/FavoritesContext";

type Props = {
  recipeId: number;
  className?: string;
  showLabel?: boolean;
};

export function FavoriteButton({ recipeId, className, showLabel }: Props) {
  const { isFavorite, toggleFavorite } = useFavorites();
  const on = isFavorite(recipeId);

  return (
    <button
      type="button"
      className={`fav-btn ${on ? "fav-btn--on" : ""} ${className ?? ""}`.trim()}
      aria-label={on ? "Remove from favourites" : "Add to favourites"}
      aria-pressed={on}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleFavorite(recipeId);
      }}
    >
      <span className="fav-btn__icon" aria-hidden>
        {on ? "♥" : "♡"}
      </span>
      {showLabel ? <span className="fav-btn__label">{on ? "Favourited" : "Favourite"}</span> : null}
    </button>
  );
}
