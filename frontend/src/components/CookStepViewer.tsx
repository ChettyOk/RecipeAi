import { useMemo, useState } from "react";

type Props = {
  steps: string[];
  doneSteps: Set<number>;
  onToggleStep: (index: number) => void;
};

export function CookStepViewer({ steps, doneSteps, onToggleStep }: Props) {
  const firstOpen = useMemo(() => steps.findIndex((_, i) => !doneSteps.has(i)), [steps, doneSteps]);
  const current = firstOpen === -1 ? Math.max(0, steps.length - 1) : firstOpen;
  const [animKey, setAnimKey] = useState(0);
  const done = doneSteps.has(current);
  const allDone = firstOpen === -1 && steps.length > 0;

  function toggleCurrent() {
    if (!done) setAnimKey((k) => k + 1);
    onToggleStep(current);
  }

  if (!steps.length) return <p className="card">No steps listed.</p>;

  return (
    <div className="cook-viewer">
      <p className="cook-viewer__progress">
        Step {current + 1} of {steps.length}
        {allDone ? " · complete" : ""}
      </p>

      <div key={`${current}-${animKey}`} className="cook-step-card">
        <label className={`cook-step-card__inner ${done ? "cook-step-card__inner--done" : ""}`}>
          <span className={`cook-check ${done ? "cook-check--on" : ""}`} aria-hidden>
            <span className="cook-check__box" />
            <span className="cook-check__mark">✓</span>
          </span>
          <input
            type="checkbox"
            className="cook-check__input"
            checked={done}
            onChange={() => toggleCurrent()}
          />
          <div className="cook-step-card__body">
            <span className="cook-step-card__num">{current + 1}</span>
            <p className="cook-step-card__text">{steps[current]}</p>
          </div>
        </label>
      </div>

      <div className="cook-viewer__dots" aria-hidden>
        {steps.map((_, i) => (
          <span
            key={i}
            className={`cook-viewer__dot ${doneSteps.has(i) ? "cook-viewer__dot--done" : ""} ${i === current ? "cook-viewer__dot--current" : ""}`}
          />
        ))}
      </div>
    </div>
  );
}
