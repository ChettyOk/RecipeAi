type Props = {
  tags: string[];
  className?: string;
};

export function DietaryTags({ tags, className }: Props) {
  if (!tags.length) return null;
  return (
    <div className={`dietary-tags ${className ?? ""}`.trim()}>
      {tags.map((t, i) => (
        <span
          key={t}
          className="dietary-tag chip chip--on"
          style={{ animationDelay: `${i * 80}ms` }}
        >
          {t.replace(/-/g, " ")}
        </span>
      ))}
    </div>
  );
}
